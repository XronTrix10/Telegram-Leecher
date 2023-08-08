# @title 🖥️ Main Colab Leech Code

# @title Main Code
# @markdown <div><center><img src="https://user-images.githubusercontent.com/125879861/255391401-371f3a64-732d-4954-ac0f-4f093a6605e1.png" height=80></center></div>

# @markdown <br><h3><b>🖱️ Select The `Bot Mode` You want</b></h3>
MODE = "Leech"  # @param ["Leech", "Mirror", "Dir-Leech"]
TYPE = "Normal"  # @param ["Normal", "Zip", "Unzip", "UnDoubleZip"]
UPLOAD_MODE = "Media"  # @param ["Media", "Document"]
# @markdown > <i>Media UPLOAD_MODE will upload files as `Streamable` on Telegram 

# @markdown <br><h3><b>✅ Tick The Below Checkbox If You Use any `Video Site Links`</b></h3>
YTDL_DOWNLOAD_MODE = False  # @param {type:"boolean"}
# @markdown > <i>YouTube Links Are Auto Detected</i> 😉

# @markdown <br><h3><b>🎥 Choose Options For `Video Converter` </b> </h3>
CONVERT_VIDEOS = False  # @param {type:"boolean"}
# @markdown > <i>If Enabled, it will convert any non-mp4 or mkv video file to mp4 or mkv</i>🎬
OUT_FORMAT = "MP4"  # @param ["MP4", "MKV"]

# @markdown <br><h3><b>🚂 Some Others `Options` </b></h3>
ENABLE_CUSTOM_FILE_NAME = False  # @param {type:"boolean"}
# @markdown > <i>Enable This to Rename Uploaded Files </i>✏️
ENABLE_PASSWORD_SUPPORT = False  # @param {type:"boolean"}
# @markdown > <i>Enable This to Unzip Encrypted Archives or Create Encrypted Archives</i> 🔐

# @markdown <br><h3><b>🖱️ Select The File `Caption Mode` You want</b></h3>

CAPTION = "Monospace"  # @param ["Regular", "Bold", "Italic", "Monospace", "Underlined"]
PREFIX = ""  # @param {type: "string"}
# @markdown > <i>Using Prefix is purely Optional</i> 🤷🏻‍♂️

import os, io, re, shutil, time, yt_dlp, math, pytz, psutil, uvloop, pathlib, subprocess
from PIL import Image
from pyrogram import Client
from natsort import natsorted
from google.colab import auth
from google.colab import drive
from datetime import datetime
from threading import Thread
from urllib.parse import urlparse
from re import search as re_search
from os import makedirs, path as ospath
from IPython.display import clear_output
from googleapiclient.discovery import build
from urllib.parse import parse_qs, urlparse
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from moviepy.editor import VideoFileClip as VideoClip
from moviepy.video.io.VideoFileClip import VideoFileClip
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

uvloop.install()


# =================================================================
#    Local OS Functions
# =================================================================


def getTime(seconds):
    seconds = int(seconds)
    days = seconds // (24 * 3600)
    seconds = seconds % (24 * 3600)
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60

    if days > 0:
        return f"{days}d {hours}h {minutes}m {seconds}s"
    elif hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def sizeUnit(size):
    if size > 1024 * 1024 * 1024 * 1024 * 1024:
        siz = f"{size/(1024**5):.2f} PiB"
    elif size > 1024 * 1024 * 1024 * 1024:
        siz = f"{size/(1024**4):.2f} TiB"
    elif size > 1024 * 1024 * 1024:
        siz = f"{size/(1024**3):.2f} GiB"
    elif size > 1024 * 1024:
        siz = f"{size/(1024**2):.2f} MiB"
    elif size > 1024:
        siz = f"{size/1024:.2f} KiB"
    else:
        siz = f"{size} B"
    return siz


def fileType(file_path: str):
    extensions_dict = {
        ".mp4": "video",
        ".avi": "video",
        ".mkv": "video",
        ".m2ts": "video",
        ".mov": "video",
        ".webm": "video",
        ".vob": "video",
        ".m4v": "video",
        ".mp3": "audio",
        ".wav": "audio",
        ".flac": "audio",
        ".aac": "audio",
        ".ogg": "audio",
        ".jpg": "photo",
        ".jpeg": "photo",
        ".png": "photo",
        ".bmp": "photo",
        ".gif": "photo",
    }
    _, extension = ospath.splitext(file_path)

    if extension.lower() in extensions_dict:
        return extensions_dict[extension]
    else:
        return "document"


def shortFileName(path):
    if ospath.isfile(path):
        dir_path, filename = ospath.split(path)
        if len(filename) > 60:
            basename, ext = ospath.splitext(filename)
            basename = basename[: 60 - len(ext)]
            filename = basename + ext
            path = ospath.join(dir_path, filename)
        return path
    elif ospath.isdir(path):
        dir_path, dirname = ospath.split(path)
        if len(dirname) > 60:
            dirname = dirname[:60]
            path = ospath.join(dir_path, dirname)
        return path
    else:
        if len(path) > 60:
            path = path[:60]
        return path


def getSize(path):
    if ospath.isfile(path):
        return ospath.getsize(path)
    else:
        total_size = 0
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = ospath.join(dirpath, f)
                total_size += ospath.getsize(fp)
        return total_size


def videoExtFix(file_path: str):
    _, f_name = ospath.split(file_path)
    if f_name.endswith(".mp4") or f_name.endswith(".mkv"):
        return file_path
    else:
        os.rename(file_path, ospath.join(file_path + ".mp4"))
        return ospath.join(file_path + ".mp4")


async def videoConverter(file: str):
    def convert_to_mp4(input_file, out_file):
        clip = VideoClip(input_file)
        clip.write_videofile(
            out_file,
            codec="libx264",
            audio_codec="aac",
            ffmpeg_params=["-strict", "-2"],
        )

    async def msg_updater(c: int, tr, engine: str):
        messg = f"╭「" + "░" * c + "█" + "░" * (11 - c) + "」"
        messg += f"\n├⏳ **Status »** __Running 🏃🏼‍♂️__\n├🕹 **Attempt »** __{tr}__"
        messg += f"\n├⚙️ **Engine »** __{engine}__\n├💪🏼 **Handler »** __{core}__"
        messg += f"\n╰🍃 **Time Spent »** __{getTime((datetime.now() - task_start).seconds)}__"
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg.id,  # type: ignore
                text=task_msg + mtext + messg + sysINFO(),
                reply_markup=keyboard(),
            )
        except Exception:
            pass

    name, ext = ospath.splitext(file)

    if ext.lower() in [".mkv", "mp4"]:
        return file  # Return if It's already mp4 / mkv file

    c, out_file, Err = 0, f"{name}.{OUT_FORMAT.lower()}", False
    gpu = !nvidia-smi --query-gpu=gpu_name --format=csv # type: ignore

    if len(gpu) != 1:
        cmd = f"ffmpeg -y -hwaccel cuvid -c:v h264_cuvid -i '{file}' -preset slow -c:v h264_nvenc -c:a copy '{out_file}'"
        core = "GPU"
    else:
        cmd = f"ffmpeg -y -i '{file}' -preset slow -c:v libx264 -c:a copy '{out_file}'"
        core = "CPU"

    mtext = f"<b>🎥 Converting Video »</b>\n\n{ospath.basename(file)}\n\n"

    proc = subprocess.Popen(cmd, shell=True)

    while proc.poll() is None:
        await msg_updater(c, "1st", "FFmpeg 🏍")
        c = (c + 1) % 12
        time.sleep(3)

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
            time.sleep(3)

    if ospath.exists(out_file) and getSize(out_file) == 0:
        os.remove(out_file)
        Err = True
    elif not ospath.exists(out_file):
        Err = True
    else:
        Err = False

    if Err:
        print("This Video Can't Be Converted !")
        return file
    else:
        os.remove(file)
        return out_file


