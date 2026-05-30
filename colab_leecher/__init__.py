# copyright 2023 © Xron Trix | https://github.com/Xrontrix10

import logging, json, asyncio
from uvloop import install
from pyrogram.client import Client

# Read the dictionary from the txt file
with open("/content/Telegram-Leecher/credentials.json", "r") as file:
    credentials = json.loads(file.read())

API_ID = credentials["API_ID"]
API_HASH = credentials["API_HASH"]
BOT_TOKEN = credentials["BOT_TOKEN"]
OWNER = credentials["USER_ID"]
DUMP_ID = credentials["DUMP_ID"]

# S3 / Wasabi config (optional — used by /s3upload and /s3leech)
S3_ACCESS_KEY = credentials.get("S3_ACCESS_KEY", "") or ""
S3_SECRET_KEY = credentials.get("S3_SECRET_KEY", "") or ""
S3_BUCKET_NAME = credentials.get("S3_BUCKET_NAME", "") or ""
S3_ENDPOINT_URL = credentials.get("S3_ENDPOINT_URL", "") or ""
S3_REGION = credentials.get("S3_REGION", "") or "us-east-1"


logging.basicConfig(level=logging.INFO)

install()

# Fix for Python 3.12+ — uvloop.install() replaces the event loop policy but does NOT
# create an event loop. In Python 3.12+ asyncio.get_event_loop() raises RuntimeError if
# there is no running loop in the current thread. We must explicitly create one BEFORE
# instantiating Pyrogram's Client (whose Dispatcher.__init__ calls get_event_loop()).
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

colab_bot = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
