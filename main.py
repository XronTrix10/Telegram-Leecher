import os
import shutil
import io
import pickle
import datetime
import time
import uvloop
from IPython.display import clear_output
from pyrogram import Client
from re import search as re_search
from urllib.parse import parse_qs, urlparse
from os import makedirs, path as ospath, listdir, remove as osremove
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload


uvloop.install()

# =================================================================
#    G Drive Functions
# =================================================================


# extract the file ID or folder ID from the link
def __getIdFromUrl(link: str):
    if "folders" in link or "file" in link:
        regex = r"https:\/\/drive\.google\.com\/(?:drive(.*?)\/folders\/|file(.*?)?\/d\/)([-\w]+)"
        res = re_search(regex, link)
        if res is None:
            raise IndexError("G-Drive ID not found.")
        return res.group(3)
    parsed = urlparse(link)
    return parse_qs(parsed.query)["id"][0]


def __getFilesByFolderId(folder_id):
    page_token = None
    files = []
    while True:
        response = (
            service.files()
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


def __getFileMetadata(file_id):
    return (
        service.files()
        .get(fileId=file_id, supportsAllDrives=True, fields="name, id, mimeType, size")
        .execute()
    )


def get_time():
    currentDateAndTime = datetime.datetime.now()
    currentTime = currentDateAndTime.strftime("%H:%M:%S")
    return currentTime


def size_measure(size):
    siz = ""
    if int(size) > 1024**4:
        siz = f"{int(size)/(1024**4):.2f} TB"
    elif int(size) > 1073741824:
        siz = f"{int(size)/(1024**3):.2f} GB"
    elif int(size) > 1048576:
        siz = f"{int(size)/(1024**2):.2f} MB"
    elif int(size) > 1024:
        siz = f"{int(size)/1024:.2f} KB"
    else:
        siz = f"{int(size)} B"
    return siz


def get_folder_size(folder_id):

    try:
        query = "trashed = false and '{0}' in parents".format(folder_id)
        results = (
            service.files()
            .list(
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                q=query,
                fields="nextPageToken, files(id, mimeType, size)",
            )
            .execute()
        )

        total_size = 0
        items = results.get("files", [])

        folders_without_size = []
        for item in items:
            # If the item is a folder and doesn't have a size attribute, call the function recursively
            if (item["mimeType"] == "application/vnd.google-apps.folder") and (
                item.get("size") is None
            ):
                folders_without_size.append(item["id"])
                continue

            # If the item has a size attribute
            if "size" in item:
                total_size += int(item["size"])
                folder_info[1] += 1
                continue

            # If none of the above condition is satisfied
            print(f"No size found for file/folder with ID '{item['id']}'")

        # Recursively call the function for folders whose size is not found
        for folder_id in folders_without_size:
            total_size += get_folder_size(folder_id)

        return total_size

    except HttpError as error:
        print(f"An error occurred: {error}")
        return -1


async def __down_Progress(file_size):

    down_done = sum(down_bytes) + file_size

    speed_string = ""

    if down_done > 0:
        elapsed_time_seconds = (datetime.datetime.now() - start_time).seconds
        down_speed = down_done / elapsed_time_seconds
        speed_string = f"{size_measure(down_speed)}/s"

    eta = (folder_info[0] - down_done) / down_speed
    eta = time.strftime("%Hh %Mm %Ss", time.gmtime(eta))

    down_msg = f"<b>📥 DOWNLOADING: {down_count[0]} OF {folder_info[1]} Files</b>\n\n<code>{d_name}</code>\n"

    percentage = round(down_done / folder_info[0] * 100, 2)
    bar_length = 14
    filled_length = int(percentage / 100 * bar_length)
    bar = "⬢" * filled_length + "⬡" * (bar_length - filled_length)
    message = f"\n[{bar}]  {percentage}%\n⚡️ __{speed_string}__  ⏳ ETA: {eta}\n✅ DONE: __{size_measure(down_done)}__ OF __{size_measure(folder_info[0])}__"
    try:
        print(message)
        # Edit the message with updated progress information.
        if is_time_over(current_time):
            await bot.edit_message_text(
                chat_id=chat_id, message_id=msg.id, text=down_msg + message
            )

    except Exception as e:
        # Catch any exceptions that might occur while editing the message.
        print(f"Error updating progress bar: {str(e)}")


async def __download_file(file_id, path):
    # Check if the specified file or folder exists and is downloadable.
    try:
        file = __getFileMetadata(file_id)
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
                file_name = os.path.join(path, file_name)
                # Create a BytesIO stream to hold the downloaded file data.
                file_contents = io.BytesIO()

                # Download the file or folder contents to the BytesIO stream.
                request = service.files().get_media(
                    fileId=file_id, supportsAllDrives=True
                )
                file_downloader = MediaIoBaseDownload(
                    file_contents, request, chunksize=50 * 1024 * 1024
                )
                done = False
                while done is False:
                    status, done = file_downloader.next_chunk()
                    print(f"Download progress: {int(status.progress() * 100)}%")
                    # Get current value from file_contents.
                    file_contents.seek(0)
                    with open(file_name, "ab") as f:
                        f.write(file_contents.getvalue())
                    # Reset the buffer for the next chunk.
                    file_contents.seek(0)
                    file_contents.truncate()
                    # The saved bytes till now
                    file_d_size = int(status.progress() * int(file["size"]))
                    print(f"Downloaded size: {size_measure(file_d_size)}")
                    await __down_Progress(file_d_size)

                print(f"DOWNLOADED  =>   {os.path.basename(file_name)}")
                down_bytes.append(int(file["size"]))
                down_count[0] += 1

            except Exception as e:
                print("Error downloading: {0}".format(e))


async def __download_folder(folder_id, path):

    folder_meta = __getFileMetadata(folder_id)
    folder_name = folder_meta["name"]
    if not ospath.exists(f"{path}/{folder_name}"):
        makedirs(f"{path}/{folder_name}")
    path += f"/{folder_name}"
    result = __getFilesByFolderId(folder_id)
    if len(result) == 0:
        return
    result = sorted(result, key=lambda k: k["name"])
    for item in result:
        file_id = item["id"]
        shortcut_details = item.get("shortcutDetails")
        if shortcut_details is not None:
            file_id = shortcut_details["targetId"]
            mime_type = shortcut_details["targetMimeType"]
        else:
            mime_type = item.get("mimeType")
        if mime_type == "application/vnd.google-apps.folder":
            await __download_folder(file_id, path)
        else:
            await __download_file(file_id, path)


# =================================================================
#    Telegram Upload Functions
# =================================================================


def get_file_type(file_path):
    name, extension = os.path.splitext(file_path)
    if extension in [".mp4", ".avi", ".mkv", ".mov", ".webm", ".m4v"]:
        video_extension_fixer(file_path)
        return "video"
    elif extension in [".mp3", ".wav", ".flac", ".aac", ".ogg"]:
        return "audio"
    elif extension in [".jpg", ".jpeg", ".png", ".gif"]:
        return "photo"
    else:
        return "document"


def video_extension_fixer(file_path):

    dir_path, filename = os.path.split(file_path)

    if filename.endswith(".mp4") or filename.endswith(".mkv"):
        pass
    # split the file name and the extension
    else:
        # rename the video file with .mp4 extension
        name, ext = os.path.splitext(filename)
        os.rename(
            os.path.join(dir_path, filename), os.path.join(dir_path, name + ".mp4")
        )
        print(f"{filename} was changed to {name}.mp4")


def create_zip(folder_path):
    folder_name = os.path.basename(folder_path)  # get folder name from folder path
    zip_file_path = folder_path  # create zip file path
    shutil.make_archive(
        zip_file_path, "zip", folder_path
    )  # create zip file by archiving the folder
    return zip_file_path + ".zip"  # return zip file path


async def size_checker(file_path):

    max_size = 2097152000  # 2 GB
    file_size = os.stat(file_path).st_size

    if file_size > max_size:

        print(f"File size is {size_measure(file_size)} SPLITTING.......")

        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.id,
            text=down_msg
            + f"\nSIZE: {size_measure(file_size)}\n\n<b>✂️ SPLITTING !</b>",
        )

        if not ospath.exists(d_fol_path):
            makedirs(d_fol_path)

        split_zipFile(file_path, max_size)

        return True
    else:

        print(f"File size is {file_size / (1024 * 1024):.2f} MB. NOT SPLITTING.......")
        return False


