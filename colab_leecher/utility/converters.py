# copyright 2023 © Xron Trix | https://github.com/Xrontrix10


import os
import GPUtil
import shutil
import logging
import subprocess
from asyncio import sleep
from threading import Thread
from datetime import datetime
from os import makedirs, path as ospath
from moviepy.editor import VideoFileClip as VideoClip
from colab_leecher.utility.variables import BOT, MSG, BotTimes, Paths, Messages
from colab_leecher.utility.helper import (
    getSize,
    keyboard,
    multipartArchive,
    sizeUnit,
    speedETA,
    status_bar,
    sysINFO,
    getTime,
)


async def videoConverter(file: str):
    global BOT, MSG, BotTimes

    def convert_to_mp4(input_file, out_file):
        clip = VideoClip(input_file)
        clip.write_videofile(
            out_file,
            codec="libx264",
            audio_codec="aac",
            ffmpeg_params=["-strict", "-2"],
        )

    async def msg_updater(c: int, tr, engine: str):
        global Messages
        messg = f"╭「" + "░" * c + "█" + "░" * (11 - c) + "」"
        messg += f"\n├⏳ **Status »** __Running 🏃🏼‍♂️__\n├🕹 **Attempt »** __{tr}__"
        messg += f"\n├⚙️ **Engine »** __{engine}__\n├💪🏼 **Handler »** __{core}__"
        messg += f"\n╰🍃 **Time Spent »** __{getTime((datetime.now() - BotTimes.start_time).seconds)}__"
        try:
            await MSG.status_msg.edit_text(
                text=Messages.task_msg + mtext + messg + sysINFO(),
                reply_markup=keyboard(),
            )
        except Exception:
            pass

    name, ext = ospath.splitext(file)

    if ext.lower() in [".mkv", ".mp4"]:
        return file  # Return if It's already mp4 / mkv file

    c, out_file, Err = 0, f"{name}.{BOT.Options.video_out}", False
    gpu = len(GPUtil.getAvailable())

    quality = "-preset slow -qp 0" if BOT.Options.convert_quality else ""

    # ignored = "-hwaccel cuvid -c:v h264_cuvid"
    if gpu == 1:
        cmd = f"ffmpeg -y -i '{file}' {quality} -c:v h264_nvenc -c:a copy '{out_file}'"
        core = "GPU"
    else:
        cmd = f"ffmpeg -y -i '{file}' {quality} -c:v libx264 -c:a copy '{out_file}'"
        core = "CPU"

    mtext = f"<b>🎥 Converting Video »</b>\n\n{ospath.basename(file)}\n\n"

    proc = subprocess.Popen(cmd, shell=True)

    while proc.poll() is None:
        await msg_updater(c, "1st", "FFmpeg 🏍")
        c = (c + 1) % 12
        await sleep(3)

    if ospath.exists(out_file) and getSize(out_file) == 0:
        os.remove(out_file)
        Err = True
    elif not ospath.exists(out_file):
        Err = True

    if Err:
        proc = Thread(target=convert_to_mp4, name="Moviepy", args=(file, out_file))
        proc.start()
        core = "CPU"
        while proc.is_alive():  # Until ytdl is downloading
            await msg_updater(c, "2nd", "Moviepy 🛵")
            c = (c + 1) % 12
            await sleep(3)

    if ospath.exists(out_file) and getSize(out_file) == 0:
        os.remove(out_file)
        Err = True
    elif not ospath.exists(out_file):
        Err = True
    else:
        Err = False

    if Err:
        logging.error("This Video Can't Be Converted !")
        return file
    else:
        os.remove(file)
        return out_file


async def sizeChecker(file_path, remove: bool):
    global Paths
    max_size = 2097152000  # 2 GB
    file_size = os.stat(file_path).st_size

    if file_size > max_size:
        if not ospath.exists(Paths.temp_zpath):
            makedirs(Paths.temp_zpath)
        _, filename = ospath.split(file_path)
        filename = filename.lower()
        if (
            filename.endswith(".zip")
            or filename.endswith(".rar")
            or filename.endswith(".7z")
            or filename.endswith(".tar")
            or filename.endswith(".gz")
        ):
            await splitArchive(file_path, max_size)
        else:
            await archive(file_path, True, remove)
            await sleep(2)
        return True
    else:
        return False