def thumbMaintainer(file_path):
    thmb = f"{d_path}/video_frame.jpg"
    if ospath.exists(thmb):
        os.remove(thmb)
    try:
        fname, _ = ospath.splitext(ospath.basename(file_path))
        ytdl_thmb = f"{d_path}/ytdl_thumbnails/{fname}.webp"
        with VideoFileClip(file_path) as video:
            if ospath.exists(custom_thumb):
                return custom_thumb, video.duration
            elif ospath.exists(ytdl_thmb):
                return convertIMG(ytdl_thmb), video.duration
            else:
                video.save_frame(thmb, t=math.floor(video.duration / 2))
                return thmb, video.duration
    except Exception as e:
        print(f"Thmb Gen ERROR: {e}")
        return thumb_path, 0


def thumbChecker():
    for filename in os.listdir("/content"):
        _, ext = ospath.splitext(filename)
        if ext in [".png", ".webp", ".bmp"]:
            n_path = convertIMG(ospath.join("/content", filename))
            os.rename(n_path, custom_thumb)
            return True
        elif ext in [".jpeg", ".jpg"]:
            os.rename(ospath.join("/content", filename), custom_thumb)
            return True
    # No jpg file was found
    return False


def isYtdlComplete():
    for _d, _, filenames in os.walk(d_fol_path):
        for f in filenames:
            __, ext = ospath.splitext(f)
            if ext in [".part", ".ytdl"]:
                return False
    return True


def convertIMG(image_path):
    image = Image.open(image_path)
    if image.mode != "RGB":
        image = image.convert("RGB")
    output_path = ospath.splitext(image_path)[0] + ".jpg"
    image.save(output_path, "JPEG")
    os.remove(image_path)
    return output_path


def sysINFO():
    ram_usage = psutil.Process(os.getpid()).memory_info().rss
    disk_usage = psutil.disk_usage("/")
    cpu_usage_percent = psutil.cpu_percent()

    string = "\n\n⌬─────「 Colab Usage 」─────⌬\n"
    string += f"\n╭🖥️ **CPU Usage »**  __{cpu_usage_percent}%__"
    string += f"\n├💽 **RAM Usage »**  __{sizeUnit(ram_usage)}__"
    string += f"\n╰💾 **DISK Free »**  __{sizeUnit(disk_usage.free)}__"
    string += caution_msg

    return string


def multipartArchive(path: str, type: str, remove: bool):
    dirname, filename = ospath.split(path)
    name, _ = ospath.splitext(filename)

    c, size, rname = 1, 0, name
    if type == "rar":
        name_, _ = ospath.splitext(name)
        rname = name_
        na_p = name_ + ".part" + str(c) + ".rar"
        p_ap = ospath.join(dirname, na_p)
        while ospath.exists(p_ap):
            if remove:
                os.remove(p_ap)
            size += getSize(p_ap)
            c += 1
            na_p = name_ + ".part" + str(c) + ".rar"
            p_ap = ospath.join(dirname, na_p)

    elif type == "7z":
        na_p = name + "." + str(c).zfill(3)
        p_ap = ospath.join(dirname, na_p)
        while ospath.exists(p_ap):
            if remove:
                os.remove(p_ap)
            size += getSize(p_ap)
            c += 1
            na_p = name + "." + str(c).zfill(3)
            p_ap = ospath.join(dirname, na_p)

    elif type == "zip":
        na_p = name + ".zip"
        p_ap = ospath.join(dirname, na_p)
        if ospath.exists(p_ap):
            if remove:
                os.remove(p_ap)
            size += getSize(p_ap)
        na_p = name + ".z" + str(c).zfill(2)
        p_ap = ospath.join(dirname, na_p)
        while ospath.exists(p_ap):
            if remove:
                os.remove(p_ap)
            size += getSize(p_ap)
            c += 1
            na_p = name + ".z" + str(c).zfill(2)
            p_ap = ospath.join(dirname, na_p)

    return rname, size


async def archive(path, is_split, remove):
    global d_name
    dir_p, p_name = ospath.split(path)
    r = "-r" if ospath.isdir(path) else ""
    if is_split:
        split = "-s 2000m" if len(z_pswd) == 0 else "-v2000m"
    else:
        split = ""
    if len(custom_name) != 0:
        name = custom_name
    elif ospath.isfile(path):
        name = ospath.basename(path)
    else:
        name = d_name
    zip_msg = f"<b>🔐 ZIPPING » </b>\n\n<code>{name}</code>\n"
    d_name = f"{name}.zip"
    starting_time = datetime.now()
    if len(z_pswd) == 0:
        cmd = f'cd "{dir_p}" && zip {r} {split} -0 "{temp_zpath}/{name}.zip" "{p_name}"'
    else:
        cmd = f'7z a -mx=0 -tzip -p{z_pswd} {split} "{temp_zpath}/{name}.zip" {path}'
    proc = subprocess.Popen(cmd, shell=True)
    total = sizeUnit(getSize(path))
    while proc.poll() is None:
        speed_string, eta, percentage = speedETA(
            starting_time, getSize(temp_zpath), getSize(path)
        )
        await status_bar(
            zip_msg,
            speed_string,
            percentage,
            getTime(eta),
            sizeUnit(getSize(temp_zpath)),
            total,
            "Xr-Zipp 🔒",
        )
        time.sleep(1)

    if remove:
        if ospath.isfile(path):
            os.remove(path)
        else:
            shutil.rmtree(path)


async def extract(zip_filepath, remove):
    global d_name
    starting_time = datetime.now()
    _, filename = ospath.split(zip_filepath)
    unzip_msg = f"<b>📂 EXTRACTING »</b>\n\n<code>{filename}</code>\n"
    p = f"-p{uz_pswd}" if len(uz_pswd) != 0 else ""
    name, ext = ospath.splitext(filename)
    file_pattern, rname, total_ = "", name, 0
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
        rname, total_ = multipartArchive(zip_filepath, file_pattern, False)
        total = sizeUnit(total_)

    proc = subprocess.Popen(cmd, shell=True)

    while proc.poll() is None:
        speed_string, eta, percentage = speedETA(
            starting_time,
            getSize(temp_unzip_path),
            total_,
        )
        await status_bar(
            unzip_msg,
            speed_string,
            percentage,
            getTime(eta),
            sizeUnit(getSize(temp_unzip_path)),
            total,
            "Xr-Unzip 🔓",
        )
        time.sleep(1)

    if remove:
        multipartArchive(zip_filepath, file_pattern, True)

        if ospath.exists(zip_filepath):
            os.remove(zip_filepath)

    d_name = rname


async def sizeChecker(file_path, remove):
    max_size = 2097152000  # 2 GB
    file_size = os.stat(file_path).st_size

    if file_size > max_size:
        if not ospath.exists(temp_zpath):
            makedirs(temp_zpath)
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
            time.sleep(2)
        return True
    else:
        return False


