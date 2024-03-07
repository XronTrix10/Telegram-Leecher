# Some codes and idea were taken from https://github.com/Itz-fork/Mega.nz-Bot/tree/nightly | Thanks to  https://github.com/Itz-fork
# So, I can't take the entire credit for this module

import subprocess, logging
from datetime import datetime
from colab_leecher.utility.helper import status_bar, getTime
from colab_leecher.utility.variables import BotTimes, Messages, Paths
from pymegatools import Megatools, MegaError

async def megadl(link: str, num: int):

    global BotTimes, Messages
    BotTimes.task_start = datetime.now()
    mega = Megatools()
    try:
        await mega.async_download(link, progress=pro_for_mega, path=Paths.down_path)
    except MegaError as e:
        logging.error(f"An Error occurred: {e}")

async def pro_for_mega(stream, process):
    line = stream[-1]
    file_name = "N/A"
    percentage = 0
    downloaded_size = "N/A"
    total_size = "N/A"
    speed = "N/A"
    eta = "Unknown"  # Initialize eta with a default value
    try:
        ok = line.split(":")
        file_name = ok[0]
        ok = ok[1].split()
        percentage = float(ok[0][:-1])
        downloaded_size = ok[2] + " " + ok[3]
        total_size = ok[7] + " " + ok[8]
        speed = ok[9][1:] + " " + ok[10][:-1]

        # Calculate ETA
        remaining_bytes = float(ok[7]) - float(ok[2])
        bytes_per_second = float(ok[9][1:]) * (1024 if ok[10][-1] == 'K' else 1)  # Convert KB/s to bytes/s if necessary
        if bytes_per_second != 0:
            remaining_seconds = remaining_bytes / bytes_per_second
            eta = getTime(remaining_seconds)

    except Exception:
        pass

    Messages.download_name = file_name
    Messages.status_head = f"<b>📥 DOWNLOADING FROM MEGA » </b>\n\n<b>🏷️ Name » </b><code>{file_name}</code>\n"

    await status_bar(
        Messages.status_head,
        speed,
        percentage,
        eta,
        downloaded_size,
        total_size,
        "Meg 😡",
    )
