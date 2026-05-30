# Setup Guide

End-to-end setup for Telegram-Leecher in Google Colab. Skip the sections you don't need (Drive and S3 are both optional).

---

## 1. Prerequisites

- A Telegram account
- A Google account (for Colab and, optionally, Drive mirroring)
- Optional: an S3-compatible bucket (AWS, **Wasabi**, Backblaze B2, MinIO, etc.) for `/s3upload` and `/s3leech`

---

## 2. Create your Telegram bot

1. Open [@BotFather](https://t.me/BotFather) on Telegram → `/newbot` → follow the prompts.
2. Save the **bot token** BotFather returns. This is your `BOT_TOKEN`.
3. Visit <https://my.telegram.org> → log in → **API development tools** → create an app.
4. Save **api_id** and **api_hash** — these are `API_ID` and `API_HASH`.
5. Find your numeric Telegram user id (send any message to [@userinfobot](https://t.me/userinfobot)). This is `USER_ID`.

---

## 3. Create a private dump channel

This is where the bot mirrors source links and sends task logs.

1. In Telegram → **New Channel** → Private.
2. Add your bot as **Administrator** (give it post permission).
3. Forward any message from the channel to [@userinfobot](https://t.me/userinfobot) to read its chat id (a 13-digit number starting with `-100`).
4. That number is your `DUMP_ID`. The cell auto-prefixes `-100` if you provide just the 10-digit suffix.

---

## 4. Open the Colab notebook

Click the **Open in Colab** badge in the [README](../README.md). The notebook has three cells:

1. **Markdown intro** — instructions and S3 endpoint examples.
2. **Drive mount cell** — only needed for `/gdupload`. Skip if you don't mirror to Drive.
3. **Main form cell** — fill in credentials, then run.

---

## 5. (Optional) Mount Google Drive

If you plan to use `/gdupload`:

```python
from google.colab import drive
drive.mount('/content/drive')
```

A browser tab opens for you to authorize. Drive is mounted at `/content/drive`. The bot writes mirrored files under `/content/drive/MyDrive/Colab Leecher Uploads/`.

> If Drive isn't mounted, `/gdupload` shows an error and asks you to mount it before retrying. `/tupload`, `/s3upload`, etc. don't need Drive.

---

## 6. (Optional) Configure S3 / Wasabi / B2

Skip this entire section if you don't plan to use S3.

Fill these five form fields:

| Field | Description | Example |
|---|---|---|
| `S3_ACCESS_KEY` | Access key from your provider | `FYTCJCK1EKLWD30D8707` |
| `S3_SECRET_KEY` | Secret key from your provider | `bKyeNjq8U0L8SrnARG…` |
| `S3_BUCKET_NAME` | Default destination bucket | `my-leecher-bucket` |
| `S3_ENDPOINT_URL` | Empty for AWS; set for compatible services | `https://s3.ap-northeast-1.wasabisys.com` |
| `S3_REGION` | Bucket region | `ap-northeast-1` |

**Endpoint cheat sheet**

| Provider | `S3_ENDPOINT_URL` | `S3_REGION` |
|---|---|---|
| AWS S3 | *(empty)* | bucket region, e.g. `us-east-1` |
| **Wasabi** | `https://s3.<region>.wasabisys.com` | matching `<region>` |
| Backblaze B2 | `https://s3.<region>.backblazeb2.com` | matching `<region>` |
| MinIO | `https://your-minio.example.com` | usually `us-east-1` |
| DigitalOcean Spaces | `https://<region>.digitaloceanspaces.com` | matching `<region>` |
| Cloudflare R2 | `https://<account-id>.r2.cloudflarestorage.com` | `auto` |

**Required IAM/permissions on your bucket**

| Action | Used by |
|---|---|
| `s3:GetObject` | `/s3leech` (downloads) |
| `s3:ListBucket` | `/s3leech` prefix mode |
| `s3:PutObject` | `/s3upload` (mirrors) |
| `s3:AbortMultipartUpload` | multipart cleanup on cancellation |

For full provider-specific walkthroughs see [S3_GUIDE.md](./S3_GUIDE.md).

---

## 7. Run the cell

Press the play button on the form cell. The cell will:

1. Print a banner.
2. Clone the repo into `/content/Telegram-Leecher/`.
3. `apt install` ffmpeg + aria2 and `pip install -r requirements.txt`.
4. Write `credentials.json` (with both Telegram and S3 fields).
5. Print one of:
   - `☁️ S3 enabled → bucket=<…> region=<…> endpoint=<…>` (full S3 ready)
   - `⚠️ S3 config is partially set …` (S3 commands disabled until all three of access key / secret key / bucket are filled)
6. Start the bot — `Colab Leecher Started !` appears in the cell output.

---

## 8. Talk to the bot

DM your bot on Telegram. Try `/start` first — you should get a reply. Then explore commands; full reference is in [COMMANDS.md](./COMMANDS.md).

Quick tour:

```text
/tupload           # leech links to Telegram
/gdupload          # mirror to Google Drive (needs step 5)
/s3upload          # mirror to S3 / Wasabi (needs step 6)
/s3leech           # leech S3 objects to Telegram (needs step 6)
/help              # show every command in-bot
```

---

## 9. Stop the bot

Stop the running cell in Colab. Re-running the cell starts a fresh session (the cell deletes any stale `my_bot.session` first).

---

## 10. Persist credentials between runs

Colab runtimes are ephemeral. To avoid retyping credentials every session:

- Store them in **Colab Secrets** (the 🔑 icon in the sidebar) and load them into the form fields on cell start, **or**
- Save `credentials.json` to your Drive (e.g. `/content/drive/MyDrive/secrets/credentials.json`) and copy it into `/content/Telegram-Leecher/credentials.json` after clone.

Treat the credentials file as sensitive — it contains your bot token, S3 keys, etc.