async def splitArchive(file_path, max_size):
    starting_time = datetime.now()
    _, filename = ospath.split(file_path)
    new_path = f"{temp_zpath}/{filename}"
    down_msg = f"<b>✂️ SPLITTING » </b>\n\n<code>{filename}</code>\n"
    # Get the total size of the file
    total_size = ospath.getsize(file_path)
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
                starting_time, bytes_written, total_size
            )
            await status_bar(
                down_msg,
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


def isTimeOver(current_time):
    ten_sec_passed = time.time() - current_time[0] >= 3
    if ten_sec_passed:
        current_time[0] = time.time()
    return ten_sec_passed


def speedETA(start, done, total):
    percentage = (done / total) * 100
    percentage = 100 if percentage > 100 else percentage
    elapsed_time = (datetime.now() - start).seconds
    if done > 0 and elapsed_time != 0:
        raw_speed = done / elapsed_time
        speed = f"{sizeUnit(raw_speed)}/s"
        eta = (total - done) / raw_speed
    else:
        speed, eta = "N/A", 0
    return speed, eta, percentage


# =================================================================
#    Direct Link Handler Functions
# =================================================================


async def on_output(output: str):
    # print("=" * 60 + f"\n\n{output}\n\n" + "*" * 60)
    global link_info
    total_size = "0B"
    progress_percentage = "0B"
    downloaded_bytes = "0B"
    eta = "0S"
    try:
        if "ETA:" in output:
            parts = output.split()
            total_size = parts[1].split("/")[1]
            total_size = total_size.split("(")[0]
            progress_percentage = parts[1][parts[1].find("(") + 1 : parts[1].find(")")]
            downloaded_bytes = parts[1].split("/")[0]
            eta = parts[4].split(":")[1][:-1]
    except Exception as do:
        print(f"Could't Get Info Due to: {do}")

    percentage = re.findall("\d+\.\d+|\d+", progress_percentage)[0]  # type: ignore
    down = re.findall("\d+\.\d+|\d+", downloaded_bytes)[0]  # type: ignore
    down_unit = re.findall("[a-zA-Z]+", downloaded_bytes)[0]
    if "G" in down_unit:
        spd = 3
    elif "M" in down_unit:
        spd = 2
    elif "K" in down_unit:
        spd = 1
    else:
        spd = 0

    elapsed_time_seconds = (datetime.now() - start_time).seconds

    if elapsed_time_seconds >= 270 and not link_info:
        raise Exception("Failed to get download information ! Probably dead link 💀")
    # Only Do this if got Information
    if total_size != "0B":
        # Calculate download speed
        link_info = True
        current_speed = (float(down) * 1024**spd) / elapsed_time_seconds
        speed_string = f"{sizeUnit(current_speed)}/s"

        await status_bar(
            down_msg,
            speed_string,
            int(percentage),
            eta,
            downloaded_bytes,
            total_size,
            "Aria2c 🧨",
        )


async def aria2_Download(link, num):
    global start_time, down_msg
    name_d = get_Aria2c_Name(link)
    start_time = datetime.now()
    down_msg = f"<b>📥 DOWNLOADING FROM » </b><i>🔗Link {str(num).zfill(2)}</i>\n\n<b>🏷️ Name » </b><code>{name_d}</code>\n"

    # Create a command to run aria2p with the link
    command = [
        "aria2c",
        "-x16",
        "--seed-time=0",
        "--summary-interval=1",
        "--max-tries=3",
        "--console-log-level=notice",
        "-d",
        d_fol_path,
        link,
    ]

    # Run the command using subprocess.Popen
    proc = subprocess.Popen(
        command, bufsize=0, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    # Read and print output in real-time
    while True:
        output = proc.stdout.readline()  # type: ignore
        if output == b"" and proc.poll() is not None:
            break
        if output:
            # sys.stdout.write(output.decode("utf-8"))
            # sys.stdout.flush()
            await on_output(output.decode("utf-8"))

    # Retrieve exit code and any error output
    exit_code = proc.wait()
    error_output = proc.stderr.read()  # type: ignore
    if exit_code != 0:
        if exit_code == 3:
            raise Exception(f"The Resource was Not Found in {link}")
        elif exit_code == 9:
            raise Exception(f"Not enough disk space available")
        elif exit_code == 24:
            raise Exception(f"HTTP authorization failed.")
        else:
            raise Exception(
                f"aria2c download failed with return code {exit_code} for {link}.\nError: {error_output}"
            )


# =================================================================
#    Telegram Downloader
# =================================================================


async def media_Identifier(link):
    parts = link.split("/")
    message_id = parts[-1]
    msg_chat_id = "-100" + parts[4]
    message_id, msg_chat_id = int(message_id), int(msg_chat_id)
    message = await bot.get_messages(msg_chat_id, message_id)

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
        raise Exception("Couldn't Download Telegram Message")
    return media, message


async def download_progress(current, total):
    speed_string, eta, percentage = speedETA(start_time, current, total)

    await status_bar(
        down_msg=down_msg,
        speed=speed_string,
        percentage=percentage,
        eta=getTime(eta),
        done=sizeUnit(sum(down_bytes) + current),
        left=sizeUnit(folder_info[0]),
        engine="Pyrogram 💥",
    )


async def TelegramDownload(link, num):
    global start_time, down_msg
    media, message = await media_Identifier(link)
    if media is not None:
        name = media.file_name if hasattr(media, "file_name") else "None"  # type: ignore
    else:
        raise Exception("Couldn't Download Telegram Message")

    down_msg = f"<b>📥 DOWNLOADING FROM » </b><i>🔗Link {str(num).zfill(2)}</i>\n\n<code>{name}</code>\n"
    start_time = datetime.now()
    file_path = ospath.join(d_fol_path, name)
    await message.download(  # type: ignore
        progress=download_progress, in_memory=False, file_name=file_path
    )
    down_bytes.append(media.file_size)


# =================================================================
#    Youtube Link Handler Functions
# =================================================================


async def YTDL_Status(link, num):
    global down_msg
    name = get_YT_Name(link)
    down_msg = f"<b>📥 DOWNLOADING FROM » </b><i>🔗Link {str(num).zfill(2)}</i>\n\n<code>{name}</code>\n"

    YTDL_Thread = Thread(target=YouTubeDL, name="YouTubeDL", args=(link,))
    YTDL_Thread.start()

    while YTDL_Thread.is_alive():  # Until ytdl is downloading
        if ytdl_status[0]:
            sys_text = sysINFO()
            message = ytdl_status[0]
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg.id,  # type: ignore
                    text=task_msg + down_msg + message + sys_text,
                    reply_markup=keyboard(),
                )
            except Exception as f:
                pass
        else:
            try:
                message = ytdl_status[1].split("@")
                await status_bar(
                    down_msg=down_msg,
                    speed=message[0],
                    percentage=float(message[1]),
                    eta=message[2],
                    done=message[3],
                    left=message[4],
                    engine="Xr-YtDL 🏮",
                )
            except Exception as f:
                pass

        time.sleep(2.5)


class MyLogger:
    def __init__(self):
        pass

    def debug(self, msg):
        global ytdl_status
        if "item" in str(msg):
            msgs = msg.split(" ")
            ytdl_status[
                0
            ] = f"\n⏳ __Getting Video Information {msgs[-3]} of {msgs[-1]}__"

    @staticmethod
    def warning(msg):
        pass

    @staticmethod
    def error(msg):
        # if msg != "ERROR: Cancelling...":
        # print(msg)
        pass


def YouTubeDL(url):
    global ytdl_status

    def my_hook(d):
        global ytdl_status

        if d["status"] == "downloading":
            if d.get("total_bytes"):
                total_bytes = d["total_bytes"]
            elif d.get("total_bytes_estimate"):
                total_bytes = d["total_bytes_estimate"]
            else:
                total_bytes = 0
            dl_bytes = d.get("downloaded_bytes", 0)
            percent = d.get("downloaded_percent", 0)
            speed = d.get("speed", "N/A")
            eta = d.get("eta", 0)

            if percent == 0 and total_bytes != 0:
                percent = round((float(dl_bytes) * 100 / float(total_bytes)), 2)

            # print(
            #     f"\rDL: {sizeUnit(dl_bytes)}/{sizeUnit(total_bytes)} | {percent}% | Speed: {sizeUnit(speed)}/s | ETA: {eta}",
            #     end="",
            # )
            ytdl_status[0] = False
            ytdl_status[
                1
            ] = f"{sizeUnit(speed)}/s@{percent}@{getTime(eta)}@{sizeUnit(dl_bytes)}@{sizeUnit(total_bytes)}"

        elif d["status"] == "downloading fragment":
            # log_str = d["message"]
            # print(log_str, end="")
            pass

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
        "allow_multiple_video_streams": True,
        "allow_multiple_audio_streams": True,
        "writethumbnail": True,
        "allow_playlist_files": True,
        "overwrites": True,
        "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
        "progress_hooks": [my_hook],
        "logger": MyLogger(),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        if not ospath.exists(thumbnail_ytdl):
            makedirs(thumbnail_ytdl)
        try:
            info_dict = ydl.extract_info(url, download=False)
            ytdl_status[0] = "⌛ __Please WAIT a bit...__"
            if "_type" in info_dict and info_dict["_type"] == "playlist":
                playlist_name = info_dict["title"]
                if not ospath.exists(ospath.join(d_fol_path, playlist_name)):
                    makedirs(ospath.join(d_fol_path, playlist_name))
                ydl_opts["outtmpl"] = {
                    "default": f"{d_fol_path}/{playlist_name}/%(title)s.%(ext)s",
                    "thumbnail": f"{thumbnail_ytdl}/%(title)s.%(ext)s",
                }
                for entry in info_dict["entries"]:
                    video_url = entry["webpage_url"]
                    ydl.download([video_url])
            else:
                ytdl_status[0] = False
                ydl_opts["outtmpl"] = {
                    "default": f"{d_fol_path}/%(title)s.%(ext)s",
                    "thumbnail": f"{thumbnail_ytdl}/%(title)s.%(ext)s",
                }
                ydl.download([url])
        except Exception as e:
            print(f"YTDL ERROR: {e}")


# =================================================================
#    Initiator Functions
# =================================================================


async def calG_DownSize(sources):
    for link in natsorted(sources):
        if "drive.google.com" in link:
            id = getIDFromURL(link)
            try:
                meta = getFileMetadata(id)
            except Exception as e:
                if "File not found" in str(e):
                    raise Exception(
                        "The file link you gave either doesn't exist or You don't have access to it!"
                    )
                elif "Failed to retrieve" in str(e):
                    clear_output()
                    raise Exception(
                        "Authorization Error with Google ! Make Sure you uploaded token.pickle !"
                    )
                else:
                    raise Exception(f"Error in G-API: {e}")
            if meta.get("mimeType") == "application/vnd.google-apps.folder":
                folder_info[0] += get_Gfolder_size(id)
            else:
                folder_info[0] += int(meta["size"])
        elif "t.me" in link:
            media, _ = await media_Identifier(link)
            if media is not None:
                size = media.file_size
                folder_info[0] += size
            else:
                raise Exception("Couldn't Download Telegram Message")
        else:
            pass


def get_Aria2c_Name(link):
    cmd = f'aria2c -x10 --dry-run --file-allocation=none "{link}"'
    result = subprocess.run(cmd, stdout=subprocess.PIPE, shell=True)
    stdout_str = result.stdout.decode("utf-8")
    filename = stdout_str.split("complete: ")[-1].split("\n")[0]
    name = filename.split("/")[-1]
    if len(name) == 0:
        name = "UNKNOWN DOWNLOAD NAME"
    return name


def get_YT_Name(link):
    with yt_dlp.YoutubeDL({"logger": MyLogger()}) as ydl:
        info = ydl.extract_info(link, download=False)
        if "title" in info:
            return info["title"]
        else:
            return "UNKNOWN DOWNLOAD NAME"


async def get_d_name(link):
    global d_name
    if len(custom_name) != 0:
        d_name = custom_name
        return
    if "drive.google.com" in link:
        id = getIDFromURL(link)
        meta = getFileMetadata(id)
        d_name = meta["name"]
    elif "t.me" in link:
        media, _ = await media_Identifier(link)
        d_name = media.file_name if hasattr(media, "file_name") else "None"  # type: ignore
    elif "youtube.com" in link or "youtu.be" in link:
        d_name = get_YT_Name(link)
    else:
        d_name = get_Aria2c_Name(link)


# =================================================================
#    G Drive Functions
# =================================================================


def build_service():
    # create credentials object using colab auth
    auth.authenticate_user()
    service = build("drive", "v3")

    return service


async def g_DownLoad(link, num):
    global start_time, down_msg
    down_msg = f"<b>📥 DOWNLOADING FROM » </b><i>🔗Link {str(num).zfill(2)}</i>\n\n<b>🏷️ Name » </b><code>{d_name}</code>\n"
    file_id = getIDFromURL(link)
    meta = getFileMetadata(file_id)

    if meta.get("mimeType") == "application/vnd.google-apps.folder":
        await gDownloadFolder(file_id, d_fol_path)
    else:
        await gDownloadFile(file_id, d_fol_path)
        clear_output()


def getIDFromURL(link: str):
    if "folders" in link or "file" in link:
        regex = r"https:\/\/drive\.google\.com\/(?:drive(.*?)\/folders\/|file(.*?)?\/d\/)([-\w]+)"
        res = re_search(regex, link)
        if res is None:
            raise IndexError("G-Drive ID not found.")
        return res.group(3)
    parsed = urlparse(link)
    return parse_qs(parsed.query)["id"][0]


def getFilesByFolderID(folder_id):
    page_token = None
    files = []
    while True:
        response = (
            service.files()  # type: ignore
            .list(
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                q=f"'{folder_id}' in parents and trashed = false",
                spaces="drive",
                pageSize=200,
                fields="nextPageToken, files(id, name, mimeType, size, shortcutDetails)",
                orderBy="folder, name",
                pageToken=page_token,
            )
            .execute()
        )
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if page_token is None:
            break
    return files


def getFileMetadata(file_id):
    return (
        service.files()  # type: ignore
        .get(fileId=file_id, supportsAllDrives=True, fields="name, id, mimeType, size")
        .execute()
    )


def get_Gfolder_size(folder_id):
    try:
        query = "trashed = false and '{0}' in parents".format(folder_id)
        results = (
            service.files()  # type: ignore
            .list(
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                q=query,
                fields="files(id, mimeType, size)",
            )
            .execute()
        )

        total_size = 0
        items = results.get("files", [])

        folders_without_size = (
            item["id"]
            for item in items
            if item.get("size") is None
            and item["mimeType"] == "application/vnd.google-apps.folder"
        )

        for item in items:
            # If the item has a size attribute
            if "size" in item:
                total_size += int(item["size"])

        # Recursively call the function for folders whose size is not found
        for folder_id in folders_without_size:
            total_size += get_Gfolder_size(folder_id)

        return total_size

    except HttpError as error:
        print(f"Error while checking size: {error}")
        return -1


async def gDownloadFile(file_id, path):
    # Check if the specified file or folder exists and is downloadable.
    try:
        file = getFileMetadata(file_id)
    except HttpError as error:
        print("An error occurred: {0}".format(error))
        file = None

    if file is None:
        print(
            "Sorry, the specified file or folder does not exist or is not accessible."
        )
    else:
        if file["mimeType"].startswith("application/vnd.google-apps"):
            print(
                "Sorry, the specified ID is for a Google Docs, Sheets, Slides, or Forms document. You can only download these types of files in specific formats."
            )
        else:
            try:
                file_name = file.get("name", f"untitleddrivefile_{file_id}")
                file_name = ospath.join(path, file_name)
                # Create a BytesIO stream to hold the downloaded file data.
                file_contents = io.BytesIO()

                # Download the file or folder contents to the BytesIO stream.
                request = service.files().get_media(  # type: ignore
                    fileId=file_id, supportsAllDrives=True
                )
                file_downloader = MediaIoBaseDownload(
                    file_contents, request, chunksize=70 * 1024 * 1024
                )
                done = False
                while done is False:
                    status, done = file_downloader.next_chunk()
                    # Get current value from file_contents.
                    file_contents.seek(0)
                    with open(file_name, "ab") as f:
                        f.write(file_contents.getvalue())
                    # Reset the buffer for the next chunk.
                    file_contents.seek(0)
                    file_contents.truncate()
                    # The saved bytes until now
                    file_d_size = int(status.progress() * int(file["size"]))
                    down_done = sum(down_bytes) + file_d_size
                    speed_string, eta, percentage = speedETA(
                        start_time, down_done, folder_info[0]
                    )
                    await status_bar(
                        down_msg=down_msg,
                        speed=speed_string,
                        percentage=percentage,
                        eta=getTime(eta),
                        done=sizeUnit(down_done),
                        left=sizeUnit(folder_info[0]),
                        engine="G-API ♻️",
                    )
                down_bytes.append(int(file["size"]))
                down_count[0] += 1

            except HttpError as error:
                if error.resp.status == 403 and "User Rate Limit Exceeded" in str(
                    error
                ):
                    raise HttpError("Download quota for the file has been exceeded.")
                else:
                    print("Error downloading: {0}".format(error))
            except Exception as e:
                print("Error downloading: {0}".format(e))


async def gDownloadFolder(folder_id, path):
    folder_meta = getFileMetadata(folder_id)
    folder_name = folder_meta["name"]
    if not ospath.exists(f"{path}/{folder_name}"):
        makedirs(f"{path}/{folder_name}")
    path += f"/{folder_name}"
    result = getFilesByFolderID(folder_id)
    if len(result) == 0:
        return
    result = natsorted(result, key=lambda k: k["name"])
    for item in result:
        file_id = item["id"]
        shortcut_details = item.get("shortcutDetails")
        if shortcut_details is not None:
            file_id = shortcut_details["targetId"]
            mime_type = shortcut_details["targetMimeType"]
        else:
            mime_type = item.get("mimeType")
        if mime_type == "application/vnd.google-apps.folder":
            await gDownloadFolder(file_id, path)
        else:
            await gDownloadFile(file_id, path)


# =================================================================
#    Telegram Upload Functions
# =================================================================


def keyboard():
    return InlineKeyboardMarkup(
        [
            [  # First row
                InlineKeyboardButton(  # Opens a web URL
                    "Git Repo 🪲",
                    url="https://github.com/XronTrix10/Telegram-Leecher",
                ),
            ],
            [
                InlineKeyboardButton(  # Opens a web URL
                    "Channel 📣",
                    url="https://t.me/Colab_Leecher",
                ),
                InlineKeyboardButton(  # Opens a web URL
                    "Group 💬",
                    url="https://t.me/Colab_Leecher_Discuss",
                ),
            ],
        ]
    )


async def status_bar(down_msg, speed, percentage, eta, done, left, engine):
    bar_length = 12
    filled_length = int(percentage / 100 * bar_length)
    # bar = "⬢" * filled_length + "⬡" * (bar_length - filled_length)
    bar = "█" * filled_length + "░" * (bar_length - filled_length)
    message = (
        f"\n╭「{bar}」 » __{percentage:.2f}%__\n├⚡️ **Speed »** __{speed}__\n├⚙️ **Engine »** __{engine}__"
        + f"\n├⏳ **Time Left »** __{eta}__"
        + f"\n├🍃 **Time Spent »** __{getTime((datetime.now() - task_start).seconds)}__"
        + f"\n├✅ **Processed »** __{done}__\n╰📦 **Total Size »** __{left}__"
    )
    sys_text = sysINFO()
    try:
        print(f"\r{engine} ║ {bar} ║ {percentage:.2f}% ║ {speed} ║ ⏳ {eta}", end="")
        # Edit the message with updated progress information.
        if isTimeOver(current_time):
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg.id,  # type: ignore
                text=task_msg + down_msg + message + sys_text,
                reply_markup=keyboard(),
            )

    except Exception as e:
        # Catch any exceptions that might occur while editing the message.
        print(f"Error Updating Status bar: {str(e)}")


