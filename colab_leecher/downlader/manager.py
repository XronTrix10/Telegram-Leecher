# copyright 2023 © Xron Trix | https://github.com/Xrontrix10


import logging
from asyncio import sleep
from natsort import natsorted
from colab_leecher.downlader.ytdl import YTDL_Status, get_YT_Name
from colab_leecher.downlader.aria2 import aria2_Download, get_Aria2c_Name
from colab_leecher.utility.helper import isYtdlComplete, keyboard, sysINFO
from colab_leecher.downlader.telegram import TelegramDownload, media_Identifier
from colab_leecher.utility.variables import BOT, Transfer, MSG, Messages, Aria2c
from colab_leecher.downlader.gdrive import g_DownLoad, get_Gfolder_size, getFileMetadata, getIDFromURL

async def downloadManager(source, is_ytdl: bool):
   
    message = "\n<b>Please Wait...</b> ⏳\n<i>Merging YTDL Video...</i> 🐬"
    if is_ytdl:
        for i, link in enumerate(source):
            await YTDL_Status(link, i + 1)
        try:
            await MSG.status_msg.edit_text(text=Messages.task_msg + Messages.status_head + message + sysINFO(), reply_markup=keyboard())
        except Exception:
            pass
        while not isYtdlComplete():
            await sleep(2)
    else:
        for i, link in enumerate(source):
            try:
                if "drive.google.com" in link:
                    await g_DownLoad(link, i + 1)
                elif "t.me" in link:
                    await TelegramDownload(link, i + 1)
                elif "youtube.com" in link or "youtu.be" in link:
                    await YTDL_Status(link, i + 1)
                    try:
                        await MSG.status_msg.edit_text(text=Messages.task_msg + Messages.status_head + message + sysINFO(),  reply_markup=keyboard(), )
                    except Exception:
                        pass
                    while not isYtdlComplete():
                        await sleep(2)
                else:
                    aria2_dn = f"<b>PLEASE WAIT ⌛</b>\n\n__Getting Download Info For__\n\n<code>{link}</code>"
                    try:
                        await MSG.status_msg.edit_text(text=aria2_dn + sysINFO(), reply_markup=keyboard())
                    except Exception as e1:
                        print(f"Couldn't Update text ! Because: {e1}")
                    Aria2c.link_info = False
                    await aria2_Download(link, i + 1)
            except Exception as Error:
                logging.exception(f"Error While Downloading: {Error}")


async def calDownSize(sources):
    global TRANSFER_INFO
    for link in natsorted(sources):
        if "drive.google.com" in link:
            id = getIDFromURL(link)
            try:
                meta = getFileMetadata(id)
            except Exception as e:
                if "File not found" in str(e):
                    logging.error(
                        "The file link you gave either doesn't exist or You don't have access to it!"
                    )
                elif "Failed to retrieve" in str(e):
                    logging.error(
                        "Authorization Error with Google ! Make Sure you uploaded token.pickle !"
                    )
                else:
                    logging.error(f"Error in G-API: {e}")
            if meta.get("mimeType") == "application/vnd.google-apps.folder":  # type: ignore
                Transfer.total_down_size += get_Gfolder_size(id)
            else:
                Transfer.total_down_size += int(meta["size"])  # type: ignore
        elif "t.me" in link:
            media, _ = await media_Identifier(link)
            if media is not None:
                size = media.file_size
                Transfer.total_down_size += size
            else:
                logging.error("Couldn't Download Telegram Message")
        else:
            pass



async def get_d_name(link: str):
    global Messages
    if len(BOT.Options.custom_name) != 0:
        Messages.download_name = BOT.Options.custom_name
        return
    if "drive.google.com" in link:
        id = getIDFromURL(link)
        meta = getFileMetadata(id)
        Messages.download_name = meta["name"]
    elif "t.me" in link:
        media, _ = await media_Identifier(link)
        Messages.download_name = media.file_name if hasattr(media, "file_name") else "None"  # type: ignore
    elif "youtube.com" in link or "youtu.be" in link:
        Messages.download_name = get_YT_Name(link)
    else:
        Messages.download_name = get_Aria2c_Name(link)
