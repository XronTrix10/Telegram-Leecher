# copyright 2024 © Xron Trix | https://github.com/Xrontrix10
"""Iterative whole-bucket / prefix S3 processing with crash-resume support.

The default S3 flows in :mod:`colab_leecher.downlader.s3` and
:mod:`colab_leecher.uploader.s3` operate in **bulk**: list every object in
the prefix, download all of them to ``Paths.down_path``, then upload
them. That is fine for a few-GB folder, but a 1 TB bucket will exhaust
Colab's 84 GB ephemeral disk before any upload happens.

This module provides a per-object **iterative** alternative. For each
object in the source bucket / prefix it:

1. Checks the persistent :mod:`colab_leecher.uploader.s3` tracker — if
   the object's ``(bucket, key, size)`` is already in the ``downloaded``
   list (either from this run or a previous, possibly crashed Colab
   runtime), it is **skipped**. This is the resume mechanism.
2. Cleans the local working dirs (``down_path`` / ``temp_zpath`` /
   ``temp_unzip_path`` / ``temp_files_dir``) so disk usage stays
   bounded by the largest single source object.
3. Downloads exactly one object via :func:`_download_one` (boto3
   multipart, so >2 GB downloads streamed in 64 MiB parts).
4. Runs the user-selected pipeline (Regular / Compress / Extract /
   UnDoubleZip) on that object only — reusing the existing
   :func:`Leech`, :func:`Zip_Handler` and :func:`Unzip_Handler`
   primitives so >2 GB Telegram splits behave exactly like ``/tupload``.
5. Uploads the result (to Telegram for ``/s3leech`` or to the
   destination S3 bucket for ``/s3upload``).
6. Records the source object in the tracker. The tracker is
   immediately mirrored to ``s3://<S3.bucket>/s3teletracker.json`` so
   a Colab crash mid-iteration does not lose progress.

Iterate mode is opt-in via :func:`is_multi_object_s3`: a URI like
``s3://bucket/single-file.zip`` (head_object succeeds) keeps the
existing single-shot flow; ``s3://bucket``, ``s3://bucket/`` or
``s3://bucket/folder/`` triggers iterative processing.
"""

import os
import shutil
import logging
import pathlib
from os import makedirs, path as ospath
from time import time as _time

from natsort import natsorted