async def progress_bar(current, total):
    upload_speed = 4 * 1024 * 1024
    elapsed_time_seconds = (datetime.now() - start_time).seconds
    if current > 0 and elapsed_time_seconds > 0:
        upload_speed = current / elapsed_time_seconds
    eta = (total_down_size - current - sum(up_bytes)) / upload_speed
    percentage = (current + sum(up_bytes)) / total_down_size * 100
    await status_bar(
        down_msg=text_msg,
        speed=f"{sizeUnit(upload_speed)}/s",
        percentage=percentage,
        eta=getTime(eta),
        done=sizeUnit(current + sum(up_bytes)),
        left=sizeUnit(total_down_size),
        engine="Pyrogram 💥",
    )


async def upload_file(file_path, real_name):
    global sent

    caption = f"<{cap}>{PREFIX} {real_name}</{cap}>"
    type_ = fileType(file_path)

    f_type = type_ if UPLOAD_MODE == "Media" else "document"

    # Upload the file
    try:
        if f_type == "video":
            # For Renaming to mp4
            if not CONVERT_VIDEOS:
                file_path = videoExtFix(file_path)
            # Generate Thumbnail and Get Duration
            thmb_path, seconds = thumbMaintainer(file_path)
            with Image.open(thmb_path) as img:
                width, height = img.size

            sent = await sent.reply_video(
                video=file_path,
                supports_streaming=True,
                width=width,
                height=height,
                caption=caption,
                thumb=thmb_path,
                duration=int(seconds),
                progress=progress_bar,
                reply_to_message_id=sent.id,
            )

        elif f_type == "audio":
            thmb_path = None if not ospath.exists(custom_thumb) else custom_thumb
            sent = await sent.reply_audio(
                audio=file_path,
                caption=caption,
                thumb=thmb_path,  # type: ignore
                progress=progress_bar,
                reply_to_message_id=sent.id,
            )

        elif f_type == "document":
            if ospath.exists(custom_thumb):
                thmb_path = custom_thumb
            elif type_ == "video":
                thmb_path, _ = thumbMaintainer(file_path)
            else:
                thmb_path = None

            sent = await sent.reply_document(
                document=file_path,
                caption=caption,
                thumb=thmb_path,  # type: ignore
                progress=progress_bar,
                reply_to_message_id=sent.id,
            )

        elif f_type == "photo":
            sent = await sent.reply_photo(
                photo=file_path,
                caption=caption,
                progress=progress_bar,
                reply_to_message_id=sent.id,
            )

        clear_output()

        sent_file.append(sent)
        sent_fileName.append(real_name)

    except Exception as e:
        print(f"Error When Uploading : {e}")


