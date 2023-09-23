# copyright 2023 © Xron Trix | https://github.com/Xrontrix10


import io
import logging
import pickle
from natsort import natsorted
from re import search as re_search
from os import makedirs, path as ospath
from urllib.parse import parse_qs, urlparse
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from colab_leecher.utility.handler import cancelTask
from colab_leecher.utility.helper import sizeUnit, getTime, speedETA, status_bar
from colab_leecher.utility.variables import Gdrive, Messages, Paths, BotTimes, Transfer


async def build_service():
    global Gdrive
    if ospath.exists(Paths.access_token):
        with open(Paths.access_token, "rb") as token:
            creds = pickle.load(token)
            # Build the service
            Gdrive.service = build("drive", "v3", credentials=creds)
    else:
        await cancelTask(
            "token.pickle NOT FOUND ! Stop the Bot and Run the Google Drive Cell to Generate, then Try again !"
        )


async def g_DownLoad(link, num):
    global start_time, down_msg
    down_msg = f"<b>📥 DOWNLOADING FROM » </b><i>🔗Link {str(num).zfill(2)}</i>\n\n<b>🏷️ Name » </b><code>{Messages.download_name}</code>\n"
    file_id = await getIDFromURL(link)
    meta = getFileMetadata(file_id)

    if meta.get("mimeType") == "application/vnd.google-apps.folder":
        await gDownloadFolder(file_id, Paths.down_path)
    else:
        await gDownloadFile(file_id, Paths.down_path)


async def getIDFromURL(link: str):
    if "folders" in link or "file" in link:
        regex = r"https:\/\/drive\.google\.com\/(?:drive(.*?)\/folders\/|file(.*?)?\/d\/)([-\w]+)"
        res = re_search(regex, link)
        if res is None:
            await cancelTask("G-Drive ID not found in Link.")
            logging.error("G-Drive ID not found.")
            return
        else:
            return res.group(3)
    parsed = urlparse(link)
    return parse_qs(parsed.query)["id"][0]


def getFilesByFolderID(folder_id):
    page_token = None
    files = []
    while True:
        response = (
            Gdrive.service.files()  # type: ignore
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
        Gdrive.service.files()  # type: ignore
        .get(fileId=file_id, supportsAllDrives=True, fields="name, id, mimeType, size")
        .execute()
    )


def get_Gfolder_size(folder_id):
    try:
        query = "trashed = false and '{0}' in parents".format(folder_id)
        results = (
            Gdrive.service.files()  # type: ignore
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
        logging.error(f"Error while checking size: {error}")
        return -1


async def gDownloadFile(file_id, path):
    global TRANSFER_INFO
    # Check if the specified file or folder exists and is downloadable.
    try:
        file = getFileMetadata(file_id)
    except HttpError as error:
        err = "Sorry, the specified file or folder does not exist or is not accessible."
        logging.info(err)
        await cancelTask(err)
        return
    else:
        if file["mimeType"].startswith("application/vnd.google-apps"):
            err = "Sorry, the specified ID is for a Google Docs, Sheets, Slides, or Forms document. You can only download these types of files in specific formats."
            logging.info(err)
            await cancelTask(err)
            return
        else:
            try:
                file_name = file.get("name", f"untitleddrivefile_{file_id}")
                file_name = ospath.join(path, file_name)
                # Create a BytesIO stream to hold the downloaded file data.
                file_contents = io.BytesIO()

                # Download the file or folder contents to the BytesIO stream.
                request = Gdrive.service.files().get_media(  # type: ignore
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
                    down_done = sum(Transfer.down_bytes) + file_d_size
                    speed_string, eta, percentage = speedETA(
                        BotTimes.task_start, down_done, Transfer.total_down_size
                    )
                    await status_bar(
                        down_msg=down_msg,
                        speed=speed_string,
                        percentage=percentage,
                        eta=getTime(eta),
                        done=sizeUnit(down_done),
                        left=sizeUnit(Transfer.total_down_size),
                        engine="G-Api ♻️",
                    )
                Transfer.down_bytes.append(int(file["size"]))

            except HttpError as error:
                if error.resp.status == 403 and "User Rate Limit Exceeded" in str(
                    error
                ):
                    logging.error("Download quota for the file has been exceeded.")
                    await cancelTask("Download quota for the file has been exceeded.")
                    return
                else:
                    logging.error("HttpError While Downloading: {0}".format(error))
                    await cancelTask("HttpError While Downloading: {0}".format(error))
                    return

            except Exception as e:
                logging.error("Error downloading: {0}".format(e))
                await cancelTask("Error downloading: {0}".format(e))
                return


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