async def archive(path, is_split, remove: bool):
    global BOT, Messages
    dir_p, p_name = ospath.split(path)
    r = "-r" if ospath.isdir(path) else ""
    if is_split:
        split = "-s 2000m" if len(BOT.Options.zip_pswd) == 0 else "-v2000m"
    else:
        split = ""
    if len(BOT.Options.custom_name) != 0:
        name = BOT.Options.custom_name
    elif ospath.isfile(path):
        name = ospath.basename(path)
    else:
        name = Messages.download_name
    Messages.status_head = f"<b>🔐 ZIPPING » </b>\n\n<code>{name}</code>\n"
    Messages.download_name = f"{name}.zip"
    BotTimes.task_start = datetime.now()

    if len(BOT.Options.zip_pswd) == 0:
        cmd = f'cd "{dir_p}" && zip {r} {split} -0 "{Paths.temp_zpath}/{name}.zip" "{p_name}"'
    else:
        cmd = f'7z a -mx=0 -tzip -p{BOT.Options.zip_pswd} {split} "{Paths.temp_zpath}/{name}.zip" {path}'
    proc = subprocess.Popen(cmd, shell=True)
    total = sizeUnit(getSize(path))
    while proc.poll() is None:
        speed_string, eta, percentage = speedETA(
            BotTimes.task_start, getSize(Paths.temp_zpath), getSize(path)
        )
        await status_bar(
            Messages.status_head,
            speed_string,
            percentage,
            getTime(eta),
            sizeUnit(getSize(Paths.temp_zpath)),
            total,
            "Xr-Zipp 🔒",
        )
        await sleep(1)

    if remove:
        if ospath.isfile(path):
            os.remove(path)
        else:
            shutil.rmtree(path)


async def extract(zip_filepath, remove: bool):
    global BOT, Paths, Messages
    _, filename = ospath.split(zip_filepath)
    Messages.status_head = f"<b>📂 EXTRACTING »</b>\n\n<code>{filename}</code>\n"
    p = f"-p{BOT.Options.unzip_pswd}" if len(BOT.Options.unzip_pswd) != 0 else ""
    name, ext = ospath.splitext(filename)
    file_pattern, real_name, temp_unzip_path, total_ = (
        "",
        name,
        Paths.temp_unzip_path,
        0,
    )
    if ext == ".rar":
        if "part" in name:
            cmd = f"unrar x -kb -idq {p} '{zip_filepath}' {temp_unzip_path}"
            file_pattern = "rar"
        else:
            cmd = f"unrar x {p} '{zip_filepath}' {temp_unzip_path}"

    elif ext == ".tar":
        cmd = f"tar -xvf '{zip_filepath}' -C {temp_unzip_path}"
    elif ext == ".gz":
        cmd = f"tar -zxvf '{zip_filepath}' -C {temp_unzip_path}"
    else:
        cmd = f"7z x {p} '{zip_filepath}' -o{temp_unzip_path}"
        if ext == ".001":
            file_pattern = "7z"
        elif ext == ".z01":
            file_pattern = "zip"

    if file_pattern == "":
        total_ = getSize(zip_filepath)
        total = sizeUnit(total_)
    else:
        real_name, total_ = multipartArchive(zip_filepath, file_pattern, False)
        total = sizeUnit(total_)

    BotTimes.task_start = datetime.now()

    proc = subprocess.Popen(cmd, shell=True)

    while proc.poll() is None:
        speed_string, eta, percentage = speedETA(
            BotTimes.task_start,
            getSize(temp_unzip_path),
            total_,
        )
        await status_bar(
            Messages.status_head,
            speed_string,
            percentage,
            getTime(eta),
            sizeUnit(getSize(temp_unzip_path)),
            total,
            "Xr-Unzip 🔓",
        )
        await sleep(1)

    if remove:
        multipartArchive(zip_filepath, file_pattern, True)

        if ospath.exists(zip_filepath):
            os.remove(zip_filepath)

    Messages.download_name = real_name


async def splitArchive(file_path, max_size):
    global Paths, BOT, MSG, Messages
    _, filename = ospath.split(file_path)
    new_path = f"{Paths.temp_zpath}/{filename}"
    Messages.status_head = f"<b>✂️ SPLITTING » </b>\n\n<code>{filename}</code>\n"
    # Get the total size of the file
    total_size = ospath.getsize(file_path)

    BotTimes.task_start = datetime.now()

    with open(file_path, "rb") as f:
        chunk = f.read(max_size)
        i = 1
        bytes_written = 0
        while chunk:
            # Generate filename for this chunk
            ext = str(i).zfill(3)
            output_filename = "{}.{}".format(new_path, ext)

            # Write chunk to file
            with open(output_filename, "wb") as out:
                out.write(chunk)

            bytes_written += len(chunk)
            speed_string, eta, percentage = speedETA(
                BotTimes.task_start, bytes_written, total_size
            )
            await status_bar(
                Messages.status_head,
                speed_string,
                percentage,
                getTime(eta),
                sizeUnit(bytes_written),
                sizeUnit(total_size),
                "Xr-Split ✂️",
            )
            # Get next chunk
            chunk = f.read(max_size)
            i += 1  # Increment chunk counter