from colab_leecher.utility.helper import (
    keyboard,
    parse_s3_uri,
    sizeUnit,
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
# detection
# ---------------------------------------------------------------------------

def _resolve_target(uri):
    """Return ``(bucket, key)`` for `uri`, falling back to the default bucket."""
    bucket, key = parse_s3_uri(uri)
    if not bucket:
        bucket = S3.bucket
    return bucket, key


def is_multi_object_s3(uri: str) -> bool:
    """Return True iff `uri` resolves to a prefix / whole bucket (not a single object).

    Used by ``taskScheduler`` to decide whether to dispatch into the
    iterative pipeline. Network-failure tolerant: any exception means
    "fall back to the existing bulk flow", which still works for
    smaller sources.
    """
    try:
        bucket, key = _resolve_target(uri)
        if not bucket:
            return False
        # Trailing slash or empty key → unambiguously a prefix.
        if not key or key.endswith("/"):
            return True
        # Try head_object: if it succeeds, this is a single object.
        # Lazy import to avoid cycles (uploader.s3 imports this module-free).
        from colab_leecher.uploader.s3 import ensure_s3_client

        client = ensure_s3_client()
        try:
            client.head_object(Bucket=bucket, Key=key)
            return False  # single object
        except Exception:
            # No object at that exact key → treat as prefix.
            return True
    except Exception as e:
        logging.warning(f"is_multi_object_s3 failed for {uri!r}: {e}")
        return False


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------

def _clean_workspace():
    """Wipe the per-iteration working directories so disk usage stays flat.

    ``Paths.WORK_PATH`` itself (created once at task start) is preserved
    so the status thumbnail and any other task-scoped state survives.
    """
    for p in (Paths.down_path, Paths.temp_zpath, Paths.temp_unzip_path, Paths.temp_files_dir):
        if ospath.exists(p):
            try:
                shutil.rmtree(p)
            except Exception as e:
                logging.warning(f"Could not clean {p}: {e}")
    makedirs(Paths.down_path, exist_ok=True)


async def _emit_status(text: str):
    """Best-effort status-message update; never raises."""
    try:
        MSG.status_msg = await MSG.status_msg.edit_text(
            text=text + sysINFO(),
            reply_markup=keyboard(),
        )
    except Exception as e:
        logging.debug(f"Status update failed (iterate): {e}")


def _split_summary(objects, direction, bucket, dest_lookup=None):
    """Return ``(to_process, already_done)`` lists for the given object set.

    `direction` is ``"downloaded"`` (resume on source side, used by
    /s3leech) or ``"uploaded"`` (resume on destination side, used by
    /s3upload Regular mode where dest_lookup yields the destination key).
    """
    from colab_leecher.uploader.s3 import is_already_tracked

    pending, done = [], []
    for obj in objects:
        size = int(obj.get("Size", 0))
        if direction == "uploaded" and dest_lookup is not None:
            dest_bucket, dest_key = dest_lookup(obj)
            if is_already_tracked("uploaded", dest_bucket, dest_key, size):
                done.append(obj)
                continue
        if is_already_tracked("downloaded", bucket, obj["Key"], size):
            done.append(obj)
            continue
        pending.append(obj)
    return pending, done


def _format_run_header(processed, skipped, total, bucket, key_prefix, mode_label):
    """Compose the task-message header shown above the per-iteration status."""
    return (
        f"<b>🔁 ITERATIVE {mode_label} » </b>\n"
        f"\n<b>🪣 Bucket » </b><code>{bucket}</code>"
        f"\n<b>📁 Prefix » </b><code>{key_prefix or '(whole bucket)'}</code>"
        f"\n<b>✅ Done » </b><code>{processed}</code>  "
        f"<b>⏭️ Skipped » </b><code>{skipped}</code>  "
        f"<b>📊 Total » </b><code>{total}</code>\n"
    )


# ---------------------------------------------------------------------------
# /s3leech — S3 source → Telegram destination, one object at a time
# ---------------------------------------------------------------------------

async def iterate_s3_to_telegram(uri, is_zip, is_unzip, is_dualzip):
    """Per-object S3 → Telegram leech with resume.

    Reuses :func:`Leech` (and the same ``sizeChecker`` >2 GB split
    pipeline used by ``/tupload``), so for any source object larger
    than 2 GB the Telegram side splits into ``.001`` / ``.002`` / …
    parts exactly like ``/tupload``.
    """
    # Lazy imports — these modules pull in S3 helpers and we want to
    # avoid any circular-import surprises at module load time.
    from colab_leecher.downlader.s3 import _download_one, _list_objects
    from colab_leecher.utility.handler import Leech, Unzip_Handler, Zip_Handler
    from colab_leecher.uploader.s3 import s3_track, s3_track_load_from_remote

    bucket, key = _resolve_target(uri)
    if not bucket:
        raise RuntimeError(
            "No S3 bucket specified and no default S3_BUCKET_NAME configured."
        )

    # Pull the durable tracker from S3 so a fresh runtime can resume.
    s3_track_load_from_remote()

    objects = _list_objects(bucket, key)
    if not objects:
        raise RuntimeError(f"No objects found at s3://{bucket}/{key}")

    Transfer.total_down_size = sum(int(o.get("Size", 0)) for o in objects)
    pending, already_done = _split_summary(objects, "downloaded", bucket)
    total = len(objects)
    skipped_initial = len(already_done)

    Messages.task_msg = (
        f"<b>🦞 TASK MODE » </b>"
        f"<i>{BOT.Mode.type.capitalize()} {BOT.Mode.mode.capitalize()} as "
        f"{BOT.Setting.stream_upload}</i>\n\n"
        f"📒 <b>Tracker » </b><code>s3://{bucket}/s3teletracker.json</code>\n"
    )
    await _emit_status(
        Messages.task_msg
        + _format_run_header(0, skipped_initial, total, bucket, key, "S3 ➜ TELEGRAM")
        + "\n⏳ __Starting iterative leech...__"
    )

    if not pending:
        logging.info("Nothing to do — every object is already in the tracker.")
        Messages.status_head = (
            f"<b>✅ ALL OBJECTS ALREADY DONE » </b>\n\n"
            f"<code>{skipped_initial}</code> entries found in s3teletracker.json — nothing to leech.\n"
        )
        return

    processed = 0
    skipped = skipped_initial
    grand_total_up = 0  # cumulative uploaded bytes across the batch (for SendLogs)

    for obj in pending:
        okey = obj["Key"]
        size = int(obj.get("Size", 0))
        idx = processed + skipped + 1  # 1-based for the status line

        _clean_workspace()
        # Reset per-object so the inner Telegram upload progress bar runs
        # a clean 0→100% for each object instead of accumulating across
        # the whole bucket. The grand total is preserved separately.
        Transfer.up_bytes = [0, 0]

        local_name = ospath.basename(okey) or f"object_{idx:04d}"
        dest = ospath.join(Paths.down_path, local_name)
        Messages.download_name = local_name
        BotTimes.current_time = _time()

        # Per-object header
        await _emit_status(
            Messages.task_msg
            + _format_run_header(processed, skipped, total, bucket, key, "S3 ➜ TELEGRAM")
            + f"\n<b>📥 OBJECT » </b><code>{okey}</code>"
            + f"\n<b>📦 Size » </b><code>{sizeUnit(size)}</code>\n"
        )

        try:
            # track=False: don't mark done yet — only after the upload below.
            await _download_one(
                bucket, okey, dest, size, 0, f"Object {idx}/{total}", track=False
            )
        except Exception as e:
            logging.error(f"Download failed for s3://{bucket}/{okey}: {e}")
            continue  # leave it un-tracked so a retry will pick it up

        # Run the user-selected upload pipeline. Each branch reuses the
        # existing handler so >2 GB splits, archive extraction, etc.
        # behave identically to /tupload.
        try:
            failed_before = len(getattr(Transfer, "failed_files", []))
            if is_zip:
                await Zip_Handler(Paths.down_path, True, True)
                await Leech(Paths.temp_zpath, True)
            elif is_unzip:
                await Unzip_Handler(Paths.down_path, True)
                await Leech(Paths.temp_unzip_path, True)
            elif is_dualzip:
                await Unzip_Handler(Paths.down_path, True)
                await Zip_Handler(Paths.temp_unzip_path, True, True)
                await Leech(Paths.temp_zpath, True)
            else:
                await Leech(Paths.down_path, True)
            # If any part of THIS object failed to upload, do NOT mark it
            # done — leave it untracked so the next run retries it instead
            # of silently skipping a partially-delivered object.
            failed_after = len(getattr(Transfer, "failed_files", []))
            if failed_after > failed_before:
                logging.error(
                    f"Object s3://{bucket}/{okey} had "
                    f"{failed_after - failed_before} failed part(s) — NOT marking done."
                )
                grand_total_up += sum(Transfer.up_bytes)
                continue
            # Mark the source object done ONLY after a fully successful
            # upload round-trip, so a crash mid-upload leaves it for retry.
            # Use the source object size so the resume check matches exactly.
            s3_track("downloaded", local_name, bucket, okey, size)
            grand_total_up += sum(Transfer.up_bytes)
            processed += 1
        except Exception as e:
            logging.error(f"Upload pipeline failed for s3://{bucket}/{okey}: {e}")
            # Don't track on failure → next run retries this object.
            continue

    # Restore the cumulative upload total so SendLogs reports the whole
    # batch size (the per-object reset above zeroed it each iteration).
    Transfer.up_bytes = [grand_total_up]

    # Final summary header (rendered by SendLogs which reads Messages.status_head)
    Messages.status_head = (
        f"<b>✅ ITERATIVE LEECH COMPLETE » </b>\n\n"
        f"<b>🪣 Bucket » </b><code>{bucket}</code>\n"
        f"<b>📊 Processed this run » </b><code>{processed}</code>\n"
        f"<b>⏭️ Skipped (already in tracker) » </b><code>{skipped}</code>\n"
        f"<b>📦 Total in source » </b><code>{total}</code>\n"
    )
    logging.info(
        f"S3 iterate-leech done: processed={processed} skipped={skipped} total={total}"
    )


# ---------------------------------------------------------------------------
# /s3upload with s3:// source — S3 → S3, one object at a time
# ---------------------------------------------------------------------------

async def iterate_s3_to_s3(uri, is_zip, is_unzip, is_dualzip):
    """Per-object S3 → S3 mirror with resume.

    Uploads each source object to ``s3://<S3.bucket>/<S3.prefix>/<rel>``
    where ``<rel>`` is the object key relative to the input prefix
    (preserving folder layout). Big files use boto3 multipart; the
    Compress / Extract / UnDoubleZip branches feed each result into
    ``s3_upload_file`` directly so split-zip volumes also land in S3.
    """
    from colab_leecher.downlader.s3 import _download_one, _list_objects
    from colab_leecher.utility.handler import Unzip_Handler, Zip_Handler
    from colab_leecher.uploader.s3 import (
        is_s3_configured,
        s3_track,
        s3_track_load_from_remote,
        s3_upload_file,
    )

    if not is_s3_configured():
        raise RuntimeError(
            "S3 not configured. Provide S3_ACCESS_KEY, S3_SECRET_KEY and S3_BUCKET_NAME."
        )

    src_bucket, src_key = _resolve_target(uri)
    if not src_bucket:
        raise RuntimeError("No S3 source bucket resolved.")
    if not S3.bucket:
        raise RuntimeError("No destination S3 bucket configured (S3_BUCKET_NAME).")

    s3_track_load_from_remote()

    objects = _list_objects(src_bucket, src_key)
    if not objects:
        raise RuntimeError(f"No objects found at s3://{src_bucket}/{src_key}")

    # Compute the base prefix that will be stripped from each source key
    # to produce the relative (destination-side) key.
    base_prefix = src_key.rstrip("/")
    if base_prefix and not base_prefix.endswith("/"):
        base_prefix = base_prefix + "/"

    def _dest_key_for(obj):
        rel = (
            obj["Key"][len(base_prefix):]
            if base_prefix and obj["Key"].startswith(base_prefix)
            else obj["Key"]
        )
        rel = rel.lstrip("/")
        composed = "/".join(p for p in (S3.prefix.strip("/") if S3.prefix else "", rel) if p)
        return S3.bucket, composed

    Transfer.total_down_size = sum(int(o.get("Size", 0)) for o in objects)
    # For Regular mode we can resume on the destination side too; for
    # zip/unzip/dualzip we can't predict every output key so we only
    # resume on the source side (which still skips fully-completed
    # source objects).
    if not (is_zip or is_unzip or is_dualzip):
        pending, already_done = _split_summary(
            objects, "uploaded", src_bucket, dest_lookup=_dest_key_for
        )
    else:
        pending, already_done = _split_summary(objects, "downloaded", src_bucket)

    total = len(objects)
    skipped_initial = len(already_done)

    Messages.task_msg = (
        f"<b>🦞 TASK MODE » </b>"
        f"<i>{BOT.Mode.type.capitalize()} {BOT.Mode.mode.capitalize()} as "
        f"{BOT.Setting.stream_upload}</i>\n\n"
        f"📒 <b>Tracker » </b><code>s3://{S3.bucket}/s3teletracker.json</code>\n"
    )
    await _emit_status(
        Messages.task_msg
        + _format_run_header(0, skipped_initial, total, src_bucket, src_key, "S3 ➜ S3")
        + "\n⏳ __Starting iterative mirror...__"
    )

    if not pending:
        logging.info("Nothing to do — every source object is already in the tracker.")
        Messages.status_head = (
            f"<b>✅ ALL OBJECTS ALREADY DONE » </b>\n\n"
            f"<code>{skipped_initial}</code> entries found in s3teletracker.json — nothing to mirror.\n"
        )
        return

    processed = 0
    skipped = skipped_initial

    for obj in pending:
        okey = obj["Key"]
        size = int(obj.get("Size", 0))
        idx = processed + skipped + 1
        _, dest_key = _dest_key_for(obj)
        dest_dir = ospath.dirname(dest_key).replace(os.sep, "/")

        _clean_workspace()

        local_name = ospath.basename(okey) or f"object_{idx:04d}"
        local_dest = ospath.join(Paths.down_path, local_name)
        Messages.download_name = local_name
        BotTimes.current_time = _time()

        await _emit_status(
            Messages.task_msg
            + _format_run_header(processed, skipped, total, src_bucket, src_key, "S3 ➜ S3")
            + f"\n<b>📥 OBJECT » </b><code>{okey}</code>"
            + f"\n<b>📦 Size » </b><code>{sizeUnit(size)}</code>"
            + f"\n<b>🎯 Dest » </b><code>s3://{S3.bucket}/{dest_key}</code>\n"
        )

        try:
            await _download_one(
                src_bucket, okey, local_dest, size, 0, f"Object {idx}/{total}", track=False
            )
        except Exception as e:
            logging.error(f"Download failed for s3://{src_bucket}/{okey}: {e}")
            continue

        # Run the user-selected pipeline. Output files are uploaded to
        # the destination bucket via the standard s3_upload_file (which
        # writes its own ``uploaded`` tracker entry per file).
        try:
            if is_zip:
                await Zip_Handler(Paths.down_path, True, True)
                for f in natsorted(os.listdir(Paths.temp_zpath)):
                    fpath = ospath.join(Paths.temp_zpath, f)
                    await s3_upload_file(fpath, f, key_prefix=dest_dir)
            elif is_unzip:
                await Unzip_Handler(Paths.down_path, True)
                files = [
                    str(p)
                    for p in pathlib.Path(Paths.temp_unzip_path).glob("**/*")
                    if p.is_file()
                ]
                for fpath in files:
                    rel = ospath.relpath(fpath, Paths.temp_unzip_path).replace(os.sep, "/")
                    sub_dir = "/".join(p for p in (dest_dir, ospath.dirname(rel)) if p)
                    await s3_upload_file(fpath, ospath.basename(fpath), key_prefix=sub_dir)
            elif is_dualzip:
                await Unzip_Handler(Paths.down_path, True)
                await Zip_Handler(Paths.temp_unzip_path, True, True)
                for f in natsorted(os.listdir(Paths.temp_zpath)):
                    fpath = ospath.join(Paths.temp_zpath, f)
                    await s3_upload_file(fpath, f, key_prefix=dest_dir)
            else:
                # Regular: single source object → single destination object,
                # boto3 multipart handles the >64 MiB heavy lifting.
                await s3_upload_file(local_dest, local_name, key_prefix=dest_dir)
            # Always record the source object as ``downloaded`` so the
            # next run can short-circuit it. ``s3_upload_file`` records
            # the destination side itself.
            s3_track("downloaded", local_name, src_bucket, okey, size)
            processed += 1
        except Exception as e:
            logging.error(f"Upload pipeline failed for s3://{src_bucket}/{okey}: {e}")
            continue

    Messages.status_head = (
        f"<b>✅ ITERATIVE MIRROR COMPLETE » </b>\n\n"
        f"<b>🪣 Source » </b><code>s3://{src_bucket}/{src_key}</code>\n"
        f"<b>🎯 Destination » </b><code>s3://{S3.bucket}/{S3.prefix or ''}</code>\n"
        f"<b>📊 Processed this run » </b><code>{processed}</code>\n"
        f"<b>⏭️ Skipped (already in tracker) » </b><code>{skipped}</code>\n"
        f"<b>📦 Total in source » </b><code>{total}</code>\n"
    )
    logging.info(
        f"S3 iterate-mirror done: processed={processed} skipped={skipped} total={total}"
    )