# =================================================================
#    Handler Functions
# =================================================================


async def downloadManager(source, is_ytdl: bool):
    global link_info, msg
    message = "\n<b>Please Wait...</b> ⏳\n<i>Merging YTDL Video...</i> 🐬"
    if is_ytdl:
        for i, link in enumerate(source):
            await YTDL_Status(link, i + 1)
        try:
            await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg.id,  # type: ignore
                    text=task_msg + down_msg + message + sysINFO(),
                    reply_markup=keyboard(),
            )
        except Exception:
            pass
        while not isYtdlComplete():
            time.sleep(2)
    else:
        for i, link in enumerate(source):
            if "drive.google.com" in link:
                await g_DownLoad(link, i + 1)
            elif "t.me" in link:
                await TelegramDownload(link, i + 1)
            elif "youtube.com" in link or "youtu.be" in link:
                await YTDL_Status(link, i + 1)
                try:
                    await bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=msg.id,  # type: ignore
                            text=task_msg + down_msg + message + sysINFO(),
                            reply_markup=keyboard(),
                    )
                except Exception:
                    pass
                while not isYtdlComplete():
                    time.sleep(2)
            else:
                aria2_dn = f"<b>PLEASE WAIT ⌛</b>\n\n__Getting Download Info For__\n\n<code>{link}</code>"
                try:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=msg.id,  # type: ignore
                        text=aria2_dn + sysINFO(),
                        reply_markup=keyboard(),
                    )
                except Exception as e1:
                    print(f"Couldn't Update text ! Because: {e1}")
                link_info = False
                await aria2_Download(link, i + 1)


