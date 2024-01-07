# Some codes and idea were taken from https://github.com/Itz-fork/Mega.nz-Bot/tree/nightly | Thanks to  https://github.com/Itz-fork
# So, I can't take the entire credit for this module


import subprocess, logging
from datetime import datetime
from colab_leecher.utility.helper import status_bar
from colab_leecher.utility.variables import BotTimes, Messages, Paths


async def megadl(link: str, num: int):

    global BotTimes, Messages
    BotTimes.task_start = datetime.now()

    # TODO: Check the type of link and set the commands accordingly. i.e, Check if private or public, file or folder

    # Create a command to run megadl with the link
    command = [
        "megadl",
        "--no-ask-password",
        "--path",
        Paths.down_path,
        link,
    ]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,  bufsize=0)

    while True:
        output = process.stdout.readline()  # Read output line by line # type: ignore
        if output == b'' and process.poll() is not None:
            break  # Exit loop when process terminates and output is empty

        try:
            await extract_info(output.strip().decode("utf-8"))
        except Exception as e:
            logging.error(f"{e}")


async def extract_info(line):

    # Split the line by colon and space
    parts = line.split(": ")
    subparts = []
    # Split the second part by space
    if len(parts) > 1:
        subparts = parts[1].split()
    
    file_name = "N/A"
    progress = "N/A"
    downloaded_size = "N/A"
    total_size = "N/A"
    speed = "N/A"

    if len(subparts) > 10:
        
        try:
            # Get the file name from the first part
            file_name = parts[0]
            Messages.download_name = file_name
            # Get the progress from the first subpart
            progress = subparts[0][:-1]
            # Get the downloaded size and bytes from the subpart
            downloaded_size = f"{subparts[2]} {subparts[3]}"
            # downloaded_bytes = subparts[4][1:-1]
            # Get the total size from the subpart
            total_size = f"{subparts[7]} {subparts[8]}"
            # Get the speed from the subpart
            speed = f"{subparts[9][1:]} {subparts[10][:-1]}"
        except Exception:
            logging.error(f"Got this \n{parts}")
        
    Messages.status_head = f"<b>📥 DOWNLOADING FROM MEGA » </b>\n\n<b>🏷️ Name » </b><code>{file_name}</code>\n"
    
    try:
        percentage = round(float(progress)) 
    except Exception:
        percentage = 0
      
    await status_bar(
        Messages.status_head,
        speed,
        percentage,
        "🤷‍♂️ !!", # TODO: Calculate ETA
        downloaded_size,
        total_size,
        "Meg 😡",
    )

