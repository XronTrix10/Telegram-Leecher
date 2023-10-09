# copyright 2023 © Xron Trix | https://github.com/Xrontrix10


import logging
from datetime import datetime
from os import path as ospath
from colab_leecher import colab_bot
from colab_leecher.utility.handler import cancelTask
from colab_leecher.utility.variables import Transfer, Paths, Messages, BotTimes
from colab_leecher.utility.helper import speedETA, getTime, sizeUnit, status_bar


async def media_Identifier(link):
    parts = link.split("/")
    message_id, message = parts[-1], None
    msg_chat_id = "-100" + parts[4]
    message_id, msg_chat_id = int(message_id), int(msg_chat_id)
    try:
        message = await colab_bot.get_messages(msg_chat_id, message_id)
    except Exception as e:
        logging.error(f"Error getting messages {e}")

    media = (
        message.document  # type: ignore
        or message.photo  # type: ignore
        or message.video  # type: ignore
        or message.audio  # type: ignore
        or message.voice  # type: ignore
        or message.video_note  # type: ignore
        or message.sticker  # type: ignore
        or message.animation  # type: ignore
        or None
    )
    if media is None:
        logging.error("Couldn't Download Telegram Message")
        await cancelTask("Couldn't Download Telegram Message")
        return
    return media, message


async def download_progress(current, total):
    speed_string, eta, percentage = speedETA(start_time, current, total)

    await status_bar(
        down_msg=Messages.status_head,
        speed=speed_string,
        percentage=percentage,
        eta=getTime(eta),
        done=sizeUnit(sum(Transfer.down_bytes) + current),
        left=sizeUnit(Transfer.total_down_size),
        engine="Pyrogram 💥",
    )


async def TelegramDownload(link, num):
    global start_time, TRANSFER_INFO
    media, message = await media_Identifier(link) # type: ignore
    if media is not None:
        name = media.file_name if hasattr(  # type: ignore
            media, "file_name") else "None"
    else:
        logging.error("Couldn't Download Telegram Message")
        await cancelTask("Couldn't Download Telegram Message")
        return

    Messages.status_head = f"<b>📥 DOWNLOADING FROM » </b><i>🔗Link {str(num).zfill(2)}</i>\n\n<code>{name}</code>\n"
    start_time = datetime.now()
    file_path = ospath.join(Paths.down_path, name)
    
    await message.download(progress=download_progress, in_memory=False, file_name=file_path) # type: ignore
    Transfer.down_bytes.append(media.file_size)
