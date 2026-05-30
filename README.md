![](https://user-images.githubusercontent.com/125879861/255391401-371f3a64-732d-4954-ac0f-4f093a6605e1.png)

<br>

<p align="center"><strong>「 A Pyrogram based Telegram Bot to Transfer Files / Folders to Telegram and Google Drive with the help of Google Colab With Multi-Functionality 」</strong></p>

<br>

## **📖 Click To Open The Notebook**

<a href="https://colab.research.google.com/github/ajithvnr2001/Telegram-Leecher/blob/feat/s3-integration/Telegram_Leecher.ipynb" target="_parent"><img src="https://user-images.githubusercontent.com/125879861/255389999-a0d261cf-893a-46a7-9a3d-2bb52811b997.png" alt="Open In Colab" width=200px/></a>

> The notebook is versioned in this repo as [`Telegram_Leecher.ipynb`](./Telegram_Leecher.ipynb) and the button above opens it in Colab directly from GitHub. The link currently targets the `feat/s3-integration` branch — once that branch is merged into `main`, swap the URL segment `blob/feat/s3-integration` → `blob/main`.

## **📚 In-depth guides**

- [Setup guide](./docs/SETUP.md) — Telegram, Google Drive and S3 credentials end-to-end
- [Bot commands reference](./docs/COMMANDS.md) — every command, every option
- [S3 / Wasabi / B2 deep dive](./docs/S3_GUIDE.md) — `/s3upload`, `/s3leech`, tracker file, multipart, examples
- [Troubleshooting](./docs/TROUBLESHOOTING.md) — common errors and fixes


## **⚡ 60-second quick start**

1. Click the **Open in Colab** badge above.
2. *(Optional)* Run the Drive-mount cell if you want to use `/gdupload`.
3. Fill the form fields (Telegram is required; the five S3 fields are only needed for `/s3upload` and `/s3leech`).
4. Run the main cell — wait for `Colab Leecher Started !`.
5. DM your bot on Telegram. Try `/help` for the full command list.

> **First time using S3?** See [SETUP.md → step 6](./docs/SETUP.md#6-optional-configure-s3--wasabi--b2) for endpoint examples for Wasabi, Backblaze B2, Cloudflare R2, DigitalOcean Spaces and MinIO.

## **🤖 Command summary**

| Command | What it does |
|---|---|
| `/tupload` | Leech links to Telegram |
| `/gdupload` | Mirror to Google Drive |
| `/ytupload` | Force the yt-dlp pipeline |
| `/drupload` | Leech a local Colab folder |
| `/s3upload` | **NEW** — Mirror downloads to your S3 / Wasabi bucket |
| `/s3leech` | **NEW** — Leech `s3://bucket/key` (or `s3://bucket/folder/`) to Telegram |
| `/s3bucket <name>` | **NEW** — Change destination S3 bucket on the fly |
| `/s3prefix <folder/sub>` | **NEW** — Set or clear destination key prefix |
| `/setname`, `/zipaswd`, `/unzipaswd` | Per-task name & passwords |
| `/settings` | Caption, thumbnail, prefix/suffix, video conversion |

Full reference (with sources, options, and examples for every command) lives in [COMMANDS.md](./docs/COMMANDS.md).


## 🎓 **How To Deploy**

<h3>Read the in-repo <a href="./docs/SETUP.md">Setup guide</a></h3>

<br>

<h3>Watch YouTube Tutorial</h3>

[![Watch It](https://img.youtube.com/vi/6LvYd-oO3U0/0.jpg)](https://www.youtube.com/watch?v=6LvYd-oO3U0)

## **💡 Features**

- Easy To Use With Bot Commands ( Update 🔥 )
- Powerful Video Converter, Convert Videos to mp4 / mkv ( New 🔥)
- Get Restricted Content From Telegram ( Beta Stage )
- Added Custom File Name Support 
- Download Multiple Files or Folders from Multiple Links 
- Support for Multi-Part Archive Extraction of all Type Extensions
- Upload Directly From Colab Container
- Auto Generate Thumbnail From Video Files 
- Download Directly To Google Drive / Mirroring
- Zip Folders/Files
- Split support for all files > 2GB/4GB

## **🔗 Supported Links**

- Direct Download Link ✅
- Google Drive Link ( Auto Authenticate ) ✅
- Telegram File Link ✅
- Video Links ( YouTube and 2000 More Sites 😉 ) ✅
- S3 / Wasabi / B2 Object URI ( `s3://bucket/key` ) ✅
- Torrent / Magnet Link ❌ ( Intentionally omitted 😔 )
- Mega.nz Link ❌ ( Coming Soon ♨️)
- GDTot, Sharer and Short Links ❌ ( Coming Soon ♨️)

## **☁️ S3 / Wasabi Integration**

Leech objects from S3-compatible storage to Telegram **and** mirror your downloads back to a configurable S3 bucket. Works with AWS, Wasabi, Backblaze B2, MinIO and any other S3-compatible service.

**Setup (in the Colab cell):**
- `S3_ACCESS_KEY` — your access key
- `S3_SECRET_KEY` — your secret key
- `S3_BUCKET_NAME` — default destination bucket
- `S3_ENDPOINT_URL` — leave empty for AWS, or e.g. `https://s3.ap-northeast-1.wasabisys.com` for Wasabi
- `S3_REGION` — defaults to `us-east-1`

**Bot commands:**
- `/s3upload` — Mirror downloads (from any source) to your S3 bucket. Honors all options: Regular / Compress / Extract / UnDoubleZip, custom name, zip & unzip passwords, and the same >2 GB pipeline as `/tupload`.
- `/s3leech` — Download object(s) from `s3://bucket/key` (or a prefix `s3://bucket/folder/`) and upload them to Telegram.
- `/s3bucket <name>` — Change the destination bucket at runtime.
- `/s3prefix <folder/sub>` — Set (or clear) a destination key prefix when mirroring TO S3.

**Tracker:** every transfer is appended to `/content/Telegram-Leecher/s3teletracker.json` with timestamp, file name, bucket, key, size and endpoint. Both `uploaded` (local→S3) and `downloaded` (S3→local) entries are recorded.

**Big files:** `boto3` performs multipart upload/download automatically beyond 64 MiB chunks, so files well above 2 GB transfer in a single command.

## **🔥 Benefits**

- No need of VPS or RDP
- Immersive Network speed in Google Servers
- Unlimited Storage in Telegram
- Upload Files of size up to 2000 MB
- Premium Upload up to 4000 MB ( Coming Soon ♨️)

## **🚀 UPTO 200 MiB/s Download Speed and 30 MiB/s Upload Speed**

![Image 1](https://user-images.githubusercontent.com/125879861/245217970-aa132967-c304-4b6d-a594-8c57a8f3d066.png)

## **🦉 Problems**

- You need to be aware of Runtime Disconnections
- Limited Disk Storage in Free Colab Account ~84 GB

## **🚨 NOTE:**

- Video Splitting is intentionally disabled to avoid video corruptions. Instead, they are zipped if they exceed MAX_UPLOAD_SIZE
<!-- - Magnet or Torrent Links are supported, But avoid using, because `Google Colab Strictly Prohibits Torrents` -->
- Downloading `YouTube Video without permission of the owner` can lead to copyright issues. Use with Caution

## **🤙🏼 Connect With Us**

<a href="https://t.me/Colab_Leecher" target="_parent"><img src="https://img.shields.io/badge/-Channel-blue?color=white&logo=telegram&logoColor=vlue"></a>

<a href="https://t.me/Colab_Leecher_Discuss" target="_parent"><img src="https://img.shields.io/badge/-Group-blue?color=white&logo=telegram&logoColor=vlue"></a>


## **⚖️ License**

<h4><a href="https://github.com/XronTrix10/Telegram-Leecher/blob/main/LICENSE">GPL-3.0 license</a></h4>

<br>

## **⚠️ You Should NOT use it as it goes against Google Colab's Policy**

> Resources in Colab are prioritized for interactive use cases. We prohibit actions associated with `bulk compute`, actions that negatively impact others, as well as actions associated with bypassing our policies. The following are disallowed from Colab runtime:
>
> - file hosting, `media serving`, or `other web service offerings not related to interactive compute with Colab`
> - `downloading torrents` or `engaging in peer-to-peer file-sharing`
> - using a remote desktop or SSH
> - connecting to remote proxies
> - mining cryptocurrency
> - running denial-of-service attacks
> - password cracking

<sub>Source: <a href="https://research.google.com/colaboratory/faq.html">Colab FAQ</a></sub>

<br>

<h3 align="center">Please Leave a 🌟 If this repo Helped you</h4>

<h4 align="center">Pull Requests are welcome 💗</h4>
