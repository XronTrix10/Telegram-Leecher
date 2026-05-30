# Troubleshooting

Common errors, what they mean, and how to fix them.

---

## Colab notebook

### "Could not find Telegram_Leecher.ipynb in api.github.com/repos/.../contents/?...&ref=main"

The Colab Open-In-Colab URL is pinned to a branch. If the badge points at `main` but the file only lives on a feature branch, GitHub returns 404 and Colab surfaces this error.

**Fix:** the [README](../README.md) Colab badge currently uses `blob/feat/s3-integration`. Once that branch is merged to `main`, replace `blob/feat/s3-integration` with `blob/main` in the badge URL. Both URLs work after the merge — the branch URL keeps working as long as the branch exists.

You can always open the notebook manually in Colab via **File → Open notebook → GitHub** and pasting the repo URL.

### "Form panel doesn't show the S3 fields"

You opened an older version of the notebook. Refresh the Colab tab — the badge always pulls the latest commit on whichever branch the URL targets. If you forked the repo, make sure your fork has the recent commits and update the badge URL to point at your fork.

### "Banner prints, then nothing happens"

The dependency install step is silent — give it 60–90 seconds on first run. If it stalls longer, expand the cell output to see the `pip install` log and look for failures (most often a transient PyPI error; re-run the cell).

---

## Bot startup

### "ApiIdInvalid" / "AuthKeyInvalid"

Your `API_ID` / `API_HASH` from <https://my.telegram.org> are wrong. Re-copy them and check there are no leading/trailing spaces.

### "Telegram client crashed: invalid bot token"

