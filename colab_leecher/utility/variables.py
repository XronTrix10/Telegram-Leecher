# copyright 2023 © Xron Trix | https://github.com/Xrontrix10


from time import time
from datetime import datetime
from pyrogram.types import Message


class BOT:
    SOURCE = []

    class Setting:
        stream_upload = "Media"
        convert_video = "Yes"
        caption = "Monospace"
        prefix = ""
        thumbnail = False

    class Options:
        stream_upload = True
        convert_video = True
        caption = "code"
        video_out = "mp4"
        custom_name = ""
        zip_pswd = ""
        unzip_pswd = ""

    class Mode:
        mode = "leech"
        type = "normal"
        ytdl = False

    class State:
        started = False
        task_going = False
        prefix = False


class YTDL:
    header = ""
    info = ""


class Transfer:
    down_bytes = [0, 0]
    up_bytes = [0, 0]
    total_down_size = 0
    sent_file = []
    sent_file_names = []


class TaskError:
    state = False
    text = ""


class BotTimes:
    current_time = time()
    start_time = datetime.now()
    task_start = datetime.now()


class Paths:
    WORK_PATH = "/content/Telegram-Leecher/BOT_WORK"
    THMB_PATH = "/content/Telegram-Leecher/colab_leecher/Thumbnail.jpg"
    HERO_IMAGE = f"{WORK_PATH}/Hero.jpg"
    down_path = f"{WORK_PATH}/Downloads"
    temp_dirleech_path = f"{WORK_PATH}/dir_leech_temp"
    mirror_dir = "/content/drive/MyDrive/Colab Leecher Uploads"
    temp_zpath = f"{WORK_PATH}/Leeched_Files"
    temp_unzip_path = f"{WORK_PATH}/Unzipped_Files"
    temp_files_dir = f"{WORK_PATH}/dir_leech_temp"
    thumbnail_ytdl = f"{WORK_PATH}/ytdl_thumbnails"


class Messages:
    caution_msg = "\n\n<i>💖 When I'm Doin This, Do Something Else ! <b>Because, Time Is Precious ✨</b></i>"
    download_name = ""
    task_msg = ""
    status_head = f"<b>📥 DOWNLOADING » </b>\n"
    dump_task = ""
    src_link = ""
    link_p = ""


class MSG:
    start = Message(id=0)
    sent_msg = Message(id=1)
    status_msg = Message(id=2)



class Aria2c:
    link_info = False


class Gdrive:
    service = None
