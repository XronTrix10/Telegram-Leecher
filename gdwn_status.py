import os
import pickle
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build


def size_measure(size):
    siz = ""
    if int(size) > 1073741824:
        siz = f"{int(size)/(1024**3):.2f} GB"
    elif int(size) > 1048576:
        siz = f"{int(size)/(1024**2):.2f} MB"
    elif int(size) > 1024:
        siz = f"{int(size)/1024:.2f} KB"
    else:
        siz = f"{int(size)} B"
    return siz


def get_folder_size(folder_id, service):

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
                continue

            # If none of the above condition is satisfied
            print(f"No size found for file/folder with ID '{item['id']}'")

        # Recursively call the function for folders whose size is not found
        for folder_id in folders_without_size:
            total_size += get_folder_size(folder_id, service)

        return total_size

    except HttpError as error:
        print(f"An error occurred: {error}")
        return -1


if __name__ == "__main__":
    # create credentials object from token.pickle file
    creds = None
    if os.path.exists("/content/token.pickle"):
        with open("/content/token.pickle", "rb") as token:
            creds = pickle.load(token)
    else:
        exit(1)

    # create drive API client
    service = build("drive", "v3", credentials=creds)

    folder_id = "1GzH4vZNFjP6__Zt6I-URg4ky_BU0LN21"
    folder_size = get_folder_size(folder_id, service)

    siz = size_measure(folder_size)

    print(f"The size of the folder with ID {folder_id} is {siz}")
