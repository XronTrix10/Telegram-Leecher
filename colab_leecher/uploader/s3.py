# copyright 2024 © Xron Trix | https://github.com/Xrontrix10
"""S3 / Wasabi uploader.

Uploads files (or whole folders) from local disk to a configurable
S3-compatible bucket. Mirrors the structure of
`colab_leecher/uploader/telegram.py`:

- ``s3_upload_file``  : single file upload + live progress + tracker write.
- ``S3_Mirror``       : uploads everything under ``folder_path`` to S3,
                         honoring the same Telegram-Leecher conventions
                         (split big files via the existing 2 GB sizeChecker
                         pipeline so the >2 GB experience matches the
                         other commands).

Big-file handling: ``boto3``'s ``TransferConfig`` automatically performs
multipart uploads above ``multipart_threshold``. We set 64 MiB threshold
and 64 MiB chunks to keep memory usage low while remaining fast on
Colab. AWS S3 caps a single object at 5 TiB and a single PUT at 5 GiB,
so multipart is required for >5 GiB anyway.
"""

import os
import json
import shutil
import logging
import pathlib
from os import path as ospath, makedirs
from datetime import datetime
from time import time as _time
from asyncio import get_event_loop, sleep
from natsort import natsorted

from colab_leecher.utility.helper import (
    getSize,
    getTime,
    keyboard,
    shortFileName,
    sizeUnit,
    speedETA,
    status_bar,
    sysINFO,
)
from colab_leecher.utility.variables import (
    BOT,
    BotTimes,
    Messages,
    MSG,
    Paths,
    S3,
    Transfer,
)


# ---------------------------------------------------------------------------
# client helpers
# ---------------------------------------------------------------------------

def _load_config_into_S3():
    """Populate ``S3.*`` from credentials.json on first use."""
    try:
        import colab_leecher as _cl  # avoid circular import at module load
    except Exception:
        return
    S3.access_key = S3.access_key or getattr(_cl, "S3_ACCESS_KEY", "") or ""
    S3.secret_key = S3.secret_key or getattr(_cl, "S3_SECRET_KEY", "") or ""
    S3.endpoint_url = S3.endpoint_url or getattr(_cl, "S3_ENDPOINT_URL", "") or ""
    S3.bucket = S3.bucket or getattr(_cl, "S3_BUCKET_NAME", "") or ""
    S3.region = S3.region or getattr(_cl, "S3_REGION", "") or "us-east-1"


def is_s3_configured() -> bool:
    _load_config_into_S3()
    return bool(S3.access_key and S3.secret_key and S3.bucket)


def ensure_s3_client():
    """Return a cached boto3 S3 client built from current ``S3.*`` config."""
    _load_config_into_S3()
    if S3.client is not None:
        return S3.client
    if not (S3.access_key and S3.secret_key):
        raise RuntimeError(
            "S3 not configured. Set S3_ACCESS_KEY and S3_SECRET_KEY in the Colab cell."
        )
    try:
        import boto3  # noqa: WPS433 (lazy import — boto3 is optional)
    except ImportError as e:
        raise RuntimeError(
            "boto3 is not installed. Add `boto3` to requirements.txt and reinstall."
        ) from e

    kwargs = dict(
        service_name="s3",
        aws_access_key_id=S3.access_key,
        aws_secret_access_key=S3.secret_key,
        region_name=S3.region or "us-east-1",
    )
    if S3.endpoint_url:
        kwargs["endpoint_url"] = S3.endpoint_url
    S3.client = boto3.client(**kwargs)
    return S3.client


# ---------------------------------------------------------------------------
# tracker (s3teletracker.json) — local + S3-persisted with crash-resume
# ---------------------------------------------------------------------------

# Key under ``S3.bucket`` where the tracker file is mirrored. This makes the
# tracker survive Colab runtime restarts: even if the local
# /content/Telegram-Leecher/s3teletracker.json disappears, the next bot run
# pulls the same JSON from S3 and resume-checks pick up where they left off.
TRACKER_KEY = "s3teletracker.json"


def _read_local_tracker():
    """Return the local tracker dict (with default keys), tolerant of corruption."""
    data = {"uploaded": [], "downloaded": []}
    if not ospath.exists(Paths.s3_tracker):
        return data
    try:
        with open(Paths.s3_tracker, "r") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            data["uploaded"] = list(loaded.get("uploaded") or [])
            data["downloaded"] = list(loaded.get("downloaded") or [])
    except Exception as e:
        logging.warning(f"S3 tracker read failed (resetting): {e}")
    return data