`BOT_TOKEN` is wrong or the bot was deleted. Get a fresh token via [@BotFather](https://t.me/BotFather) → `/mybots` → select bot → API Token.

### "ChatWriteForbidden" when starting tasks

The bot is not an admin in the dump channel, or `DUMP_ID` is wrong. Re-add the bot as admin with post permission. Verify `DUMP_ID` by forwarding any message from the channel to [@userinfobot](https://t.me/userinfobot).

---

## Google Drive

### "Google Drive is NOT MOUNTED!"

You ran `/gdupload` without mounting Drive. Run the **Drive mount cell** in the notebook (cell 3) first, then retry. Skip Drive entirely if you don't use `/gdupload` — `/tupload`, `/s3upload`, etc. work without Drive.

---

## S3 / Wasabi / B2

### "S3 is NOT CONFIGURED!"

One or more of `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET_NAME` is empty in the form. Fill all three and re-run the cell.

### "InvalidAccessKeyId" (boto3 client error)

The access key is wrong, revoked, or doesn't belong to the endpoint you're hitting. Double-check:

1. Endpoint URL matches the provider for the keys you pasted.
2. Key wasn't disabled in your provider console.
3. No accidental whitespace in either field.

### "SignatureDoesNotMatch"

Secret key is wrong, **or** `S3_REGION` doesn't match the bucket's region. Wasabi and B2 both validate the region in the signature.

### "NoSuchBucket"

Bucket name typo, or bucket lives in a different region than `S3_REGION`. List your buckets in the provider console and copy the exact name.

### "EndpointConnectionError" / "Could not connect to the endpoint URL"

Likely causes:

- `S3_ENDPOINT_URL` has a typo or a trailing slash that confuses boto3 (drop the trailing `/`).
- You set an endpoint for AWS S3 — leave it empty for AWS.
- The Colab runtime can't reach the host (rare, usually a transient network blip; restart the cell).

### "AccessDenied" on PutObject / GetObject

Your IAM user / app key doesn't have the required permissions. See the [S3 deep dive](./S3_GUIDE.md#worked-examples) for the minimum AWS IAM policy. For Wasabi/B2, ensure the application key is **read+write** for the bucket.

### "/s3leech s3://bucket/folder/" returns "No objects found"

The prefix is empty, or the trailing slash matters and you forgot it. Check the bucket in the provider console and copy the exact prefix. `s3://bucket/folder` (no slash) and `s3://bucket/folder/` (slash) have different semantics — the former tries `head_object` first.

### Cancelled an `/s3upload` task — partial multipart hanging?

The bot's `TransferConfig` calls `AbortMultipartUpload` automatically on exception, but a hard runtime kill can leave parts. Most providers expire abandoned multipart uploads after 24 hours. To clean up immediately:

```python
import boto3
s3 = boto3.client('s3', endpoint_url='<your-endpoint>')
for u in s3.list_multipart_uploads(Bucket='<bucket>').get('Uploads', []):
    s3.abort_multipart_upload(Bucket='<bucket>', Key=u['Key'], UploadId=u['UploadId'])
```

### Upload is much slower than expected on Wasabi/B2

The runtime is geographically far from the endpoint region. Pick a region close to where Colab assigned your runtime (the [Colab IP/region](https://stackoverflow.com/questions/48750199/google-colaboratory-misleading-information-about-its-gpu-only-5-ram-available) is usually US-central, but it varies). For Wasabi, `us-east-1` and `us-east-2` are typically fastest from Colab US.

---

## Tracker file

### `s3teletracker.json` is missing

It's only created the first time an S3 transfer succeeds. Until then, no file exists. Run `/s3upload` or `/s3leech` once.

### Tracker file became invalid JSON

If a hard kill happened mid-write, the file may have a truncated entry. The bot detects this and resets the file on next transfer (only the corrupt session is lost). You can also delete it manually:

```python
import os
os.remove('/content/Telegram-Leecher/s3teletracker.json')
```

If the **remote** copy is corrupt (`s3://<bucket>/s3teletracker.json`), delete that object via your provider's web console **and** the local file:

```python
import os, boto3
os.remove('/content/Telegram-Leecher/s3teletracker.json') if os.path.exists('/content/Telegram-Leecher/s3teletracker.json') else None
boto3.client('s3', endpoint_url='YOUR_ENDPOINT').delete_object(Bucket='YOUR_BUCKET', Key='s3teletracker.json')
```

### How do I keep the tracker between runtimes?

**You don't need to** — as of the iterate-mode update, the bot automatically mirrors the tracker to `s3://<S3_BUCKET_NAME>/s3teletracker.json` after every successful transfer. A fresh Colab runtime running the same `/s3*` command will pull the remote tracker and resume from where the previous runtime left off.

If `S3_BUCKET_NAME` is empty (you only use `/s3leech` against arbitrary source buckets), set a dummy bucket value to enable persistence — any bucket your access key can write to works.

### How do I force a full re-run of a bucket I've already processed?

Delete the tracker. From a Colab cell:

```python
import boto3
s3 = boto3.client('s3',
    aws_access_key_id='YOUR_KEY',
    aws_secret_access_key='YOUR_SECRET',
    endpoint_url='YOUR_ENDPOINT_OR_REMOVE_FOR_AWS')
s3.delete_object(Bucket='YOUR_BUCKET', Key='s3teletracker.json')
```

Or use the provider web console. Next `/s3upload` or `/s3leech` will start fresh.

### Iterate mode didn't trigger for my whole-bucket task

The bot only auto-iterates when the URI resolves to a multi-object source. A typo can produce a URI that `head_object` happens to match, sending you into bulk mode. Check that:

- Source URI ends with a slash (`s3://bucket/folder/`) **or** has no key after the bucket (`s3://bucket`)
- The bucket actually has more than one object under that prefix
- The dump-channel message shows the line: `🔁 Iterative bucket mode » processing one object at a time, with S3-persisted tracker resume`

If the line is missing, the bot decided the URI was a single object. Add a trailing slash to force prefix interpretation.

### Iterate mode skipped everything (`Skipped » N   Done » 0`)

Every object's `(bucket, key, size)` is already in the tracker. Either:

1. The previous run completed successfully (no action needed) — verify via `s3://<bucket>/s3teletracker.json`.
2. The objects' sizes changed but the keys didn't (unusual). Delete the relevant entries from the tracker JSON manually, or delete the whole tracker as above.

---

## Big-file uploads to Telegram

### "FILE_PARTS_INVALID" or upload aborts on >2 GB

This is a Telegram MTProto limit, not an S3 limit. The Settings menu's **Video → Split Videos / Zip Videos** controls how the bot handles big files. Pick **Zip Videos** to let the bot split into multi-volume zips for any file type.

Premium uploads up to 4 GB are not yet wired in (planned).

---

## Performance tuning

| Symptom | Knob |
|---|---|
| S3 upload feels slow | Increase `max_concurrency` in `colab_leecher/uploader/s3.py::_build_transfer_config` (default 4). |
| Memory pressure on small Colab instances | Lower `multipart_chunksize` from 64 MiB to 16 MiB in the same function. |
| Telegram upload spikes API calls | Increase `BOT.Setting.split_video` size in `/settings`. |

These are all in code — pull, edit, push, and Colab picks up the change next time the cell runs (since the cell does a fresh `git clone`).

---

## Where to look next

- [SETUP.md](./SETUP.md) — first-time setup walk-through
- [COMMANDS.md](./COMMANDS.md) — every command and option
- [S3_GUIDE.md](./S3_GUIDE.md) — deep S3 documentation
- Open an issue on the repo if you've hit something not covered here.
