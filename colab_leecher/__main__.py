# copyright 2023 © Xron Trix | https://github.com/Xrontrix10


import logging, shutil
from pyrogram import filters
from datetime import datetime
from asyncio import sleep, get_event_loop
from colab_leecher import colab_bot, OWNER
from .utility.task_manager import taskScheduler
from .utility.variables import BOT, MSG, BotTimes, Messages, Paths
from .utility.helper import getTime, isLink, setThumbnail, message_deleter
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

src_request_msg = None
task = None


@colab_bot.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.delete()
    text = "**Hey There, 👋🏼**\n\nI am a Powerful File Tranloading Bot 🚀\nI can Download and Upload Files To Telegram or Your Google Drive From Various Sources 🦐\n\nSend /help for more information on how to use me 🙃"
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Repository", url="https://github.com/XronTrix10/Telegram-Leecher"
                )
            ],
        ]
    )
    await message.reply_text(text, reply_markup=keyboard)


@colab_bot.on_message(filters.command("colabxr") & filters.private)
async def colabxr(client, message):
    global BOT, src_request_msg
    text = "<b>Please Send me a DOWNLOAD LINK / BULK LINKS:</b>\n\n<b>SUPPORTED LINKS ARE:</b>\n1. <code>Direct Links</code>\n2. <code>drive.google.com</code>\n3. <code>Telegram(t.me/)</code>\n4. <code>Torrent/Magnet</code>\n5. <code>Video Links (i.e, YouTube)</code>\n"
    if message.chat.id == OWNER:
        await message.delete()
        BOT.State.started = True
        if BOT.State.task_going == False:
            src_request_msg = await message.reply_text(text)
        else:
            msg = await message.reply_text(
                "I am Already Working ! Please Wait Until I finish !!"
            )
            await sleep(15)
            await msg.delete()
    else:
        await message.reply_text(
            "Please Deploy Your Own Bot. [Repo Link](https://github.com/XronTrix10/Telegram-Leecher)"
        )


async def send_settings(client, message, msg_id, command: bool):
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Upload Mode", callback_data="upload_mode"),
                InlineKeyboardButton("Video Convert", callback_data="video"),
            ],
            [
                InlineKeyboardButton("Caption Style", callback_data="caption"),
                InlineKeyboardButton("Set Prefix", callback_data="set-prefix"),
            ],
            [InlineKeyboardButton("Close", callback_data="close")],
        ]
    )
    text = "**CURRENT BOT SETTINGS ⚙️**"
    text += f"\n\nUPLOAD BOT: <code>{BOT.Setting.stream_upload}</code>"
    text += f"\nCONVERT VIDEO: <code>{BOT.Setting.convert_video}</code>"
    text += f"\nVIDEO OUT: <code>{BOT.Options.video_out}</code>"
    text += f"\nCAPTION: <code>{BOT.Setting.caption}</code>"
    pr = "None" if BOT.Setting.prefix == "" else "Exists"
    thmb = "None" if not BOT.Setting.thumbnail else "Exists"
    text += f"\nPREFIX: <code>{pr}</code>\nTHUMBNAIL: <code>{thmb}</code>"
    if command:
        await message.reply_text(text=text, reply_markup=keyboard)
    else:
        await colab_bot.edit_message_text(
            chat_id=message.chat.id, message_id=msg_id, text=text, reply_markup=keyboard
        )


@colab_bot.on_message(filters.command("settings") & filters.private)
async def settings(client, message):
    if message.chat.id == OWNER:
        await message.delete()
        await send_settings(client, message, message.id, True)


@colab_bot.on_message(filters.reply)
async def setPrefix(client, message):
    global BOT, SETTING
    if BOT.State.prefix:
        BOT.Setting.prefix = message.text
        BOT.State.prefix = False

        await send_settings(client, message, message.reply_to_message_id, False)
        await message.delete()


@colab_bot.on_message(filters.create(isLink) & ~filters.photo)
async def handle_url(client, message):
    global BOT
    if message.chat.id == OWNER:
        if src_request_msg:
            await src_request_msg.delete()
        if BOT.State.task_going == False and BOT.State.started:
            BOT.SOURCE = message.text.split()
            keyboard = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Leech", callback_data="leech")],
                    [InlineKeyboardButton("Mirror", callback_data="mirror")],
                    [InlineKeyboardButton("Dir-Leech", callback_data="dir-leech")],
                ]
            )
            await message.reply_text(
                text="Choose Operation BOT:", reply_markup=keyboard, quote=True
            )
        elif BOT.State.started:
            await message.delete()
            await message.reply_text(
                "I am Already Working ! Please Wait Until I finish !!"
            )

    else:
        await message.reply_text(
            "Please Deploy Your Own Bot. [Repo Link](https://github.com/XronTrix10/Telegram-Leecher)",
            disable_web_page_preview=True,
        )


