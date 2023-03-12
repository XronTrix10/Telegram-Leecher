


def __gDrive_file(filee):
    size += int(filee.get("size", 0))


def __gDrive_directory(drive_folder):
    files = __getFilesByFolderId(drive_folder["id"])
    if len(files) == 0:
        return
    for filee in files:
        shortcut_details = filee.get("shortcutDetails")
        if shortcut_details is not None:
            mime_type = shortcut_details["targetMimeType"]
            file_id = shortcut_details["targetId"]
            filee = __getFileMetadata(file_id)
        else:
            mime_type = filee.get("mimeType")
        if mime_type == "application/vnd.google-apps.folder":
            __gDrive_directory(filee)
        else:
            __gDrive_file(filee)


size = 0