def _write_local_tracker(data):
    """Persist `data` to the local tracker JSON file."""
    try:
        with open(Paths.s3_tracker, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.warning(f"S3 tracker write failed: {e}")


def _entry_signature(entry):
    """Stable identity for a tracker entry: (bucket, key, size)."""
    return (entry.get("bucket"), entry.get("key"), int(entry.get("size") or 0))


def _merge_entries(*lists):
    """De-duplicate entries across lists, preserving first-seen order."""
    seen = set()
    out = []
    for lst in lists:
        for entry in lst or []:
            sig = _entry_signature(entry)
            if sig in seen:
                continue
            seen.add(sig)
            out.append(entry)
    return out


def s3_track_persist_to_remote():
    """Upload the local tracker file to ``s3://<S3.bucket>/<TRACKER_KEY>``.

    Best-effort: failures (no creds, network blip, permission denied) are
    logged but never abort the running task. The local file is the source
    of truth during a session; the remote copy is the durable backup.
    """
    if not S3.bucket or not ospath.exists(Paths.s3_tracker):
        return
    try:
        client = ensure_s3_client()
    except Exception as e:
        logging.debug(f"S3 client unavailable for tracker persist: {e}")
        return
    try:
        with open(Paths.s3_tracker, "rb") as f:
            body = f.read()
        client.put_object(
            Bucket=S3.bucket,
            Key=TRACKER_KEY,
            Body=body,
            ContentType="application/json",
        )
    except Exception as e:
        logging.warning(f"S3 tracker persist to remote failed: {e}")


def s3_track_load_from_remote():
    """Download the tracker from S3 and merge with the local tracker.

    Called at the start of every iterative S3 task so a fresh Colab
    runtime can resume work that an earlier (possibly crashed) runtime
    had already completed. Safe to call repeatedly.
    """
    if not S3.bucket:
        return
    try:
        client = ensure_s3_client()
    except Exception as e:
        logging.debug(f"S3 client unavailable for tracker fetch: {e}")
        return
    try:
        obj = client.get_object(Bucket=S3.bucket, Key=TRACKER_KEY)
        body = obj["Body"].read().decode("utf-8")
        remote = json.loads(body) if body.strip() else {}
        if not isinstance(remote, dict):
            remote = {}
    except Exception as e:
        # NoSuchKey on first run is expected — fall through silently.
        if "NoSuchKey" not in str(type(e).__name__) and "NoSuchKey" not in str(e):
            logging.info(f"No remote tracker yet (or fetch failed: {e}) — starting fresh")
        return

    local = _read_local_tracker()
    merged = {
        "uploaded": _merge_entries(local.get("uploaded"), remote.get("uploaded")),
        "downloaded": _merge_entries(local.get("downloaded"), remote.get("downloaded")),
    }
    _write_local_tracker(merged)
    logging.info(
        f"S3 tracker loaded from s3://{S3.bucket}/{TRACKER_KEY} → "
        f"{len(merged['uploaded'])} uploaded, {len(merged['downloaded'])} downloaded entries"
    )


def is_already_tracked(direction: str, bucket: str, key: str, size=None) -> bool:
    """Return True if (bucket, key) (and optional size) already exists in tracker.

    Used by the iterative whole-bucket handlers to skip objects that an
    earlier run already processed.
    """
    data = _read_local_tracker()
    for entry in data.get(direction, []):
        if entry.get("bucket") != bucket or entry.get("key") != key:
            continue
        if size is None:
            return True
        try:
            if int(entry.get("size") or 0) == int(size):
                return True
        except (TypeError, ValueError):
            return True
    return False


def s3_track(direction: str, file_name: str, bucket: str, key: str, size: int):
    """Append a transfer entry to ``s3teletracker.json`` and mirror it to S3.

    `direction` is one of ``"uploaded"`` (local→S3) or ``"downloaded"``
    (S3→local). Failures (read, write, remote-mirror) are non-fatal:
    tracker is best-effort and never aborts the running task.
    """
    data = _read_local_tracker()
    data.setdefault(direction, [])
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "file_name": file_name,
        "bucket": bucket,
        "key": key,
        "size": int(size),
        "size_human": sizeUnit(int(size)),
        "endpoint": S3.endpoint_url or "aws",
    }
    # Skip a duplicate signature so re-runs don't bloat the tracker.
    sig = _entry_signature(entry)
    if not any(_entry_signature(e) == sig for e in data[direction]):
        data[direction].append(entry)
    _write_local_tracker(data)

    # Mirror to S3 so a Colab restart can resume from where we left off.
    s3_track_persist_to_remote()


# ---------------------------------------------------------------------------
# upload primitives
# ---------------------------------------------------------------------------

def _build_transfer_config():
    try:
        from boto3.s3.transfer import TransferConfig
    except ImportError:
        return None
    return TransferConfig(
        multipart_threshold=64 * 1024 * 1024,
        multipart_chunksize=64 * 1024 * 1024,
        max_concurrency=4,
        use_threads=True,
    )