async def Leech(folder_path: str, remove: bool):
    global total_down_size, text_msg, start_time, msg, sent
    total_down_size = getSize(folder_path)
    files = [str(p) for p in pathlib.Path(folder_path).glob("**/*") if p.is_file()]
    for f in natsorted(files):
        file_path = ospath.join(folder_path, f)

        # Converting Video Files
        if CONVERT_VIDEOS and fileType(file_path) == "video":
            file_path = await videoConverter(file_path)

        leech = await sizeChecker(file_path, remove)

        if leech:  # File was splitted
            if ospath.exists(file_path) and remove:
                os.remove(file_path)  # Delete original Big Zip file

            dir_list = natsorted(os.listdir(temp_zpath))

            count = 1

            for dir_path in dir_list:
                short_path = ospath.join(temp_zpath, dir_path)
                file_name = ospath.basename(short_path)
                new_path = shortFileName(short_path)
                os.rename(short_path, new_path)
                start_time = datetime.now()
                current_time[0] = time.time()
                text_msg = f"<b>📤 UPLOADING SPLIT » {count} OF {len(dir_list)} Files</b>\n\n<code>{file_name}</code>\n"
                try:
                    msg = await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=msg.id,  # type: ignore
                        text=task_msg
                        + text_msg
                        + "\n⏳ __Starting.....__"
                        + sysINFO(),
                        reply_markup=keyboard(),
                    )
                except Exception as d:
                    print(d)
                await upload_file(new_path, file_name)
                up_bytes.append(os.stat(new_path).st_size)

                count += 1

            shutil.rmtree(temp_zpath)

        else:
            if not remove:  # Copy To Temp Dir for Renaming Purposes
                file_path = shutil.copy(file_path, temp_files_dir)
            file_name = ospath.basename(file_path)
            # Trimming filename upto 50 chars
            new_path = shortFileName(file_path)
            os.rename(file_path, new_path)
            start_time = datetime.now()
            current_time[0] = time.time()
            text_msg = f"<b>📤 UPLOADING » </b>\n\n<code>{file_name}</code>\n"
            try:
                msg = await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg.id,  # type: ignore
                    text=task_msg + text_msg + "\n⏳ __Starting.....__" + sysINFO(),
                    reply_markup=keyboard(),
                )
            except Exception as d:
                print(d)
            file_size = os.stat(new_path).st_size
            await upload_file(new_path, file_name)
            up_bytes.append(file_size)

            if remove:
                if ospath.exists(new_path):
                    os.remove(new_path)
            else:
                for file in os.listdir(temp_files_dir):
                    os.remove(ospath.join(temp_files_dir, file))

    if remove and ospath.exists(folder_path):
        shutil.rmtree(folder_path)
    if ospath.exists(thumbnail_ytdl):
        shutil.rmtree(thumbnail_ytdl)
    if ospath.exists(temp_files_dir):
        shutil.rmtree(temp_files_dir)


async def Zip_Handler(d_fol_path: str, is_split: bool, remove: bool):
    global msg, down_msg, start_time, total_down_size

    down_msg = f"<b>🔐 ZIPPING » </b>\n\n<code>{d_name}</code>\n"

    try:
        msg = await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.id,  # type: ignore
            text=task_msg + down_msg + sysINFO(),
        )
    except Exception as e2:
        print(f"Problem in ZipLeech !{e2}")

    print("\nNow ZIPPING the folder...")
    current_time[0] = time.time()
    start_time = datetime.now()
    if not ospath.exists(temp_zpath):
        makedirs(temp_zpath)
    await archive(d_fol_path, is_split, remove)
    clear_output()
    time.sleep(2)

    total_down_size = getSize(temp_zpath)

    if remove:
        if ospath.exists(d_fol_path):
            shutil.rmtree(d_fol_path)


async def Unzip_Handler(d_fol_path: str, remove: bool):
    global msg

    down_msg = f"\n<b>📂 EXTRACTING » </b>\n\n<code>{d_name}</code>\n"

    msg = await bot.edit_message_text(
        chat_id=chat_id,
        message_id=msg.id,  # type: ignore
        text=task_msg + down_msg + "\n⏳ __Starting.....__" + sysINFO(),
    )
    filenames = [str(p) for p in pathlib.Path(d_fol_path).glob("**/*") if p.is_file()]
    for f in natsorted(filenames):
        short_path = ospath.join(d_fol_path, f)
        if not ospath.exists(temp_unzip_path):
            makedirs(temp_unzip_path)
        filename = ospath.basename(f).lower()
        _, ext = ospath.splitext(filename)
        try:
            if ospath.exists(short_path):
                if ext in [".7z", ".gz", ".zip", ".rar", ".001", ".tar", ".z01"]:
                    await extract(short_path, remove)
                else:
                    shutil.copy(short_path, temp_unzip_path)
        except Exception as e5:
            print(f"UZLeech Launcher Exception: {e5}")

    if remove:
        shutil.rmtree(d_fol_path)


# =================================================================
#    Mode Handler Functions
# =================================================================