def split_zipFile(file_path, max_size):

    dir_path, filename = os.path.split(file_path)

    new_path = f"{d_fol_path}/{filename}"

    with open(file_path, "rb") as f:
        chunk = f.read(max_size)
        i = 1

        while chunk:
            # Generate filename for this chunk
            ext = str(i).zfill(3)
            output_filename = "{}.{}".format(new_path, ext)

            # Write chunk to file
            with open(output_filename, "wb") as out:
                out.write(chunk)

            # Get next chunk
            chunk = f.read(max_size)

            # Increment chunk counter
            i += 1


def is_time_over(current_time):
    ten_sec_passed = time.time() - current_time[0] >= 6
    if ten_sec_passed:
        current_time[0] = time.time()
    return ten_sec_passed


async def progress_bar(current, total):

    speed_string = ""

    if current > 0:
        elapsed_time_seconds = (datetime.datetime.now() - start_time).seconds
        upload_speed = current / elapsed_time_seconds
        speed_string = f"{size_measure(upload_speed)}/s"

    eta = (z_file_size - current - sum(up_bytes)) / upload_speed
    eta = time.strftime("%Hh %Mm %Ss", time.gmtime(eta))

    percentage = round((current + sum(up_bytes)) / z_file_size * 100, 2)
    bar_length = 14
    filled_length = int(percentage / 100 * bar_length)
    bar = "⬢" * filled_length + "⬡" * (bar_length - filled_length)
    message = f"\n[{bar}]  {percentage}%\n⚡️ __{speed_string}__ ⏳ ETA: {eta}\n✅ DONE: __{size_measure(current + sum(up_bytes))}__ OF __{size_measure(z_file_size)}__"
    try:
        print(message)
        # Edit the message with updated progress information.
        if is_time_over(current_time):
            await bot.edit_message_text(
                chat_id=chat_id, message_id=msg.id, text=text_msg + message
            )

    except Exception as e:
        # Catch any exceptions that might occur while editing the message.
        print(f"Error updating progress bar: {str(e)}")


