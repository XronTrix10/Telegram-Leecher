# copyright 2023 © Xron Trix | https://github.com/Xrontrix10


import logging
from PIL import Image
from asyncio import sleep
from os import path as ospath
from datetime import datetime
from pyrogram.errors import FloodWait
from colab_leecher.utility.variables import BOT, Transfer, BotTimes, Messages, MSG, Paths
from colab_leecher.utility.helper import sizeUnit, fileType, getTime, status_bar, thumbMaintainer, videoExtFix

async def progress_bar(current, total):
    global status_msg, status_head
    upload_speed = 4 * 1024 * 1024
    elapsed_time_seconds = (datetime.now() - BotTimes.task_start).seconds
    if current > 0 and elapsed_time_seconds > 0:
        upload_speed = current / elapsed_time_seconds
    # Guard against a zero/garbage total (e.g. an empty object) which would
    # otherwise raise ZeroDivisionError, and clamp the derived values so the
    # rendered bar/ETA stay sane across multi-object iterate-mode batches.
    total_size = max(int(Transfer.total_down_size or 0), 1)
    done_bytes = current + sum(Transfer.up_bytes)
    eta = max(0, (total_size - done_bytes) / upload_speed)
    percentage = max(0.0, min((done_bytes / total_size) * 100, 100.0))
    await status_bar(
        down_msg=Messages.status_head,
        speed=f"{sizeUnit(upload_speed)}/s",
        percentage=percentage,
        eta=getTime(eta),
        done=sizeUnit(done_bytes),
        left=sizeUnit(total_size),
        engine="Pyrofork 💥",
    )


async def upload_file(file_path, real_name):
    global Transfer, MSG
    BotTimes.task_start = datetime.now()
    caption = f"<{BOT.Options.caption}>{BOT.Setting.prefix} {real_name} {BOT.Setting.suffix}</{BOT.Options.caption}>"
    type_ = fileType(file_path)

    f_type = type_ if BOT.Options.stream_upload else "document"

    # Guard: Telegram bot API rejects any single upload larger than 2 GB.
    # A part this big means the splitter mis-sized it; surface a clear error
    # instead of silently "succeeding" and reporting a bogus COMPLETE.
    TELEGRAM_MAX = 2097152000  # 2 GB
    try:
        actual_size = ospath.getsize(file_path)
    except OSError:
        actual_size = 0
    if actual_size > TELEGRAM_MAX:
        msg = (
            f"Upload SKIPPED — '{real_name}' is {actual_size / (1024**3):.2f} GiB, "
            f"which exceeds Telegram's 2 GB limit. The splitter should have "
            f"produced smaller parts."
        )
        logging.error(msg)
        Transfer.failed_files.append(real_name)
        return False

    # Upload the file
    try:
        if f_type == "video":
            # For Renaming to mp4
            if not BOT.Options.stream_upload:
                file_path = videoExtFix(file_path)
            # Generate Thumbnail and Get Duration
            thmb_path, seconds = thumbMaintainer(file_path)
            with Image.open(thmb_path) as img:
                width, height = img.size

            MSG.sent_msg = await MSG.sent_msg.reply_video(
                video=file_path,
                supports_streaming=True,
                width=width,
                height=height,
                caption=caption,
                thumb=thmb_path,
                duration=int(seconds),
                progress=progress_bar,
                reply_to_message_id=MSG.sent_msg.id,
            )

        elif f_type == "audio":
            thmb_path = None if not ospath.exists(Paths.THMB_PATH) else Paths.THMB_PATH
            MSG.sent_msg = await MSG.sent_msg.reply_audio(
                audio=file_path,
                caption=caption,
                thumb=thmb_path,  # type: ignore
                progress=progress_bar,
                reply_to_message_id=MSG.sent_msg.id,
            )

        elif f_type == "document":
            if ospath.exists(Paths.THMB_PATH):
                thmb_path = Paths.THMB_PATH
            elif type_ == "video":
                thmb_path, _ = thumbMaintainer(file_path)
            else:
                thmb_path = None

            MSG.sent_msg = await MSG.sent_msg.reply_document(
                document=file_path,
                caption=caption,
                thumb=thmb_path,  # type: ignore
                progress=progress_bar,
                reply_to_message_id=MSG.sent_msg.id,
            )

        elif f_type == "photo":
            MSG.sent_msg = await MSG.sent_msg.reply_photo(
                photo=file_path,
                caption=caption,
                progress=progress_bar,
                reply_to_message_id=MSG.sent_msg.id,
            )

        Transfer.sent_file.append(MSG.sent_msg)
        Transfer.sent_file_names.append(real_name)
        return True

    except FloodWait as e:
        logging.warning(f"FloodWait: Waiting {e.value} Seconds Before Trying Again.")
        await sleep(e.value)  # Wait dynamic FloodWait seconds before Trying Again
        return await upload_file(file_path, real_name)
    except Exception as e:
        logging.error(f"Error When Uploading : {e}")
        Transfer.failed_files.append(real_name)
        return False
