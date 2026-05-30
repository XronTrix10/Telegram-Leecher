# Bot Commands Reference

Every command exposed by the bot, with the options that apply.

| Command | Purpose | Sources accepted | Destination |
|---|---|---|---|
| `/start` | Liveness check | — | — |
| `/help` | Show in-bot command list | — | — |
| `/tupload` | Leech to Telegram | HTTP(S), GDrive, Telegram, YouTube/yt-dlp, Mega, Terabox, **S3 URI** | Telegram |
| `/gdupload` | Mirror to Google Drive | Same as `/tupload` | `/content/drive/MyDrive/Colab Leecher Uploads/` |
| `/drupload` | Leech a local Colab folder | local path | Telegram |
| `/ytupload` | Force yt-dlp pipeline | YouTube + 2000+ sites | Telegram |
| `/s3upload` | Mirror to S3 / Wasabi | Same as `/tupload` | configurable S3 bucket |
| `/s3leech` | Leech S3 objects to Telegram | `s3://bucket/key` or prefix | Telegram |
| `/s3bucket <name>` | Change destination S3 bucket at runtime | — | — |
| `/s3prefix <folder>` | Set/clear S3 destination key prefix | — | — |
| `/setname <name.ext>` | Set custom output file name | — | — |
| `/zipaswd <pw>` | Password for output zip | — | — |
| `/unzipaswd <pw>` | Password for extracting archives | — | — |
| `/settings` | Open settings menu (caption, thumbnail, prefix/suffix, video) | — | — |

---

## Source URI formats

The bot detects source type automatically from each line of input.

| Pattern | Routed to |
|---|---|
| `https://drive.google.com/...` | Google Drive downloader |
| `https://t.me/...` | Telegram message downloader |
| `https://(www.)?youtube.com/...`, `youtu.be/...` | yt-dlp |
| `https://terabox...`, `1024tera...` | Terabox |
| `https://mega.nz/...` | Mega |
| `magnet:?xt=urn:btih:...` | Aria2c (note: Colab discourages torrents) |
| `s3://bucket/key`, `s3://bucket/folder/`, `s3:///key` | S3 downloader |
| any other `http(s)://...` | Aria2c direct download |
| `/content/...`, `/home/...` | local path (used by `/drupload`) |

You can mix sources in a single task — paste several lines, the bot processes each.

---

## Per-task argument lines

Append any of these lines to the bottom of your sources message **before** picking the upload type:

```text
[Custom name.ext]      # rename single-file output (square brackets)
{Zip password}         # password for /zipaswd output (curly braces)
(Unzip password)       # password for archive extraction (parentheses)
```

Example:

```text
https://example.com/big.zip
[my-name.zip]
{secretpw}
```

---

## Type selection (Regular / Compress / Extract / UnDoubleZip)

After you submit sources, the bot offers four options:

| Option | What happens |
|---|---|
| **Regular** | Download → upload as-is. Big files are split or zipped per the `Settings → Video` choice. |
| **Compress** | Download → zip → upload. `/zipaswd` password is applied if set. Multi-volume zip for >MAX_UPLOAD_SIZE. |
| **Extract** | Download → unzip (multi-part archives supported) → upload extracted contents. `/unzipaswd` is used. |
| **UnDoubleZip** | Download → unzip once → re-zip the result → upload. Useful for nested archives. |

For `/s3upload`, the same four options control what gets pushed to S3.

For `/s3leech`, the same four options control what gets pushed to Telegram after downloading from S3.

---

## Settings menu (`/settings`)

| Section | Options |
|---|---|
| **Video** | Split videos vs. zip videos when >2 GB; convert to mp4/mkv; quality preset |
| **Caption** | Monospace / Bold / Italic / Underlined / Regular text style |
| **Thumbnail** | View / delete custom thumbnail (send any image to set one) |
| **Prefix / Suffix** | Add a prefix or suffix to every uploaded file name |
| **Stream upload** | Send as `Media` (preview-able) or `Document` |

---

## S3 commands

### `/s3upload`
- Mode: `s3-mirror`.
- Sources: anything `/tupload` accepts, including `s3://...` URIs (S3-to-S3 copies are supported).
- Destination: `s3://<S3_BUCKET_NAME>/<S3_PREFIX>/Uploaded__<timestamp>/<file>` (bulk mode) or `s3://<S3_BUCKET_NAME>/<S3_PREFIX>/<rel-path>` (iterate mode, preserves source folder structure).
- **Iterative mode** auto-triggers when the source is a single multi-object S3 URI (`s3://bucket/`, `s3://bucket/prefix/`). Each source object is downloaded → uploaded → tracked → cleaned up before the next, so a 1 TB source bucket does not require 1 TB of Colab disk. See [S3_GUIDE.md → Whole-bucket iterative mode](./S3_GUIDE.md#-whole-bucket-iterative-mode--crash-resume).
- **Crash-resume**: tracker is mirrored to `s3://<S3_BUCKET_NAME>/s3teletracker.json`; re-running the same command on a fresh Colab runtime auto-skips already-completed objects.
- Multipart upload triggers above 64 MiB chunk size — files well above 2 GB are fine.
- Tracker: writes an `uploaded` entry per file in `s3teletracker.json`.

### `/s3leech`
- Mode: `leech` with S3 source.
- Sources: `s3://bucket/key` (single object), `s3://bucket/prefix/` (folder) or `s3://bucket` (whole bucket).
- Use `s3:///key` (note three slashes) to reuse the configured `S3_BUCKET_NAME` as the bucket.
- **Iterative mode** auto-triggers for prefix and whole-bucket sources (anything where `head_object` fails). Each object is downloaded → split if >2 GB → uploaded to Telegram → tracked → cleaned up before the next.
- **Crash-resume**: same `s3teletracker.json` mechanism as `/s3upload`.
- Destination: Telegram (the same upload pipeline used by `/tupload`).
- Tracker: writes a `downloaded` entry per object retrieved.

### `/s3bucket <name>`
- Changes the **destination** bucket used by `/s3upload`.
- Doesn't affect `/s3leech` source URIs (those carry their own bucket).
- Persists for the current bot session only.

### `/s3prefix <folder/sub>`
- Sets a key prefix prepended to every uploaded object key.
- `/s3prefix` with no argument clears the prefix.

---

## Lifecycle controls

- **Cancel button** appears on the live status message — stops the running task immediately.
- **Image upload (DM)** sets a custom Telegram thumbnail used for media uploads.
- The bot logs the entire task to your dump channel (`DUMP_ID`) once finished.