async def upload_file(file_path, type, file_name):

    # Upload the file
    try:

        global sent

        caption = f"<code>{file_name}</code>"

        if type == "video":

            sent = await bot.send_video(
                chat_id=dump_id,
                video=file_path,
                supports_streaming=True,
                width=480,
                height=320,
                caption=caption,
                thumb=thumb_path,
                progress=progress_bar,
            )

        elif type == "audio":

            sent = await bot.send_audio(
                chat_id=dump_id,
                audio=file_path,
                supports_streaming=True,
                caption=caption,
                thumb=thumb_path,
                progress=progress_bar,
            )

        elif type == "document":

            sent = await sent.reply_document(
                document=file_path,
                caption=caption,
                thumb=thumb_path,
                progress=progress_bar,
                reply_to_message_id=sent.id
            )

        elif type == "photo":

            sent = await bot.send_photo(
                chat_id=dump_id,
                photo=file_path,
                caption=caption,
                progress=progress_bar,
            )

        clear_output()

        sent_file.append(sent)
        sent_fileName.append(file_name)
        print(f"\n{file_name} Sent !")

    except Exception as e:
        print(e)


# ****************************************************************
#    Main Functions, function calls and variable declarations
# ****************************************************************

link_p = str(dump_id)[4:]
# Replace THUMB_PATH with the path to your thumbnail file (optional)
thumb_path = "/content/thmb.jpg"
# Replace FILE_PATH with the path to your media file
d_path = "/content/Downloads"

sent_file = []
sent_fileName = []
down_bytes = []
down_bytes.append(0)
up_bytes = []
up_bytes.append(0)

current_time = []
current_time.append(time.time())

folder_info = []
folder_info.extend([0, 1])

down_count = []
down_count.append(1)


if not ospath.exists(d_path):
    makedirs(d_path)

# create credentials object from token.pickle file
creds = None
if os.path.exists("/content/token.pickle"):
    with open("/content/token.pickle", "rb") as token:
        creds = pickle.load(token)
else:
    exit(1)

# create drive API client
service = build("drive", "v3", credentials=creds)


# enter the link for the file or folder that you want to download
link = input("Enter the Google Drive link for the file or folder: ")

file_id = __getIdFromUrl(link)

meta = __getFileMetadata(file_id)

d_name = meta["name"]

d_fol_path = f"{d_path}/{d_name}"