async def s3_upload_file(file_path: str, real_name: str, key_prefix: str = "") -> int:
    """Upload one local file to S3 with live progress + tracker.

    Returns the uploaded file size in bytes.
    """
    client = ensure_s3_client()
    bucket = S3.bucket
    if not bucket:
        raise RuntimeError("S3 destination bucket not set. Use /s3bucket <name>.")

    file_size = ospath.getsize(file_path)
    # Compose S3 key: <S3.prefix>/<key_prefix>/<filename>
    parts = [p.strip("/") for p in (S3.prefix, key_prefix, real_name) if p]
    key = "/".join(parts)

    BotTimes.task_start = datetime.now()
    Messages.status_head = (
        f"<b>📤 UPLOADING TO S3 » </b>\n"
        f"\n<b>🏷️ Name » </b><code>{real_name}</code>"
        f"\n<b>🪣 Bucket » </b><code>{bucket}</code>"
        f"\n<b>🔑 Key » </b><code>{key}</code>\n"
    )

    progress = {"bytes": 0}

    def _cb(n):
        progress["bytes"] += n

    cfg = _build_transfer_config()

    def _do():
        if cfg is not None:
            client.upload_file(file_path, bucket, key, Callback=_cb, Config=cfg)
        else:
            client.upload_file(file_path, bucket, key, Callback=_cb)

    loop = get_event_loop()
    fut = loop.run_in_executor(None, _do)

    while not fut.done():
        done_now = progress["bytes"]
        # Aggregate across files for global percentage if total_down_size set.
        total = max(file_size, 1)
        speed_string, eta, percentage = speedETA(BotTimes.task_start, done_now, total)
        await status_bar(
            Messages.status_head,
            speed_string,
            percentage,
            getTime(eta),
            sizeUnit(done_now),
            sizeUnit(file_size),
            "S3 ☁️",
        )
        await sleep(1)

    await fut  # raises on failure

    s3_track("uploaded", real_name, bucket, key, file_size)
    return file_size


# ---------------------------------------------------------------------------
# folder-level mirror (used by the /s3upload command)
# ---------------------------------------------------------------------------

async def S3_Mirror(folder_path: str, remove: bool):
    """Mirror everything in ``folder_path`` to S3.

    Layout in S3:
        ``<S3.prefix>/<task-folder>/<relative-path-of-file>``

    The task folder name is timestamped so repeated runs don't collide,
    matching the behaviour of ``Do_Mirror`` for Google Drive.
    """
    if not is_s3_configured():
        raise RuntimeError(
            "S3 not configured. Provide S3_ACCESS_KEY, S3_SECRET_KEY and S3_BUCKET_NAME."
        )

    cdt = datetime.now().strftime("Uploaded__%Y-%m-%d_%H-%M-%S")
    files = [str(p) for p in pathlib.Path(folder_path).glob("**/*") if p.is_file()]
    if not files:
        logging.warning("S3_Mirror: nothing to upload, folder empty.")
        return

    total = sum(ospath.getsize(f) for f in files)
    Transfer.total_down_size = total

    for file_path in natsorted(files):
        rel = ospath.relpath(file_path, folder_path)
        # Use forward slashes in S3 keys regardless of host OS.
        rel = rel.replace(os.sep, "/")
        # Trim outrageously long names (mirrors Leech behaviour).
        new_path = shortFileName(file_path)
        if new_path != file_path:
            os.rename(file_path, new_path)
            file_path = new_path
            rel = ospath.relpath(file_path, folder_path).replace(os.sep, "/")

        file_name = ospath.basename(file_path)
        BotTimes.current_time = _time()
        Messages.status_head = (
            f"<b>📤 UPLOADING TO S3 » </b>\n\n<code>{file_name}</code>\n"
        )
        try:
            MSG.status_msg = await MSG.status_msg.edit_text(
                text=Messages.task_msg
                + Messages.status_head
                + "\n⏳ __Starting.....__"
                + sysINFO(),
                reply_markup=keyboard(),
            )
        except Exception as d:
            logging.error(f"Error updating status bar (S3 mirror): {d}")

        # Compose key: <prefix>/<task>/<rel>
        parts = [p.strip("/") for p in (S3.prefix, cdt, ospath.dirname(rel)) if p]
        key_dir = "/".join(parts)

        size_uploaded = await s3_upload_file(file_path, file_name, key_prefix=key_dir)
        Transfer.up_bytes.append(size_uploaded)

        if remove and ospath.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logging.warning(f"Could not remove {file_path}: {e}")

    if remove and ospath.exists(folder_path):
        try:
            shutil.rmtree(folder_path)
        except Exception as e:
            logging.warning(f"Could not remove folder {folder_path}: {e}")