async def Do_Leech(source, is_dir, is_ytdl, is_zip, is_unzip, is_dualzip):
    global d_fol_path, msg, link_info, total_down_size

    if is_dir:
        for s in source:
            if not ospath.exists(s):
                raise Exception("Provided directory does not exist !")
            d_fol_path = s
            if is_zip:
                await Zip_Handler(d_fol_path, True, False)
                await Leech(temp_zpath, True)
            elif is_unzip:
                await Unzip_Handler(d_fol_path, False)
                await Leech(temp_unzip_path, True)
            elif is_dualzip:
                await Unzip_Handler(d_fol_path, False)
                await Zip_Handler(temp_unzip_path, True, True)
                await Leech(temp_zpath, True)
            else:
                if ospath.isdir(s):
                    await Leech(d_fol_path, False)
                else:
                    total_down_size = ospath.getsize(s)
                    name = ospath.basename(s)
                    await upload_file(s, name)
    else:
        await downloadManager(source, is_ytdl)

        total_down_size = getSize(d_fol_path)
        clear_output()

        # Renaming Files With Custom Name
        if len(custom_name) != 0 and TYPE not in ["Zip", "UnDoubleZip"]:
            files = os.listdir(d_fol_path)
            for file_ in files:
                current_name = ospath.join(d_fol_path, file_)
                new_name = ospath.join(d_fol_path, custom_name)
                os.rename(current_name, new_name)

        # Preparing To Upload
        if is_zip:
            await Zip_Handler(d_fol_path, True, True)
            await Leech(temp_zpath, True)
        elif is_unzip:
            await Unzip_Handler(d_fol_path, True)
            await Leech(temp_unzip_path, True)
        elif is_dualzip:
            print("Got into un doubled zip")
            await Unzip_Handler(d_fol_path, True)
            await Zip_Handler(temp_unzip_path, True, True)
            await Leech(temp_zpath, True)
        else:
            await Leech(d_fol_path, True)

    await FinalStep(msg, True)


async def Do_Mirror(source, is_ytdl, is_zip, is_unzip, is_dualzip):
    global d_fol_path, msg, link_info, total_down_size, temp_zpath, temp_unzip_path, mirror_dir

    try:
        if not ospath.exists("/content/drive"):
            drive.mount("/content/drive")
    except Exception as e:
        raise Exception(f"Failed to Mount Drive ! Because: {e}")

    if not ospath.exists(mirror_dir):
        makedirs(mirror_dir)

    await downloadManager(source, is_ytdl)

    total_down_size = getSize(d_fol_path)
    clear_output()

    if len(custom_name) != 0 and TYPE not in ["Zip", "UnDoubleZip"]:
        files = os.listdir(d_fol_path)
        for file_ in files:
            current_name = ospath.join(d_fol_path, file_)
            new_name = ospath.join(d_fol_path, custom_name)
            os.rename(current_name, new_name)

    cdt = datetime.now()
    cdt_ = cdt.strftime("Uploaded » %Y-%m-%d %H:%M:%S")
    mirror_dir_ = ospath.join(mirror_dir, cdt_)

    if is_zip:
        await Zip_Handler(d_fol_path, True, True)
        shutil.copytree(temp_zpath, mirror_dir_)
    elif is_unzip:
        await Unzip_Handler(d_fol_path, True)
        shutil.copytree(temp_unzip_path, mirror_dir_)
    elif is_dualzip:
        await Unzip_Handler(d_fol_path, True)
        await Zip_Handler(temp_unzip_path, True, True)
        shutil.copytree(temp_zpath, mirror_dir_)
    else:
        shutil.copytree(d_fol_path, mirror_dir_)

    await FinalStep(msg, False)


async def FinalStep(msg, is_leech: bool):
    final_text = (
        f"<b>☘️ File Count:</b>  <code>{len(sent_file)}</code>\n\n<b>📜 Logs:</b>\n"
    )
    l_ink = "⌬─────[「 Colab Usage 」](https://colab.research.google.com/drive/12hdEqaidRZ8krqj7rpnyDzg1dkKmvdvp)─────⌬"

    file_count = (
        f"├<b>☘️ File Count » </b><code>{len(sent_file)} Files</code>\n"
        if is_leech
        else ""
    )

    size = sizeUnit(sum(up_bytes)) if is_leech else sizeUnit(total_down_size)

    last_text = (
        f"\n\n<b>#{(MODE).upper()}_COMPLETE 🔥</b>\n\n"
        + f"╭<b>📛 Name » </b><code>{d_name}</code>\n"
        + f"├<b>📦 Size » </b><code>{size}</code>\n"
        + file_count
        + f"╰<b>🍃 Saved Time »</b> <code>{getTime((datetime.now() - task_start).seconds)}</code>"
    )

    await bot.send_message(
        chat_id=dump_id,
        text=f"**SOURCE »** __[Here]({src_link})__" + last_text,
        reply_to_message_id=sent.id,
    )

    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=msg.id,
        text=task_msg + l_ink + last_text,
        reply_markup=keyboard(),
    )

    if is_leech:
        try:
            final_texts = []
            for i in range(len(sent_file)):
                file_link = f"https://t.me/c/{link_p}/{sent_file[i].id}"
                fileName = sent_fileName[i]
                fileText = f"\n({str(i+1).zfill(2)}) <a href={file_link}>{fileName}</a>"
                if len(final_text + fileText) >= 4096:
                    final_texts.append(final_text)
                    final_text = fileText
                else:
                    final_text += fileText
            final_texts.append(final_text)

            for fn_txt in final_texts:
                msg = await bot.send_message(
                    chat_id=chat_id, reply_to_message_id=msg.id, text=fn_txt
                )
        except Exception as e:
            Err = f"<b>Error Sending logs » </b><i>{e}</i>"
            Err += f"\n\n<i>⚠️ If You are Unknown with this **ERROR**, Then Forward This Message in [Colab Leecher Discussion](https://t.me/Colab_Leecher_Discuss) Where [Xron Trix](https://t.me/XronTrix) may fix it</i>"
            await bot.send_message(
                chat_id=chat_id, reply_to_message_id=msg.id, text=Err
            )


# ****************************************************************
#    Main Functions, function calls and variable declarations
# ****************************************************************

custom_thumb = "/content/Thumbnail.jpg"
default_thumb = "/content/Telegram-Leecher/custom_thmb.jpg"
d_path, d_name, d_name, custom_name = "/content/bot_Folder", "", "", ""
mirror_dir = "/content/drive/MyDrive/Colab Leecher Uploads"
link_info, msg = False, None
d_fol_path = f"{d_path}/Downloads"
temp_zpath = f"{d_path}/Leeched_Files"
temp_unzip_path = f"{d_path}/Unzipped_Files"
temp_files_dir = f"{d_path}/dir_leech_temp"
thumbnail_ytdl = f"{d_path}/ytdl_thumbnails"
sent_file, sent_fileName, down_bytes = [], [], []
down_bytes.append(0)
ytdl_status = []
ytdl_status.append("")
ytdl_status.append("")
up_bytes = []
up_bytes.append(0)
current_time = []
current_time.append(time.time())
folder_info = [0, 1]
down_count = []
down_count.append(1)
start_time = datetime.now()
link, uz_pswd, z_pswd, text_msg = "something", "", "", ""
sources, service = [], None
is_dualzip, is_unzip, is_zip, is_ytdl, is_dir = (
    (TYPE == "UnDoubleZip"),
    (TYPE == "Unzip"),
    (TYPE == "Zip"),
    YTDL_DOWNLOAD_MODE,
    False,
)
caution_msg = "\n\n<i>💖 When I'm Doin This, Do Something Else ! <b>Because, Time Is Precious ✨</b></i>"
if CAPTION == "Regular":
    cap = "p"
