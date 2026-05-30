# S3 / Wasabi / B2 Deep Dive

Everything about the S3-compatible storage integration: how it works, every supported provider with full copy-paste-ready credentials examples, all commands and options, the tracker file format, the multipart pipeline for >2 GB files, and provider-specific gotchas.

> **TL;DR:** Pick your provider's section below, copy the four/five form values into the Colab cell, run the bot, then paste the example DM commands into Telegram. You'll have files moving in <60 seconds.

---

## Table of contents

1. [What you can do](#what-you-can-do)
2. [Configuration (Colab cell)](#configuration-colab-cell)
3. **🔁 [Whole-bucket iterative mode + crash-resume](#-whole-bucket-iterative-mode--crash-resume)** ← NEW
4. **Per-provider quick-start (in depth)**
   - [AWS S3](#aws-s3)
   - [Wasabi](#wasabi)
   - [Backblaze B2](#backblaze-b2)
   - [Cloudflare R2](#cloudflare-r2)
   - [DigitalOcean Spaces](#digitalocean-spaces)
   - [MinIO / self-hosted](#minio--self-hosted)
   - [Storj DCS, Linode Object Storage, Scaleway, IDrive e2, Vultr…](#other-s3-compatible-providers)
5. [URI grammar](#uri-grammar)
6. [Worked examples (Telegram session walkthroughs)](#worked-examples-telegram-session-walkthroughs)
7. [Tracker file (`s3teletracker.json`)](#tracker-file-s3teletrackerjson)
8. [Multipart and big files (>2 GB)](#multipart-and-big-files-2-gb)
9. [Behavior matrix](#behavior-matrix)
10. [Cost & rate considerations](#cost--rate-considerations)
11. [Security notes](#security-notes)
12. [Quick command reference](#quick-command-reference)

---

## What you can do

| Direction | Command | Pipeline |
|---|---|---|
| any source → S3 | `/s3upload` | URLs/links/paths → local download → upload to S3 |
| S3 → Telegram | `/s3leech` | S3 object/prefix → local → upload to Telegram (with split for >2 GB) |
| S3 → S3 | `/s3upload` with `s3://...` source | source object → local → upload to destination bucket |
| S3 → Google Drive | `/gdupload` with `s3://...` source | source object → local → mirror to Drive |
| S3 inside any other command | (auto) | `s3://` URIs are accepted by `/tupload`, `/gdupload`, `/ytupload` too |

All transfers honor the same options as the rest of the bot: **Regular / Compress / Extract / UnDoubleZip**, custom names, zip & unzip passwords, the `/settings` menu (caption, thumbnail, prefix/suffix, video conversion), and the **Cancel ❌** button.

---

## Configuration (Colab cell)

Five form fields under the **☁️ S3 / Wasabi / B2 Configuration** section:

```text
S3_ACCESS_KEY    # access key
S3_SECRET_KEY    # secret key
S3_BUCKET_NAME   # default destination bucket
S3_ENDPOINT_URL  # leave empty for AWS, fill for Wasabi/B2/MinIO/etc.
S3_REGION        # bucket region (default: us-east-1)
```

When the cell starts you'll see one of:

```text
☁️  S3 enabled → bucket=<my-bucket> region=<ap-northeast-1> endpoint=<https://s3.ap-northeast-1.wasabisys.com>

⚠️  S3 config is partially set — /s3upload and /s3leech will be unavailable until
    S3_ACCESS_KEY, S3_SECRET_KEY and S3_BUCKET_NAME are all filled in.
```

If neither line appears, S3 is fully unconfigured and the four `/s3*` commands will refuse to run with a clear error message.

---

## 🔁 Whole-bucket iterative mode + crash-resume

When you point `/s3leech` or `/s3upload` at a **whole bucket or a prefix that contains many objects**, the bot automatically switches into **iterative mode**: instead of downloading every object first and uploading them all in bulk (which would blow Colab's 84 GB ephemeral disk for any large bucket), it processes objects **one at a time** with a clean workspace between iterations.

### When iterate mode triggers

Iterate mode kicks in automatically when **all** of these are true:

- Exactly **one** source line in your message
- That source is an `s3://` URI
- The URI resolves to a prefix or whole bucket (i.e. `head_object` fails — there is no single object at that exact key)
- Mode is `/s3leech` or `/s3upload`

URIs that trigger iterate mode:

```text
s3://my-bucket                     ← whole bucket
s3://my-bucket/                    ← whole bucket (with slash)
s3://my-bucket/folder/             ← prefix
s3://my-bucket/folder/2025/        ← deeper prefix
s3:///folder/                      ← prefix in default S3_BUCKET_NAME
```

URIs that do **not** trigger iterate mode (existing single-shot flow runs):

```text
s3://my-bucket/path/to/file.zip    ← single object, head_object succeeds
```

You'll see this annotation in the dump-channel message when iterate mode is active:

```text
🔁 Iterative bucket mode » processing one object at a time, with S3-persisted tracker resume
```

### Per-object pipeline (what runs for each object)

For every object in the bucket / prefix:

1. **Resume check** — if the object's `(bucket, key, size)` is already in the persistent tracker (from this run **or** a previous, possibly crashed Colab runtime), it is **skipped**.
2. **Workspace cleanup** — `down_path` / `temp_zpath` / `temp_unzip_path` / `temp_files_dir` are wiped, so peak disk usage is bounded by the **largest single source object**, not the whole bucket.
3. **Single-object download** — boto3 multipart download (64 MiB chunks). The object is **not** marked done yet (the download is internally invoked with `track=False`).
4. **Upload pipeline** — runs the user-selected option (Regular / Compress / Extract / UnDoubleZip), reusing the same `Leech` / `Zip_Handler` / `Unzip_Handler` primitives used by `/tupload` and `/gdupload`. **>2 GB source objects are split into <2 GB Telegram parts via `sizeChecker` exactly like `/tupload`.**
5. **Tracker write (only after a full round-trip)** — the object is recorded in `s3teletracker.json` **only after the download *and* the upload both succeed**, then **immediately mirrored to `s3://<S3_BUCKET_NAME>/s3teletracker.json`**. This ordering is important: if the runtime dies *during* the download or upload of an object, that object is **left untracked** so the next run **retries it** rather than skipping it. A crash therefore loses at most the work-in-progress on the single object that was mid-flight — never a half-delivered object marked "done".
6. **Move on** to the next object.

The status message in your Telegram DM updates per-iteration:

```text
🔁 ITERATIVE S3 ➜ TELEGRAM »

🪣 Bucket » my-bucket
📁 Prefix » folder/2025/
✅ Done » 47   ⏭️ Skipped » 12   📊 Total » 250

📥 OBJECT » folder/2025/photo-049.jpg
📦 Size » 8.4 MB

[progress bar from boto3 download → splitter → telegram upload…]
```

> **Note on the progress bar:** in iterate mode the per-object Telegram upload bar is reset for each object, so it runs a clean 0→100 % per object. The batch-level progress (how many of the whole bucket are done) is shown by the **✅ Done / ⏭️ Skipped / 📊 Total** counters in the header.

### Resume from a crash (Colab disconnect, OOM, manual stop, etc.)

The tracker is the single source of truth for "what's been done". Because **every successful iteration writes both the local file *and* uploads it to S3** (see `s3_track_persist_to_remote()`), a brand-new Colab runtime can pick up exactly where the previous one left off:

1. **Crash happens** — runtime dies mid-leech, after object 47 of 250 was completed and the 48th was in flight.
2. **Restart Colab**, fill in the same form values, run the cell.
3. **Re-issue the same command** in your Telegram DM:
   ```text
   /s3leech

   s3://my-bucket/folder/
   ```
4. **First thing the bot does** is download the tracker from S3 (`s3_track_load_from_remote()`), merging it with the local file. The dump-channel status now reads:
   ```text
   ✅ Done » 0   ⏭️ Skipped » 47   📊 Total » 250
   ```
5. The bot **skips objects 1–47** (already in tracker), starts processing from object 48, and continues until the bucket is fully done.

If you want to **force a full re-processing** from scratch, delete the tracker first:

```python
# In a fresh Colab cell BEFORE running the bot:
import boto3
s3 = boto3.client('s3',
    aws_access_key_id='YOUR_KEY',
    aws_secret_access_key='YOUR_SECRET',
    endpoint_url='YOUR_ENDPOINT_OR_LEAVE_OUT_FOR_AWS')
s3.delete_object(Bucket='YOUR_BUCKET', Key='s3teletracker.json')
print('Tracker deleted — next /s3* command will start fresh')
```

Or via the AWS / Wasabi / R2 web console — just delete the `s3teletracker.json` object at the root of your destination bucket.

### Resume scope per upload type

| Type option | Resume key | Behavior |
|---|---|---|
| **Regular** (`/s3leech`) | `(src_bucket, src_key, size)` in `downloaded` | Skipped objects don't redownload. |
| **Regular** (`/s3upload` from S3 source) | `(dst_bucket, dst_key, size)` in `uploaded` **and** `(src_bucket, src_key, size)` in `downloaded` | The destination check protects against renamed sources too. |
| **Compress / Extract / UnDoubleZip** | `(src_bucket, src_key, size)` in `downloaded` | Source-side resume only — the bot can't predict every output key (split-zip volumes, extracted file count). A partially-zipped source on crash is re-zipped from scratch on retry. |

### Disk pressure: what stays bounded

The per-iteration workspace cleanup means peak disk usage is bounded by:

```
peak ≈ size_of_largest_single_object (Regular)
peak ≈ size_of_largest_object × 2 (Compress / UnDoubleZip — original + zip output)
peak ≈ size_of_largest_archive + extracted_size (Extract)
```

So a 1 TB bucket made of 1 GB objects is processable on a 84 GB Colab runtime — peak disk is ~1 GB at any moment.

### Tracker file location

```text
Local (in-session)  : /content/Telegram-Leecher/s3teletracker.json
Remote (persistent) : s3://<S3_BUCKET_NAME>/s3teletracker.json
```

The remote copy is what makes resume possible across Colab runtimes. The local copy is what the bot reads during a session for the per-iteration skip check.

If `S3_BUCKET_NAME` is **not configured** (e.g. you only use `/s3leech` against random source buckets and never set a default), the tracker is **local-only** — resume still works within a single Colab session, but a Colab restart loses the progress. Configure a default bucket if you care about long-running batches surviving runtime hops.

### Things that still use the bulk (non-iterative) flow

- Single-object S3 URIs (`s3://bucket/file.zip`)
- Mixed-source tasks (multiple sources in one message, e.g. an HTTP link + an S3 URI)
- Non-S3 sources (HTTP, Drive, Telegram, yt-dlp, Mega, Terabox)

Iterate mode is purely opt-in via URI shape — no separate command, no flag.

---

## AWS S3

The original. Every other provider on this page is an "S3-compatible API" trying to be this.

### 1. Get credentials

1. Sign in to <https://console.aws.amazon.com/>.
2. Top-right user menu → **Security credentials**.
3. **Create access key** → choose *Application running outside AWS* → confirm.
4. Save **Access key ID** and **Secret access key** — the secret is shown **only once**.

> Production tip: use IAM users with the minimum policy below instead of root keys.

### 2. Create a bucket

1. Open **S3** service → **Create bucket**.
2. Name it (e.g. `my-leecher-bucket`) and pick a region (e.g. `us-east-1`, `ap-south-1`).
3. Leave defaults; click **Create**.

### 3. Minimum IAM policy

Replace `<bucket>`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:AbortMultipartUpload"],
      "Resource": "arn:aws:s3:::<bucket>/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket", "s3:ListBucketMultipartUploads"],
      "Resource": "arn:aws:s3:::<bucket>"
    }
  ]
}
```

### 4. Form values

```text
S3_ACCESS_KEY    = AKIA****************
S3_SECRET_KEY    = ****************************************
S3_BUCKET_NAME   = my-leecher-bucket
S3_ENDPOINT_URL  =                                   ← leave empty
S3_REGION        = us-east-1                         ← bucket's region
```

### 5. First test in Telegram

```text
/s3upload
https://speed.hetzner.de/100MB.bin
[aws-test.bin]
```
→ pick **Regular** → file lands at `s3://my-leecher-bucket/Uploaded__<timestamp>/aws-test.bin`.

```text
/s3leech
s3://my-leecher-bucket/Uploaded__<timestamp>/aws-test.bin
```
→ pick **Regular** → file is sent to your Telegram DM. Tracker file gets one `uploaded` and one `downloaded` entry.

### 6. Gotchas

- AWS S3 **does not** require `S3_ENDPOINT_URL`. Leaving it empty is correct; setting it can break signing.
- Region matters — bucket is region-scoped and `S3_REGION` must match (or you'll get `PermanentRedirect` / `IllegalLocationConstraintException`).

---

## Wasabi

Cheap S3-compatible storage with no egress fees. Most popular choice for Colab leeching.

### 1. Get credentials

1. Sign up at <https://console.wasabisys.com/>.
2. Left sidebar → **Access Keys** → **Create New Access Key** → root or sub-user.
3. Save **Access Key** and **Secret Key**.

### 2. Create a bucket

1. **Buckets** → **Create Bucket** → pick a region (this picks the endpoint).
2. Name it globally unique (e.g. `wasabi-leecher-test`).

### 3. Wasabi region → endpoint table

Pick the region geographically closest to where Colab assigned your runtime (usually US-east):

| Region code | Endpoint URL | Location |
|---|---|---|
| `us-east-1` | `https://s3.us-east-1.wasabisys.com` | N. Virginia, USA |
| `us-east-2` | `https://s3.us-east-2.wasabisys.com` | N. Virginia, USA |
| `us-central-1` | `https://s3.us-central-1.wasabisys.com` | Texas, USA |
| `us-west-1` | `https://s3.us-west-1.wasabisys.com` | Oregon, USA |
| `ca-central-1` | `https://s3.ca-central-1.wasabisys.com` | Toronto, Canada |
| `eu-central-1` | `https://s3.eu-central-1.wasabisys.com` | Amsterdam, NL |
| `eu-central-2` | `https://s3.eu-central-2.wasabisys.com` | Frankfurt, DE |
| `eu-west-1` | `https://s3.eu-west-1.wasabisys.com` | London, UK |
| `eu-west-2` | `https://s3.eu-west-2.wasabisys.com` | Paris, FR |
| `ap-northeast-1` | `https://s3.ap-northeast-1.wasabisys.com` | Tokyo, JP |
| `ap-northeast-2` | `https://s3.ap-northeast-2.wasabisys.com` | Osaka, JP |
| `ap-southeast-1` | `https://s3.ap-southeast-1.wasabisys.com` | Singapore |
| `ap-southeast-2` | `https://s3.ap-southeast-2.wasabisys.com` | Sydney, AU |

Authoritative list: <https://docs.wasabi.com/docs/what-are-the-service-urls-for-wasabi-s-different-regions>.

### 4. Form values (Tokyo example, matching the original Wasabi sample you might already have)

```text
S3_ACCESS_KEY    = FYTCJCK1EKLWD30D8707
S3_SECRET_KEY    = bKyeNjq8U0L8SrnARGzcXiLkpoecLQEdanMv1Ok6
S3_BUCKET_NAME   = testfilesdownvnr
S3_ENDPOINT_URL  = https://s3.ap-northeast-1.wasabisys.com
S3_REGION        = ap-northeast-1
```

> The keys above are example placeholders — replace with your own.

### 5. First test in Telegram

```text
/s3upload
https://speed.hetzner.de/1GB.bin
[wasabi-test-1g.bin]
```
→ **Regular** → file is mirrored to Wasabi via boto3 multipart (~16 chunks of 64 MiB each).

```text
/s3leech
s3://testfilesdownvnr/Uploaded__<timestamp>/wasabi-test-1g.bin
```
→ **Regular** → 1 file in Telegram (under 2 GB so no split).

### 6. >2 GB end-to-end test

```text
# Pre-load a 5 GB file into Wasabi via the bot:
/s3upload
https://speed.hetzner.de/10GB.bin
[wasabi-big.bin]
# pick Regular — boto3 multipart, single S3 object

/s3leech
s3://testfilesdownvnr/Uploaded__<timestamp>/wasabi-big.bin
# pick Regular — sizeChecker splits into 5 parts of ~2 GB each, all uploaded to Telegram
```

### 7. Gotchas

- Region in `S3_REGION` **must** match the region in `S3_ENDPOINT_URL`, or you'll get `SignatureDoesNotMatch`.
- Wasabi is free egress *up to the volume of your storage*; bulk re-uploads can cross that line.
- New buckets sometimes take 30–60 s to become available — if the first command fails with `NoSuchBucket`, wait and retry.

---

## Backblaze B2

Cheap object storage with the S3-compatible API enabled.

### 1. Get credentials

1. Sign in to <https://secure.backblaze.com/b2_buckets.htm>.
2. Sidebar → **Application Keys** → **Add a New Application Key**.
3. Choose the bucket (or "All"), enable **Read and Write**, click **Create New Key**.
4. Save **keyID** (this is `S3_ACCESS_KEY`) and **applicationKey** (this is `S3_SECRET_KEY`). The application key is shown **only once**.

### 2. Create a bucket

1. **Buckets** → **Create a Bucket** → name it (globally unique).
2. Set privacy to **Private**.
3. After creation, note the **Endpoint** shown for the bucket — it looks like `s3.us-west-002.backblazeb2.com`.

### 3. Form values

```text
S3_ACCESS_KEY    = 0026****************              ← keyID
S3_SECRET_KEY    = K002****************              ← applicationKey
S3_BUCKET_NAME   = my-b2-bucket
S3_ENDPOINT_URL  = https://s3.us-west-002.backblazeb2.com
S3_REGION        = us-west-002
```

The region segment of the endpoint **is** the region. The first three letters identify the geographic area; the trailing digits identify the cluster.

### 4. First test in Telegram

```text
/s3upload
https://speed.hetzner.de/100MB.bin
[b2-test.bin]
```
→ **Regular** → object lands at `s3://my-b2-bucket/Uploaded__<timestamp>/b2-test.bin`.

### 5. Gotchas

- B2's S3-compatible API requires the **Application Key** (not the master key) for full S3 SDK compatibility. Master keys may work but are not recommended.
- B2 enforces a 5 TiB single-object limit, identical to AWS.
- B2 charges Class B (download) and Class C (list) operations even on free-tier accounts; multipart upload counts as one Class C call per part initiation.

---

## Cloudflare R2

S3-compatible object storage with **zero egress fees**.

### 1. Get credentials

1. <https://dash.cloudflare.com/> → **R2** → **Manage R2 API Tokens**.
2. **Create API token** → choose **Object Read & Write** → scope to your bucket.
3. Save **Access Key ID** and **Secret Access Key**.
4. Note the **endpoint** — it has the form `https://<account-id>.r2.cloudflarestorage.com`.

### 2. Create a bucket

1. **R2** → **Create bucket** → name it.
2. R2 buckets are global — there's no region selector at creation time.

### 3. Form values

```text
S3_ACCESS_KEY    = ********************
S3_SECRET_KEY    = ****************************************
S3_BUCKET_NAME   = my-r2-bucket
S3_ENDPOINT_URL  = https://<your-account-id>.r2.cloudflarestorage.com
S3_REGION        = auto                                   ← R2-specific, literal string
```

### 4. First test

```text
/s3upload
https://speed.hetzner.de/100MB.bin
[r2-test.bin]
```

### 5. Gotchas

- **`S3_REGION = auto`** — anything else fails signing. Use the literal string `auto`.
- The endpoint contains your **account ID**, not a region. Find it on the R2 page header.
- R2 doesn't support presigned URLs older than 7 days; not relevant for the bot but worth knowing.

---

## DigitalOcean Spaces

S3-compatible object storage tied to DigitalOcean droplets / network.

### 1. Get credentials

1. <https://cloud.digitalocean.com/account/api/tokens> → **Spaces access keys** → **Generate New Key**.
2. Save **Access Key** and **Secret**.

### 2. Create a Space

1. **Spaces** → **Create a Space** → pick datacenter region (e.g. `nyc3`, `sfo3`, `ams3`, `sgp1`, `fra1`).
2. Name it.

### 3. DigitalOcean region table

| Region code | Endpoint URL |
|---|---|
| `nyc3` | `https://nyc3.digitaloceanspaces.com` |
| `sfo3` | `https://sfo3.digitaloceanspaces.com` |
| `ams3` | `https://ams3.digitaloceanspaces.com` |
| `sgp1` | `https://sgp1.digitaloceanspaces.com` |
| `fra1` | `https://fra1.digitaloceanspaces.com` |
| `syd1` | `https://syd1.digitaloceanspaces.com` |
| `tor1` | `https://tor1.digitaloceanspaces.com` |
| `blr1` | `https://blr1.digitaloceanspaces.com` |

### 4. Form values

```text
S3_ACCESS_KEY    = DO00****************
S3_SECRET_KEY    = ****************************************
S3_BUCKET_NAME   = my-do-space
S3_ENDPOINT_URL  = https://nyc3.digitaloceanspaces.com
S3_REGION        = nyc3
```

### 5. First test

```text
/s3upload
https://speed.hetzner.de/100MB.bin
[do-test.bin]
```

### 6. Gotchas

- Each Space lives in **one** region. Cross-region copies require a manual `s3://src-bucket/...` → `/s3upload` round-trip.
- DigitalOcean's monthly inclusive bandwidth is metered; check your billing before bulk leeching.

---

## MinIO / self-hosted

Run your own S3-compatible server, e.g. on a VPS.

### 1. Run MinIO

```bash
docker run -d -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=admin" \
  -e "MINIO_ROOT_PASSWORD=changeme123" \
  --name minio minio/minio server /data --console-address ":9001"
```

Open `http://your-host:9001` → log in with the credentials above → **Identity → Access Keys → Create access key**.

### 2. Create a bucket

1. **Buckets** → **Create Bucket** → name it.

### 3. Form values

```text
S3_ACCESS_KEY    = <your-access-key>
S3_SECRET_KEY    = <your-secret-key>
S3_BUCKET_NAME   = my-minio-bucket
S3_ENDPOINT_URL  = https://your-minio.example.com    ← or http:// if no TLS
S3_REGION        = us-east-1                         ← MinIO defaults to us-east-1
```

### 4. First test

```text
/s3upload
https://speed.hetzner.de/100MB.bin
[minio-test.bin]
```

### 5. Gotchas

- HTTPS strongly recommended — Colab warns on insecure HTTP endpoints.
- MinIO's default region is `us-east-1`. To use a different region, set the server flag `MINIO_REGION_NAME=<region>` and match it in the cell.
- Self-hosted networks may have firewall/NAT issues; if Colab can't reach your endpoint, you'll see `EndpointConnectionError`.

---

## Other S3-compatible providers

The bot works with any provider that speaks the S3 API. Same form fields, just different endpoint values.

| Provider | `S3_ENDPOINT_URL` | `S3_REGION` |
|---|---|---|
| **Storj DCS** (S3 gateway) | `https://gateway.storjshare.io` | `eu1` / `us1` / `ap1` |
| **Linode Object Storage** | `https://<region>.linodeobjects.com` (e.g. `us-east-1.linodeobjects.com`) | matching `<region>` |
| **Scaleway Object Storage** | `https://s3.<region>.scw.cloud` (e.g. `s3.fr-par.scw.cloud`) | matching `<region>` |
| **IDrive e2** | `https://<region>.idrivee2-XX.com` (varies by tier) | matching `<region>` |
| **Vultr Object Storage** | `https://<region>.vultrobjects.com` | matching `<region>` |
| **OVH Object Storage** | `https://s3.<region>.io.cloud.ovh.net` | matching `<region>` |
| **Cloud SQL S3 (Yandex)** | `https://storage.yandexcloud.net` | `ru-central1` |
| **Alibaba OSS** (S3-compat) | `https://oss-<region>.aliyuncs.com` | matching `<region>` |

If your provider isn't listed, look in their docs for "S3-compatible endpoint" — the bot just needs HTTPS endpoint + access key + secret key + bucket name + region.

---

## URI grammar

| URI | Meaning |
|---|---|
| `s3://bucket/path/to/file.ext` | single object |
| `s3://bucket/folder/` | every object under the prefix (folder mode, preserves tree) |
| `s3:///key/in/default/bucket` | three slashes → use `S3_BUCKET_NAME` as bucket |
| `s3://bucket` (no trailing slash) | every object in the bucket — be careful, this can be a **lot** |

Folder mode preserves the directory tree under `Paths.down_path` and uploads/leeches each file as you'd expect.

---

## Worked examples (Telegram session walkthroughs)

Each example shows the exact commands you type, what you should select, and what happens. Provider doesn't matter; pick whichever S3-compatible service you configured.

### Example 1 — Mirror a direct download to S3 (Regular)

```text
/s3upload

https://example.com/release-1.0.zip
[release-final.zip]
```

→ tap **Regular** → file is downloaded by aria2 to `/content/Telegram-Leecher/BOT_WORK/Downloads/`, then uploaded to `s3://<bucket>/Uploaded__YYYY-MM-DD_HH-MM-SS/release-final.zip`. A JSON entry appears in `s3teletracker.json` under `uploaded`.

### Example 2 — Leech a single S3 object back to Telegram

```text
/s3leech

s3://my-bucket/Uploaded__2026-05-28_19-45-21/release-final.zip
```

→ tap **Regular** → object is downloaded via boto3 multipart (parts of 64 MiB each), then uploaded as a single file to your Telegram DM (or split into <2 GB parts if it exceeds 2 GB). A `downloaded` entry is appended to the tracker.

### Example 3 — Leech a whole prefix (folder) to Telegram, zipped

```text
/s3leech

s3://my-bucket/photos/vacation-2025/
{my-vacation-pw}
```

→ tap **Compress** → entire folder is downloaded preserving its tree, zipped (with the `{my-vacation-pw}` password), and the resulting (split if >2 GB) zip parts are uploaded to Telegram.

### Example 4 — Copy an object from one bucket to another

```text
/s3bucket destination-bucket
/s3upload

s3://source-bucket/path/to/file.mkv
```

→ tap **Regular** → object is downloaded from `source-bucket`, uploaded to `destination-bucket` under a fresh `Uploaded__<timestamp>/file.mkv` key. Tracker logs **both** directions.

### Example 5 — Set a destination prefix once, mirror many things

```text
/s3prefix archive/2026-Q2
/s3upload

https://example.com/a.iso
https://example.com/b.iso
https://example.com/c.iso
```

→ tap **Regular** → all three end up at `s3://<bucket>/archive/2026-Q2/Uploaded__<timestamp>/...`. The prefix persists for the rest of the bot session until you change/clear it.

### Example 6 — Extract an archive stored in S3 and put the contents in Drive

```text
/gdupload

s3://my-bucket/backups/2026-05-01.tar.gz
(archive_password)
```

→ tap **Extract** → archive is downloaded from S3, extracted (with the `(archive_password)` from the parens line), and the contents are mirrored to `Drive/Colab Leecher Uploads/...`.

### Example 7 — >2 GB file from S3 to Telegram (split mirror)

```text
/s3leech

s3://my-bucket/movies/big-blockbuster-5gb.mkv
[Movie Title 2026.mkv]
```

→ tap **Regular** → boto3 multipart download → `sizeChecker` detects 5 GB > 2 GB → `splitVideo` (or `splitArchive` if it's a zip/rar/7z/tar/gz) produces 3 chunks of <2 GB → each chunk uploaded to Telegram. End user sees 3 messages in their DM, named `Movie Title 2026.part001.mkv`, `.part002.mkv`, `.part003.mkv`.

### Example 8 — Source mix in one task

```text
/s3upload

https://example.com/from-internet.zip
s3://other-bucket/from-s3.zip
https://drive.google.com/file/d/<id>/view
```

→ tap **Regular** → all three are downloaded (by aria2 / boto3 / Google API respectively), then all three are uploaded to your S3 bucket under one `Uploaded__<timestamp>/` folder. Tracker gets one `downloaded` entry (for the S3 source) and three `uploaded` entries.

### Example 9 — Custom name + zip password + unzip password in one shot

```text
/s3upload

https://example.com/mystery.7z
[unboxed.zip]
{out-zip-pw}
(in-7z-pw)
```

→ tap **UnDoubleZip** → archive is downloaded → extracted with `(in-7z-pw)` → re-zipped (split into 2 GB volumes) with `{out-zip-pw}` → uploaded to S3 as `unboxed.zip.001`, `unboxed.zip.002`, …

---

## Tracker file (`s3teletracker.json`)

Two locations:

- **Local (in-session)**: `/content/Telegram-Leecher/s3teletracker.json`
- **Remote (persistent)**: `s3://<S3_BUCKET_NAME>/s3teletracker.json`

The remote copy is the durable backup that survives Colab runtime restarts. After every successful transfer, the local file is updated **and** mirrored to S3 (best-effort — failures are logged but never abort the transfer).

Two top-level arrays — `uploaded` (local→S3) and `downloaded` (S3→local). Each entry:

```json
{
  "timestamp":  "2026-05-28T19:45:21",
  "file_name":  "release-final.zip",
  "bucket":     "my-bucket",
  "key":        "Uploaded__2026-05-28_19-45-21/release-final.zip",
  "size":       2147483648,
  "size_human": "2.00 GB",
  "endpoint":   "https://s3.ap-northeast-1.wasabisys.com"
}
```

### Tips

- The file is appended in real time, so you can `cat` it during a transfer to verify progress is recorded.
- Entries are deduplicated by `(bucket, key, size)` — re-runs of the same task won't bloat the tracker.
- If the file becomes corrupt (manual edit, etc.) the bot resets it and continues — only the corrupt session's entries are lost.
- If `S3_BUCKET_NAME` is empty, the remote copy is skipped and the tracker is local-only (lost on Colab restart).
- To force a full re-processing, delete `s3teletracker.json` from the bucket (or use the snippet in [§ Whole-bucket iterative mode → Resume from a crash](#-whole-bucket-iterative-mode--crash-resume)).

---

## Multipart and big files (>2 GB)

There are **two different "big file" mechanisms** in the codebase, and S3 hooks into both correctly depending on the destination:

### Telegram destination — *physical split into <2 GB parts*

Telegram's bot API caps a single upload at 2 GB. Both `/tupload` and `/s3leech` therefore invoke `colab_leecher/utility/converters.py::sizeChecker` on each file before upload; anything >2 GB is split into `.001 / .002 / …` (raw), `.partNNN.<ext>` (video segment) or split-zip volumes via `zip -s 2000m` / `7z -v2000m`. Each part is then uploaded to Telegram individually.

### Object-storage destination — *multipart upload, no physical split*

S3 (and Drive) accept the whole object, so there's no need to fragment. `/s3upload` and `/gdupload` send the whole file. For S3, the bot uses boto3's `TransferConfig`:

| Parameter | Value |
|---|---|
| `multipart_threshold` | 64 MiB |
| `multipart_chunksize` | 64 MiB |
| `max_concurrency` | 4 |
| `use_threads` | True |

Anything over 64 MiB is uploaded/downloaded as parallel 64 MiB parts. S3 supports up to 10 000 parts per object → ~640 GB at our chunk size; boto3 auto-resizes for objects up to S3's 5 TiB ceiling.

Progress flows through the same `status_bar` used by every other downloader/uploader, so the **Cancel ❌** button keeps working. Cancelling stops the asyncio task immediately; the in-flight chunk in the boto3 worker thread completes silently and is then discarded.

### What happens to a 5 GB file in each command (worked example)

| Command | Mode | Pipeline | Result |
|---|---|---|---|
| `/tupload` | Regular | `Leech` → `sizeChecker` splits → 3× upload | 3 parts in Telegram |
| `/tupload` | Compress | `Zip_Handler(is_split=True)` → 3× upload | 3 split-zip volumes in Telegram |
| `/s3leech` | Regular | `s3_Download` (boto3 multipart) → `Leech` → `sizeChecker` splits → 3× upload | 3 parts in Telegram (matches `/tupload`) |
| `/s3leech` | Compress | `s3_Download` → `Zip_Handler(is_split=True)` → 3× upload | 3 split-zip volumes in Telegram |
| `/gdupload` | Regular | download → `shutil.copytree` → Drive | 1 file in Drive |
| `/gdupload` | Compress | `Zip_Handler(is_split=True)` → Drive | 3 split-zip volumes in Drive |
| `/s3upload` | Regular | download → `s3_upload_file` (boto3 multipart) | **1 object** in S3 (~80 internal parts of 64 MiB) |
| `/s3upload` | Compress | `Zip_Handler(is_split=True)` → upload each volume | 3 separate split-zip objects in S3 (matches `/gdupload`) |
| `/s3upload` | Extract | download → unzip → upload each extracted file | as many S3 objects as files in the archive |
| `/s3upload` | UnDoubleZip | download → unzip → re-zip (split) → upload | 3 split-zip objects in S3 |

**Takeaway:** `/s3leech` reuses the exact same split pipeline as `/tupload` (Telegram's 2 GB cap is honored), and `/s3upload` mirrors `/gdupload` (whole file via multipart in Regular, split-zip volumes in Compress).

---

## Behavior matrix

| Scenario | Result |
|---|---|
| `/s3upload` with no S3 creds | Bot replies with a configuration message and refuses the command. |
| `/s3leech s3://other-bucket/...` while `S3_BUCKET_NAME=my-bucket` | Source URI bucket wins; the configured default is only used by `/s3upload` and by `s3:///key` short-form URIs. |
| `/s3leech s3:///foo` with no `S3_BUCKET_NAME` | Bot raises a clear error: "No S3 bucket specified and no default S3_BUCKET_NAME configured." |
| Object > 2 GB | Multipart kicks in automatically; Telegram split or zip happens after the local download per the regular Settings rules. |
| Source includes a mix of `s3://` and `https://` URIs | Each is dispatched to the right downloader and aggregated together. **Bulk mode** (no iterate). |
| `/s3leech s3://bucket/folder/` | **Iterate mode** — whole prefix processed one object at a time with crash-resume. |
| `/s3leech s3://bucket/single-file.ext` | Bulk mode — single object, no iteration needed. |
| `/s3upload s3://other-bucket/` | Iterate mode — S3-to-S3 mirror, one object at a time. |
| Tracker file write fails | A warning is logged but the transfer is **not** aborted (tracker is best-effort). |
| Re-run after Colab crash | Iterate mode auto-skips already-tracked objects; bulk mode re-downloads everything. |

---

## Cost & rate considerations

- Multipart uploads are billed per part on most providers — the bot uses 64 MiB parts which keeps the part count low even for 100 GB+ files.
- Wasabi has no egress fees up to your storage volume; AWS, B2 and DO charge per GB out. R2 has zero egress.
- Re-running `/s3upload` for the same file uploads it again — there is no idempotent dedup. The fresh `Uploaded__<timestamp>/` prefix avoids overwrites.
- The tracker is the easiest way to audit what cost you what: every entry has the size in bytes and a human-readable form.

---

## Security notes

- `credentials.json` (in `/content/Telegram-Leecher/`) contains your bot token + S3 keys. Treat it as sensitive.
- Colab runtimes are ephemeral — once the runtime stops, that file is gone. If you persist it via Drive, make sure that Drive folder isn't shared.
- The bot never broadcasts credentials. It only writes them to the local credentials file at startup.
- You can revoke an exposed key in your provider's console; the bot will fail with `InvalidAccessKeyId` until you update the cell and restart.
- Use scoped IAM users / sub-accounts where possible. For AWS, the policy in [§ AWS S3 step 3](#3-minimum-iam-policy) is the minimum.

---

## Quick command reference

```text
/s3upload                 # mirror downloads → S3 (with all standard options)
/s3leech                  # leech S3 objects/prefixes → Telegram
/s3bucket <name>          # change destination bucket (session-scoped)
/s3prefix <folder/sub>    # set or clear destination key prefix
```

For more, see [COMMANDS.md](./COMMANDS.md) and [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).