@colab_bot.on_callback_query()
async def handle_options(client, callback_query):
    global BOT, task

    if callback_query.data in ["leech", "mirror", "dir-leech"]:
        BOT.Mode.mode = callback_query.data
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Normal", callback_data="normal")],
                [
                    InlineKeyboardButton("Zip", callback_data="zip"),
                    InlineKeyboardButton("Unzip", callback_data="unzip"),
                    InlineKeyboardButton("UnDoubleZip", callback_data="undzip"),
                ],
            ]
        )
        await callback_query.message.edit_text(
            f"Tell me the type of {BOT.Mode.mode} you want:", reply_markup=keyboard
        )
    elif callback_query.data in ["normal", "zip", "unzip", "undzip"]:
        BOT.Mode.type = callback_query.data
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Yes", callback_data="ytdl-true")],
                [InlineKeyboardButton("No", callback_data="ytdl-false")],
            ]
        )
        await callback_query.message.edit_text(
            "Is it a YTDL Link ?", reply_markup=keyboard
        )
    elif callback_query.data == "upload_mode":
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Media", callback_data="media")],
                [InlineKeyboardButton("Document", callback_data="document")],
            ]
        )
        await callback_query.message.edit_text(
            "Choose Upload Mode:", reply_markup=keyboard
        )
    elif callback_query.data == "video":
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Convert", callback_data="convert-true"),
                    InlineKeyboardButton(
                        "Don't Convert", callback_data="convert-false"
                    ),
                ],
                [
                    InlineKeyboardButton("MP4", callback_data="mp4"),
                    InlineKeyboardButton("MKV", callback_data="mkv"),
                ],
            ]
        )
        await callback_query.message.edit_text(
            f"CHOOSE YOUR DESIRED BOT ⚙️:\n\nOUTPUT VIDEO: <code>{BOT.Options.video_out}</code>",
            reply_markup=keyboard,
        )
    elif callback_query.data == "caption":
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Monospace", callback_data="code-Monospace")],
                [InlineKeyboardButton("Regular", callback_data="p-Regular")],
                [InlineKeyboardButton("Bold", callback_data="b-Bold")],
                [InlineKeyboardButton("Italic", callback_data="i-Italic")],
                [InlineKeyboardButton("Underlined", callback_data="u-Underlined")],
            ]
        )
        await callback_query.message.edit_text(
            "Choose Your Caption Style:", reply_markup=keyboard
        )
    elif callback_query.data == "close":
        await callback_query.message.delete()
    elif callback_query.data == "set-prefix":
        await callback_query.message.edit_text(
            "Send a Text to Set as PREFIX by REPLYING THIS MESSAGE:"
        )
        BOT.State.prefix = True
    elif callback_query.data in [
        "code-Monospace",
        "p-Regular",
        "b-Bold",
        "i-Italic",
        "u-Underlined",
    ]:
        res = callback_query.data.split("-")
        BOT.Options.caption = res[0]
        BOT.Setting.caption = res[1]
        await send_settings(
            client, callback_query.message, callback_query.message.id, False
        )
    elif callback_query.data in ["convert-true", "convert-false", "mp4", "mkv"]:
        if callback_query.data in ["convert-true", "convert-false"]:
            BOT.Options.convert_video = (
                True if callback_query.data == "convert-true" else False
            )
            BOT.Setting.convert_video = (
                "Yes" if callback_query.data == "convert-true" else "No"
            )
        else:
            BOT.Options.video_out = callback_query.data
        await send_settings(
            client, callback_query.message, callback_query.message.id, False
        )
    elif callback_query.data in ["media", "document"]:
        BOT.Options.stream_upload = True if callback_query.data == "media" else False
        BOT.Setting.stream_upload = (
            "Media" if callback_query.data == "media" else "Document"
        )
        await send_settings(
            client, callback_query.message, callback_query.message.id, False
        )

    # @main Triggering Actual Leech Functions
    elif callback_query.data in ["ytdl-true", "ytdl-false"]:
        BOT.Mode.ytdl = True if callback_query.data == "ytdl-true" else False
        await callback_query.message.delete()
        await colab_bot.delete_messages(
            chat_id=callback_query.message.chat.id,
            message_ids=callback_query.message.reply_to_message_id,
        )
        MSG.start = await colab_bot.send_message(
            chat_id=OWNER, text="**Starting your task...🦐**"
        )
        BOT.State.task_going = True
        BOT.State.started = False
        BotTimes.start_time = datetime.now()
        event_loop = get_event_loop()
        task = event_loop.create_task(taskScheduler())
        await task
        BOT.State.task_going = False


    # If user Wants to Stop The Task
    elif callback_query.data == "cancel":
        text = f"#TASK_STOPPED\n\n**╭🔗 Source » **__[Here]({Messages.src_link})__\n**├🤔 Reason » **__User cancelled__\n╰🍃 Spent Time » **__{getTime((datetime.now() - BotTimes.start_time).seconds)}__"
        if BOT.State.task_going:
            try:
                task.cancel()  # type: ignore
                shutil.rmtree(Paths.WORK_PATH)
            except Exception as e:
                logging.error(f"Error Deleting Task Folder: {e}")
            else:
                logging.info(f"Going Task Cancelled !")
            finally:
                BOT.State.task_going = False
                await MSG.status_msg.delete()
                await colab_bot.send_message(
                    chat_id=OWNER,
                    text=text,
                    reply_markup=InlineKeyboardMarkup(
                        [
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
                    ),
                )


@colab_bot.on_message(filters.photo & filters.private)
async def handle_image(client, message):
    success = await setThumbnail(message)
    if success:
        msg = await message.reply_text(
            f"**Thumbnail Successfully Changed ✅**", quote=True
        )
        await message.delete()
    else:
        msg = await message.reply_text(
            f"Couldn't Set Thumbnail ! Try Again !", quote=True
        )
    await sleep(15)
    await message_deleter(message, msg)


@colab_bot.on_message(filters.command("setname") & filters.private)
async def custom_name(client, message):
    global BOT
    if len(message.command) != 2:
        msg = await message.reply_text(
            "Send\n/setname <code>custom_fileame.extension</code>\nTo Set Custom File Name 📛",
            quote=True,
        )
    else:
        BOT.Options.custom_name = message.command[1]
        msg = await message.reply_text(
            "Custom Name Has Been Successfully Set !", quote=True
        )

    await sleep(15)
    await message_deleter(message, msg)


@colab_bot.on_message(filters.command("zipaswd") & filters.private)
async def zip_pswd(client, message):
    global BOT
    if len(message.command) != 2:
        msg = await message.reply_text(
            "Send\n/zipaswd <code>password</code>\nTo Set Password for Output Zip File. 🔐",
            quote=True,
        )
    else:
        BOT.Options.zip_pswd = message.command[1]
        msg = await message.reply_text(
            "Zip Password Has Been Successfully Set !", quote=True
        )

    await sleep(15)
    await message_deleter(message, msg)


@colab_bot.on_message(filters.command("unzipaswd") & filters.private)
async def unzip_pswd(client, message):
    global BOT
    if len(message.command) != 2:
        msg = await message.reply_text(
            "Send\n/unzipaswd <code>password</code>\nTo Set Password for Extracting Archives. 🔓",
            quote=True,
        )
    else:
        BOT.Options.unzip_pswd = message.command[1]
        msg = await message.reply_text(
            "Unzip Password Has Been Successfully Set !", quote=True
        )

    await sleep(15)
    await message_deleter(message, msg)


@colab_bot.on_message(filters.command("help") & filters.private)
async def help_command(client, message):
    msg = await message.reply_text(
        "Send /start To Check If I am alive 🤨\n\nSend /colabxr and follow prompts to start transloading 🚀\n\nSend /settings to edit bot settings ⚙️\n\nSend /setname To Set Custom File Name 📛\n\nSend /zipaswd To Set Password For Zip File 🔐\n\nSend /unzipaswd To Set Password to Extract Archives 🔓\n\n⚠️ **You can ALWAYS SEND an image To Set it as THUMBNAIL for your files 🌄**",
        quote=True,
    )
    await sleep(15)
    await message_deleter(message, msg)


BotTimes.start_time = datetime.now()
logging.info("Colab Leecher Started !")
colab_bot.run()
