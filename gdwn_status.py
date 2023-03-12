from __future__ import print_function
import io
import os.path
import pickle
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaIoBaseDownload

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


# define your file id and credentials location
file_id = '10zlXfCPKubJtvp7A1vMNxuttc1YaQ9E4'
creds_path = '/content/token.pickle'

# set up the API client
creds = None
if os.path.exists(creds_path):
    with open(creds_path, 'rb') as token:
        creds = pickle.load(token)
service = build('drive', 'v3', credentials=creds)

# get the file metadata
try:
    file = service.files().get(fileId=file_id, supportsAllDrives=True, fields="name, id, mimeType, size").execute()
except HttpError as error:
    print(f'An error occurred: {error}')
    file = None

# create a file object to write the data to
filename = file['name']
fd = io.BytesIO()

# download the file data
if file:
    try:
        request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
        downloader = MediaIoBaseDownload(fd, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            downloaded_bytes = int(status.progress() * int(file['size']))
            if status:
                progress_percent = int(status.progress() * 100)
                print(f'Downloading {filename}: {progress_percent}% complete')
                print(f'Download progress: {size_measure(downloaded_bytes)} / {size_measure(file["size"])}\n')
    except HttpError as error:
        print(f'An error occurred: {error}')

# write the downloaded data to a file
with open(filename, 'wb') as f:
    f.write(fd.getbuffer())
print(f'Successfully saved {filename}!')