elif CAPTION == "Bold":
    cap = "b"
elif CAPTION == "Italic":
    cap = "i"
elif CAPTION == "Monospace":
    cap = "code"
else:
    cap = "u"

try:
    if not thumbChecker():
        thumb_path = default_thumb
        print("Didn't find thumbnail, So switching to default thumbnail")
    else:
        thumb_path = custom_thumb
    if ospath.exists(d_path):
        shutil.rmtree(d_path)
        makedirs(d_path)
    else:
        makedirs(d_path)

    is_ytdl = YTDL_DOWNLOAD_MODE

    print(f"TASK MODE: {TYPE} {MODE} as {UPLOAD_MODE}")

    while link.lower() != "c":
        link = input(f"Download Source [ Enter 'C' to Terminate]: ")
        if link.lower() != "c":
            sources.append(link)

    if ENABLE_PASSWORD_SUPPORT:
        if TYPE == "Unzip" or TYPE == "UnDoubleZip":
            uz_pswd = input("Password For Unzip [ Enter 'E' for Empty ]: ")

        if TYPE == "Zip" or TYPE == "UnDoubleZip":
            z_pswd = input("Password For Zip [ Enter 'E' for Empty ]: ")

    if ENABLE_CUSTOM_FILE_NAME:
        if TYPE != "Unzip":
            custom_name = input("Enter Custom File name [ 'D' to set Default ]: ")
        else:
            print("Custom Name Not Applicable")

    uz_pswd = "" if uz_pswd.lower() == "e" else uz_pswd
    z_pswd = "" if z_pswd.lower() == "e" else z_pswd
    custom_name = "" if custom_name.lower() == "d" else custom_name

    task_start = datetime.now()
    down_msg = f"<b>📥 DOWNLOADING » </b>\n"
    task_msg = f"<b>🦞 TASK MODE » </b>"
    dump_task = (
        task_msg + f"<i>{TYPE} {MODE} as {UPLOAD_MODE}</i>\n\n<b>🖇️ SOURCES » </b>"
    )
    if MODE == "Dir-Leech":
        if not ospath.exists(sources[0]):
            raise ValueError(f"Directory Path is Invalid ! Provided: {sources[0]}")
        if not os.path.exists(temp_files_dir):
            makedirs(temp_files_dir)
        down_msg = f"<b>📤 UPLOADING » </b>\n"
        ida = "📂"
        is_dir = True
        dump_task += f"\n\n{ida} <code>{sources[0]}</code>"
    else:
        for link in sources:
            if "t.me" in link:
                ida = "💬"
            elif "drive.google.com" in link:
                service = build_service()
                ida = "♻️"
            elif "magnet" in link or "torrent" in link:
                ida = "🧲"
                caution_msg = "\n\n⚠️<i><b> Torrents Are Strictly Prohibited in Google Colab</b>, Try to avoid Magnets !</i>"
            elif "youtube.com" in link or "youtu.be" in link:
                ida = "🏮"
            else:
                ida = "🔗"
            dump_task += f"\n\n{ida} <code>{link}</code>"
    # Get the current date and time in the specified time zone
    cdt = datetime.now(pytz.timezone("Asia/Kolkata"))
    # Format the date and time as a string
    dt = cdt.strftime(" %d-%m-%Y")
    dump_task += f"\n\n<b>📆 Task Date » </b><i>{dt}</i>"
    if not ospath.exists(d_fol_path):
        makedirs(d_fol_path)
    api_id, chat_id, dump_id = int(API_ID), int(USER_ID), int(DUMP_ID)  # type: ignore
    link_p = str(dump_id)[4:]
    async with Client(  # type: ignore
        "my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN  # type: ignore
    ) as bot:
        sent = await bot.send_message(chat_id=dump_id, text=dump_task)  # type: ignore
        src_link = f"https://t.me/c/{link_p}/{sent.id}"
        task_msg += f"__[{TYPE} {MODE} as {UPLOAD_MODE}]({src_link})__\n\n"
        while True:
            try:
                msg = await bot.send_photo(  # type: ignore
                    chat_id=chat_id,
                    photo=thumb_path,
                    caption=task_msg
                    + down_msg
                    + f"\n📝 __Starting DOWNLOAD...__"
                    + sysINFO(),
                    reply_markup=keyboard(),
                )
            except Exception as e:
                pass
            else:
                break
        clear_output()
        if MODE == "Dir-Leech":
            folder_info[0] = getSize(sources[0])
            d_name = ospath.basename(sources[0])
        else:
            await calG_DownSize(sources)  # type: ignore
            await get_d_name(sources[0])  # type: ignore

        if TYPE == "Zip":
            d_fol_path = ospath.join(d_fol_path, d_name)
            if ospath.exists(d_fol_path):
                makedirs(d_fol_path)

        sources = natsorted(sources)
        current_time[0] = time.time()
        start_time = datetime.now()

        if MODE == "Mirror":
            await Do_Mirror(sources, is_ytdl, is_zip, is_unzip, is_dualzip)  # type: ignore
        else:
            await Do_Leech(sources, is_dir, is_ytdl, is_zip, is_unzip, is_dualzip)  # type: ignore


except Exception as e:
    clear_output()
    if ospath.exists(d_path):
        shutil.rmtree(d_path)

    if "400 PEER_ID_INVALID" in str(e):
        e = "Invalid USER_ID ! Enter your own Telegram USER ID in The Config Cell Correctly, Then Try Again"
    elif "Peer id invalid" in str(e):
        e = "Invalid DUMP_ID ! Enter CHAT ID of CHANNEL or GROUP starting with '-100' in The Config Cell Correctly, Then Try Again. Make sure you added the Bot in The Channel !"
    elif "Requested format is not available" in str(e):
        e = "Probably The Given Link is Not Supported by YTDL. Try Again Without YTDL !"

    Error_Text = (
        "⍟───── [Colab Leech](https://colab.research.google.com/drive/12hdEqaidRZ8krqj7rpnyDzg1dkKmvdvp) ─────⍟\n"
        + f"\n<b>TASK FAILED TO COMPLETE 💔</b>\n\n╭<b>📛 Name » </b> <code>{d_name}</code>\n├<b>🍃 Wasted Time » </b>"
        + f"__{getTime((datetime.now() - task_start).seconds)}__\n"  # type: ignore
        + f"<b>╰🤔 Reason » </b>__{e}__"
        + f"\n\n<i>⚠️ If You are Unknown with this **ERROR**, Then Forward This Message in [Colab Leecher Discussion](https://t.me/Colab_Leecher_Discuss) Where [Xron Trix](https://t.me/XronTrix) may fix it</i>"
    )

    async with Client(  # type: ignore
        "my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN  # type: ignore
    ) as bot:
        try:
            await bot.delete_messages(chat_id=chat_id, message_ids=msg.id)  # type: ignore
            await bot.send_photo(  # type: ignore
                chat_id=chat_id,  # type: ignore
                photo=thumb_path,  # type: ignore
                caption=task_msg + Error_Text,  # type: ignore
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(  # Opens a web URL
                                "Report Issue 🥺",
                                url="https://github.com/XronTrix10/Telegram-Leecher/issues",
                            ),
                            InlineKeyboardButton(  # Opens a web URL
                                "Group Discuss 🤔",
                                url="https://t.me/Colab_Leecher_Discuss",
                            ),
                        ],
                    ]
                ),
            )
        except Exception:
            pass

    print(f"Error Occured: {e}")
