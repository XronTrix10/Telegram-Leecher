# copyright 2024 © Xron Trix | https://github.com/Xrontrix10
"""S3 / Wasabi downloader.

Mirrors the interface of the other downloaders in this package
(`gdrive.py`, `aria2.py`, …): an async ``s3_Download`` coroutine that
downloads an object (or all objects under a prefix) into
``Paths.down_path`` and reports progress via ``status_bar``.

Supports any S3-compatible service (AWS, Wasabi, Backblaze B2, …) via
``S3.endpoint_url``. Files larger than 2 GB are handled transparently
because ``boto3``'s default ``TransferConfig`` performs multipart
downloads automatically.
"""

import os
import logging
from os import path as ospath, makedirs
from datetime import datetime
from asyncio import get_event_loop, sleep

from colab_leecher.utility.helper import (
    getTime,
    parse_s3_uri,
    sizeUnit,
    speedETA,
    status_bar,
)
from colab_leecher.utility.variables import (
    BotTimes,
    Messages,
    Paths,
    S3,
    Transfer,
)
from colab_leecher.uploader.s3 import (  # shared helpers
    ensure_s3_client,
    s3_track,
)


def _resolve_target(uri: str):
    """Resolve `uri` to (bucket, key). Falls back to default bucket."""
    bucket, key = parse_s3_uri(uri)
    if not bucket:
        bucket = S3.bucket
    return bucket, key


def _list_objects(bucket: str, prefix: str):
    """Return all object dicts under `prefix` in `bucket` (handles paging)."""
    client = ensure_s3_client()
    out = []
    token = None
    while True:
        kwargs = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        resp = client.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []):
            # skip "folder" placeholder keys
            if obj["Key"].endswith("/") and obj.get("Size", 0) == 0:
                continue
            out.append(obj)
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")
    return out


def get_S3_size(uri: str) -> int:
    """Return total bytes of the object or prefix referenced by `uri`."""
    bucket, key = _resolve_target(uri)
    if not bucket:
        return 0
    try:
        client = ensure_s3_client()
        # Try as a single object first.
        if key and not key.endswith("/"):
            try:
                head = client.head_object(Bucket=bucket, Key=key)
                return int(head.get("ContentLength", 0))
            except Exception:
                pass  # fall through to prefix listing
        objs = _list_objects(bucket, key)
        return sum(int(o.get("Size", 0)) for o in objs)
    except Exception as e:
        logging.error(f"S3 size lookup failed for {uri}: {e}")
        return 0


def get_S3_Name(uri: str) -> str:
    """Best-effort name for the object/prefix in `uri`."""
    bucket, key = _resolve_target(uri)
    key = key.rstrip("/")
    if key:
        return ospath.basename(key) or key
    return bucket or "S3_DOWNLOAD"


async def _download_one(bucket: str, key: str, dest_path: str, total: int, base_done: int, num_label: str, track: bool = True):
    """Download a single S3 object to `dest_path` with live progress.

    When ``track`` is True (default, used by the bulk ``s3_Download``
    flow) a ``downloaded`` tracker entry is written as soon as the
    download completes. The iterative whole-bucket handlers pass
    ``track=False`` and record the object only **after** the full
    download→process→upload round-trip succeeds, so a crash mid-upload
    does not mark an object done (which would skip it on resume).
    """
    client = ensure_s3_client()
    parent = ospath.dirname(dest_path)
    if parent and not ospath.exists(parent):
        makedirs(parent, exist_ok=True)

    Messages.status_head = (
        f"<b>📥 DOWNLOADING FROM S3 » </b><i>{num_label}</i>\n"
        f"\n<b>🪣 Bucket » </b><code>{bucket}</code>"
        f"\n<b>🏷️ Key » </b><code>{key}</code>\n"
    )

    progress = {"bytes": 0}

    def _cb(n):
        progress["bytes"] += n
        S3.bytes_transferred += n  # global, used by mirror progress as well

    loop = get_event_loop()

    def _do():
        client.download_file(bucket, key, dest_path, Callback=_cb)

    fut = loop.run_in_executor(None, _do)

    BotTimes.task_start = datetime.now() if base_done == 0 else BotTimes.task_start

    while not fut.done():
        done_now = base_done + progress["bytes"]
        speed_string, eta, percentage = speedETA(BotTimes.task_start, done_now, max(total, 1))
        await status_bar(
            Messages.status_head,
            speed_string,
            percentage,
            getTime(eta),
            sizeUnit(done_now),
            sizeUnit(total),
            "S3 ☁️",
        )
        await sleep(1)

    # Surface boto3 errors to the caller
    await fut

    file_size = ospath.getsize(dest_path) if ospath.exists(dest_path) else 0
    if track:
        s3_track("downloaded", ospath.basename(dest_path), bucket, key, file_size)
    return file_size


async def s3_Download(uri: str, num: int):
    """Download an S3 object or prefix into ``Paths.down_path``.

    `uri` accepts ``s3://bucket/key`` or ``s3://bucket/prefix/`` (trailing
    slash). When the bucket portion is omitted the configured
    ``S3.bucket`` is used.
    """
    bucket, key = _resolve_target(uri)
    if not bucket:
        raise RuntimeError("No S3 bucket specified and no default S3_BUCKET_NAME configured.")

    client = ensure_s3_client()
    BotTimes.task_start = datetime.now()
    Messages.status_head = (
        f"<b>📥 DOWNLOADING FROM S3 » </b><i>🔗Link {str(num).zfill(2)}</i>\n"
        f"\n<b>🪣 Bucket » </b><code>{bucket}</code>\n"
    )

    # Decide single-object vs prefix.
    objs = []
    is_single = False
    if key and not key.endswith("/"):
        try:
            head = client.head_object(Bucket=bucket, Key=key)
            objs = [{"Key": key, "Size": int(head.get("ContentLength", 0))}]
            is_single = True
        except Exception:
            objs = _list_objects(bucket, key)
    else:
        objs = _list_objects(bucket, key)

    if not objs:
        raise RuntimeError(f"No objects found at s3://{bucket}/{key}")

    total_bytes = sum(int(o.get("Size", 0)) for o in objs)

    # Decide local layout: single -> file; prefix -> mirror folder tree.
    if is_single:
        local_name = ospath.basename(key) or "s3_object"
        dest = ospath.join(Paths.down_path, local_name)
        await _download_one(bucket, key, dest, total_bytes, 0, f"🔗Link {str(num).zfill(2)}")
        Transfer.down_bytes.append(int(objs[0].get("Size", 0)))
        return

    # Prefix download: preserve relative paths under the prefix.
    base_prefix = key
    if base_prefix and not base_prefix.endswith("/"):
        base_prefix = base_prefix + "/"
    folder_local_name = (
        ospath.basename(base_prefix.rstrip("/")) if base_prefix else bucket
    )
    folder_root = ospath.join(Paths.down_path, folder_local_name)
    if not ospath.exists(folder_root):
        makedirs(folder_root, exist_ok=True)

    base_done = 0
    for idx, obj in enumerate(objs, start=1):
        okey = obj["Key"]
        rel = okey[len(base_prefix):] if base_prefix and okey.startswith(base_prefix) else okey
        rel = rel.lstrip("/")
        if not rel:
            continue
        dest = ospath.join(folder_root, rel)
        await _download_one(
            bucket,
            okey,
            dest,
            total_bytes,
            base_done,
            f"Link {str(num).zfill(2)} • Object {idx}/{len(objs)}",
        )
        base_done += int(obj.get("Size", 0))

    Transfer.down_bytes.append(total_bytes)
