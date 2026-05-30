# copyright 2023 © Xron Trix | https://github.com/Xrontrix10


import os
import json
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
    fileType,
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
            f_type = fileType(file_path)
            if f_type == "video" and BOT.Options.is_split:
                # TODO: Store the size in a constant variable
                await splitVideo(file_path, 2000, remove)
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
    total_size = getSize(path)
    total_in_unit = sizeUnit(total_size)
    while proc.poll() is None:
        speed_string, eta, percentage = speedETA(
            BotTimes.task_start, getSize(Paths.temp_zpath), total_size
        )
        await status_bar(
            Messages.status_head,
            speed_string,
            percentage,
            getTime(eta),
            sizeUnit(getSize(Paths.temp_zpath)),
            total_in_unit,
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


async def splitVideo(file_path, max_size, remove: bool):
    """Split a video into parts that are EACH guaranteed <= the Telegram cap.

    `max_size` is the per-part cap in MiB (e.g. 2000 → 2000 MiB = 2 GB).

    The old implementation computed the segment duration from ffprobe's
    reported ``format.bit_rate``, which is often missing or under-reported.
    When the bitrate read low, the derived ``segment_time`` was too long and
    ffmpeg produced fewer, OVERSIZED parts (e.g. a 5 GiB file → 2 parts of
    ~2.5 GiB), each of which exceeds Telegram's 2 GB limit and fails to
    upload — so the file was never delivered completely.

    This version:
      1. Derives the segment time from the ACTUAL file size and duration
         (reliable), not the reported bitrate.
      2. Targets ~94% of the cap so keyframe-aligned cuts stay under it.
      3. VERIFIES every produced part and, if any part still exceeds the
         cap (or ffmpeg produced nothing), falls back to a guaranteed raw
         byte-split so no part is ever larger than the limit.
    """
    global Paths, BOT, MSG, Messages
    _, filename = ospath.split(file_path)
    just_name, extension = ospath.splitext(filename)

    total_size = ospath.getsize(file_path)
    # Telegram hard cap for a single part, in bytes.
    max_part_bytes = int(max_size) * 1024 * 1024

    Messages.status_head = f"<b>✂️ SPLITTING » </b>\n\n<code>{filename}</code>\n"
    BotTimes.task_start = datetime.now()

    # --- determine total duration (seconds) — reliable, unlike bit_rate ---
    duration_total = 0.0
    try:
        output = subprocess.check_output(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", file_path]
        )
        duration_total = float(json.loads(output)["format"].get("duration", 0) or 0)
    except Exception as e:
        logging.error(f"splitVideo: could not read duration ({e})")
        duration_total = 0.0

    use_raw_fallback = False

    if duration_total <= 0 or total_size <= 0:
        # Can't time-segment reliably → guaranteed raw byte split.
        use_raw_fallback = True
    else:
        # Variable-bitrate (VBR) content — e.g. 4K AV1 movies — has bitrate
        # peaks far above the average. A single attempt at 94% of the cap can
        # still produce an oversized segment if a high-bitrate scene lands in
        # one part. So we try progressively smaller per-part targets and
        # re-verify each time; the first attempt whose parts are ALL within
        # the cap wins. If none succeed we drop to the raw byte-split.
        out_pattern = f"{Paths.temp_zpath}/{just_name}.part%03d{extension}"
        total_in_unit = sizeUnit(total_size)

        def _clear_parts():
            for f in os.listdir(Paths.temp_zpath):
                if f.startswith(just_name + ".part"):
                    try:
                        os.remove(ospath.join(Paths.temp_zpath, f))
                    except OSError:
                        pass

        success = False
        for target_ratio in (0.94, 0.85, 0.72, 0.60):
            _clear_parts()
            target_bytes = int(max_part_bytes * target_ratio)
            seg_time = max(1, int(duration_total * target_bytes / total_size))

            # -map 0 keeps every audio/subtitle track (important for movies).
            cmd = (
                f'ffmpeg -i "{file_path}" -c copy -map 0 -f segment '
                f'-segment_time {seg_time} -reset_timestamps 1 "{out_pattern}"'
            )
            Messages.status_head = (
                f"<b>✂️ SPLITTING » </b>\n\n<code>{filename}</code>\n"
                f"<i>target {int(target_ratio*100)}% of cap, ~{seg_time}s/part</i>\n"
            )
            BotTimes.task_start = datetime.now()
            proc = subprocess.Popen(cmd, shell=True)
            while proc.poll() is None:
                speed_string, eta, percentage = speedETA(
                    BotTimes.task_start, getSize(Paths.temp_zpath), total_size
                )
                await status_bar(
                    Messages.status_head,
                    speed_string,
                    percentage,
                    getTime(eta),
                    sizeUnit(getSize(Paths.temp_zpath)),
                    total_in_unit,
                    "Xr-Split ✂️",
                )
                await sleep(1)

            # --- verify: every produced part must be within the cap ---
            produced = [
                ospath.join(Paths.temp_zpath, f)
                for f in os.listdir(Paths.temp_zpath)
                if f.startswith(just_name + ".part")
            ]
            oversized = [p for p in produced if ospath.getsize(p) > max_part_bytes]
            if produced and not oversized:
                logging.info(
                    f"splitVideo: OK at {int(target_ratio*100)}% target → "
                    f"{len(produced)} part(s), largest "
                    f"{max(ospath.getsize(p) for p in produced)/1024**3:.2f} GiB"
                )
                success = True
                break
            logging.warning(
                f"splitVideo: {int(target_ratio*100)}% target produced "
                f"{len(produced)} part(s) with {len(oversized)} over the "
                f"{max_size} MiB cap — retrying smaller."
            )

        if not success:
            _clear_parts()
            use_raw_fallback = True

    if use_raw_fallback:
        # Raw byte split: parts are EACH exactly <= max_part_bytes. They are
        # not individually playable but reassemble with `cat parts* > file`.
        await splitArchive(file_path, max_part_bytes)

    if remove and ospath.exists(file_path):
        os.remove(file_path)