async with Client(
    "my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token
) as bot:

    down_msg = f"<b>📥 DOWNLOADING: </b>\n\n<code>{d_name}</code>\n"

    try:
        msg = await bot.send_message(
            chat_id=chat_id, text=down_msg + f"\n📝 __Calculating DOWNLOAD SIZE...__"
        )
    except Exception as e:
        print(f"Can not {e} ")

    if meta.get("mimeType") == "application/vnd.google-apps.folder":
        folder_info[0] = get_folder_size(file_id)
    else:
        file_metadata = __getFileMetadata(file_id)
        # Get the file size from the metadata:
        folder_info[0] = int(file_metadata["size"])

    print(f"\nTotal Download size is: {size_measure(folder_info[0])}")

    # Determine if the ID is of file or folder
    if meta.get("mimeType") == "application/vnd.google-apps.folder":
        current_time[0] = time.time()
        start_time = datetime.datetime.now()
        await __download_folder(file_id, d_path)
        clear_output()
        print("*" * 40 + "\n Folder Download Complete\n" + "*" * 40)

    else:
        if not ospath.exists(d_fol_path):
            makedirs(d_fol_path)
        current_time[0] = time.time()
        start_time = datetime.datetime.now()
        await __download_file(file_id, d_fol_path)
        clear_output()
        print("*" * 40 + "\n File Download Complete\n" + "*" * 40)

    msg = await bot.edit_message_text(
        chat_id=chat_id,
        message_id=msg.id,
        text=f"\n<b>🔐 ZIPPING:</b>\n\n<code>{d_name}</code>\n",
    )

    print("\nNow Zipping the folder...")
    z_file_path = create_zip(d_fol_path)
    z_file_size = os.stat(z_file_path).st_size

    print(f"\nZip file saved as: {z_file_path}")

    shutil.rmtree(d_fol_path)
    print("\nDELETED Original Directory !\n")

    down_msg = f"\n<b>✅ Download COMPLETE:</b>\n\n<code>{d_name}</code>\n"

    leech = await size_checker(z_file_path)

    file_size = os.stat(z_file_path).st_size

    clear_output()

    if ospath.exists(d_fol_path):
        file_count = len(os.listdir(d_fol_path))
    else:
        file_count = 1

    dump_text = final_text = f"<b>📛 Name:</b>  <code>{d_name}</code>\n\n<b>📦 Size: {size_measure(z_file_size)}</b>\n\n<b>📂 Total Files:</b>  <code>{file_count}</code>\n"

    sent = await bot.send_photo(chat_id=dump_id, photo=thumb_path, caption=dump_text)

    if leech:  # File was splitted

        if ospath.exists(z_file_path):
            os.remove(z_file_path)  # Delete original Big Zip file
        print("Big Zip File Deleted !")
        # print('\nNow uploading multiple splitted zip files..........\n')

        dir_list = sorted(os.listdir(d_fol_path))

        count = 1

        for dir_path in dir_list:

            short_path = os.path.join(d_fol_path, dir_path)
            file_type = get_file_type(short_path)
            file_name = os.path.basename(short_path)
            print(f"\nNow uploading {file_name}\n")
            start_time = datetime.datetime.now()
            current_time[0] = time.time()
            text_msg = f"<b>📤 UPLOADING: {count} OF {len(dir_list)} Files</b>\n\n<code>{file_name}</code>\n"
            msg = await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg.id,
                text=text_msg + "\n⏳ __Starting.....__",
            )
            await upload_file(short_path, file_type, file_name)
            up_bytes.append(os.stat(short_path).st_size)

            count += 1

        shutil.rmtree(d_fol_path)

    else:

        file_type = get_file_type(z_file_path)
        file_name = os.path.basename(z_file_path)
        print(f"\nNow uploading {file_name}\n")
        start_time = datetime.datetime.now()
        current_time[0] = time.time()
        text_msg = f"<b>📤 UPLOADING: 1 File</b>\n\n<code>{file_name}</code>\n"
        msg = await bot.edit_message_text(
            chat_id=chat_id, message_id=msg.id, text=text_msg + "\n⏳ __Starting.....__"
        )
        await upload_file(z_file_path, file_type, file_name)

        os.remove(z_file_path)

    final_text = f"<b>📛 Name:</b>  <code>{d_name}</code>\n\n<b>📦 Size: {size_measure(z_file_size)}</b>\n\n<b>📂 Total Files:</b>  <code>{len(sent_file)}</code>\n"
    i = 0

    for sent in sent_file:

        file_link = f"https://t.me/c/{link_p}/{sent.id}"
        fileName = sent_fileName[i]
        fileText = f"\n{i+1}. <a href={file_link}>{fileName}</a>"
        final_text += fileText
        i += 1

    await bot.delete_messages(chat_id=chat_id, message_ids=msg.id)
    await bot.send_photo(chat_id=chat_id, photo=thumb_path, caption=final_text)
