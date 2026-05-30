# copyright 2023 © Xron Trix | https://github.com/Xrontrix10


# @title 🖥️ Main Colab Leech Code

# @title Main Code
# @markdown <div><center><img src="https://user-images.githubusercontent.com/125879861/255391401-371f3a64-732d-4954-ac0f-4f093a6605e1.png" height=80></center></div>
# @markdown <center><h4><a href="https://github.com/XronTrix10/Telegram-Leecher/wiki/INSTRUCTIONS">READ</a> How to use</h4></center>

# @markdown <br>
# @markdown ### 🤖 Telegram Bot Configuration *(required)*
API_ID = 0  # @param {type: "integer"}
API_HASH = ""  # @param {type: "string"}
BOT_TOKEN = ""  # @param {type: "string"}
USER_ID = 0  # @param {type: "integer"}
DUMP_ID = 0  # @param {type: "integer"}

# @markdown ---
# @markdown ### ☁️ S3 / Wasabi / B2 Configuration *(optional — needed only for `/s3upload` and `/s3leech`)*
# @markdown
# @markdown Works with **AWS, Wasabi, Backblaze B2, Cloudflare R2, DigitalOcean Spaces, MinIO** and any other S3-compatible service.
# @markdown Leave the five fields below blank if you don't plan to use S3.
# @markdown
# @markdown <details><summary><b>📋 Click to expand: copy-paste examples for every provider</b></summary>
# @markdown
# @markdown #### 🟧 AWS S3
# @markdown ```text
# @markdown S3_ACCESS_KEY    = AKIA****************
# @markdown S3_SECRET_KEY    = ****************************************
# @markdown S3_BUCKET_NAME   = my-leecher-bucket
# @markdown S3_ENDPOINT_URL  =                          ← LEAVE EMPTY for AWS
# @markdown S3_REGION        = us-east-1                ← bucket's region
# @markdown ```
# @markdown
# @markdown #### 🟩 Wasabi (most popular for Colab — no egress fees)
# @markdown ```text
# @markdown S3_ACCESS_KEY    = FYTC********  ← from Wasabi → Access Keys → Create New
# @markdown S3_SECRET_KEY    = bKye************************************
# @markdown S3_BUCKET_NAME   = my-wasabi-bucket
# @markdown S3_ENDPOINT_URL  = https://s3.ap-northeast-1.wasabisys.com    ← match region!
# @markdown S3_REGION        = ap-northeast-1
# @markdown ```
# @markdown <sub>Region table: us-east-1 / us-east-2 / us-central-1 / us-west-1 / ca-central-1 / eu-central-1 / eu-central-2 / eu-west-1 / eu-west-2 / ap-northeast-1 / ap-northeast-2 / ap-southeast-1 / ap-southeast-2. Endpoint is always <code>https://s3.&lt;region&gt;.wasabisys.com</code></sub>
# @markdown
# @markdown #### 🟥 Backblaze B2
# @markdown ```text
# @markdown S3_ACCESS_KEY    = 0026****************    ← keyID from B2 → Application Keys
# @markdown S3_SECRET_KEY    = K002****************    ← applicationKey (shown ONCE)
# @markdown S3_BUCKET_NAME   = my-b2-bucket
# @markdown S3_ENDPOINT_URL  = https://s3.us-west-002.backblazeb2.com    ← from bucket page
# @markdown S3_REGION        = us-west-002             ← region segment of endpoint
# @markdown ```
# @markdown
# @markdown #### 🟧 Cloudflare R2 (zero egress fees)
# @markdown ```text
# @markdown S3_ACCESS_KEY    = ********************    ← R2 → Manage R2 API Tokens
# @markdown S3_SECRET_KEY    = ****************************************
# @markdown S3_BUCKET_NAME   = my-r2-bucket
# @markdown S3_ENDPOINT_URL  = https://<account-id>.r2.cloudflarestorage.com
# @markdown S3_REGION        = auto                    ← literal string "auto" — R2 quirk
# @markdown ```
# @markdown
# @markdown #### 🟦 DigitalOcean Spaces
# @markdown ```text
# @markdown S3_ACCESS_KEY    = DO00****************
# @markdown S3_SECRET_KEY    = ****************************************
# @markdown S3_BUCKET_NAME   = my-do-space
# @markdown S3_ENDPOINT_URL  = https://nyc3.digitaloceanspaces.com   ← e.g. nyc3 / sfo3 / ams3 / sgp1 / fra1
# @markdown S3_REGION        = nyc3                                  ← match the region in URL
# @markdown ```
# @markdown
# @markdown #### ⬛ MinIO / self-hosted
# @markdown ```text
# @markdown S3_ACCESS_KEY    = <your-access-key>
# @markdown S3_SECRET_KEY    = <your-secret-key>
# @markdown S3_BUCKET_NAME   = my-minio-bucket
# @markdown S3_ENDPOINT_URL  = https://your-minio.example.com   ← public HTTPS endpoint
# @markdown S3_REGION        = us-east-1                        ← MinIO default
# @markdown ```
# @markdown
# @markdown #### 🟪 Storj DCS / Linode / Scaleway / IDrive e2 / Vultr / OVH / Yandex / Alibaba
# @markdown ```text
# @markdown S3_ENDPOINT_URL  = https://<provider-endpoint-from-their-docs>
# @markdown S3_REGION        = <region-as-required-by-provider>
# @markdown ```
# @markdown <sub>Full list with endpoints in <a href="https://github.com/ajithvnr2001/Telegram-Leecher/blob/feat/s3-integration/docs/S3_GUIDE.md#other-s3-compatible-providers">docs/S3_GUIDE.md → Other S3-compatible providers</a></sub>
# @markdown
# @markdown </details>
# @markdown
# @markdown ---
S3_ACCESS_KEY = ""  # @param {type: "string"}
S3_SECRET_KEY = ""  # @param {type: "string"}
S3_BUCKET_NAME = ""  # @param {type: "string"}
S3_ENDPOINT_URL = ""  # @param {type: "string"}
S3_REGION = "us-east-1"  # @param {type: "string"}

# @markdown ---
# @markdown ### 📚 Quick command cheat sheet
# @markdown - `/tupload` &nbsp;&nbsp;— leech links to Telegram
# @markdown - `/gdupload` — mirror to Google Drive
# @markdown - `/ytupload` — YouTube / yt-dlp leech
# @markdown - `/drupload` — leech a local Colab folder
# @markdown - `/s3upload` &nbsp;**☁️ NEW** &nbsp;— mirror downloads to your S3 / Wasabi bucket (>2 GB OK, multipart)
# @markdown - `/s3leech` &nbsp;&nbsp;**📥 NEW** &nbsp;— leech `s3://bucket/key` or `s3://bucket/folder/` to Telegram
# @markdown - `/s3bucket <name>` — change destination bucket on the fly
# @markdown - `/s3prefix <folder>` — set a destination key prefix
# @markdown
# @markdown #### 🔁 **Whole-bucket iterative mode + crash-resume** (auto)
# @markdown - Point `/s3leech` or `/s3upload` at `s3://my-bucket/` or `s3://my-bucket/folder/` and the bot processes objects **one at a time** (download → split if >2 GB → upload → cleanup → next). Works for terabyte-sized buckets on a 84 GB Colab disk.
# @markdown - The tracker is mirrored to `s3://<S3_BUCKET_NAME>/s3teletracker.json` after every transfer, so if Colab crashes mid-batch you can simply re-run the same command in a fresh runtime — the bot skips already-processed objects and resumes from where it left off.
# @markdown - To force a full re-run, delete `s3teletracker.json` from the bucket via your provider's web console.
# @markdown
# @markdown <details><summary><b>📨 Click for ready-to-paste sample DM commands</b></summary>
# @markdown
# @markdown **Mirror an internet file → S3 (Regular)**
# @markdown ```text
# @markdown /s3upload
# @markdown
# @markdown https://speed.hetzner.de/100MB.bin
# @markdown [test-100mb.bin]
# @markdown ```
# @markdown
# @markdown **Mirror a Google Drive link → S3 (Compress)**
# @markdown ```text
# @markdown /s3upload
# @markdown
# @markdown https://drive.google.com/file/d/<file-id>/view
# @markdown [my-archive.zip]
# @markdown {zip-pw-if-any}
# @markdown ```
# @markdown
# @markdown **Leech a single S3 object → Telegram**
# @markdown ```text
# @markdown /s3leech
# @markdown
# @markdown s3://my-bucket/Uploaded__2026-05-28_19-45-21/test-100mb.bin
# @markdown ```
# @markdown
# @markdown **Leech a whole S3 folder/prefix → Telegram (zipped)**
# @markdown ```text
# @markdown /s3leech
# @markdown
# @markdown s3://my-bucket/photos/vacation-2025/
# @markdown {gallery-pw}
# @markdown ```
# @markdown
# @markdown **Copy from one S3 bucket to another**
# @markdown ```text
# @markdown /s3bucket destination-bucket
# @markdown /s3upload
# @markdown
# @markdown s3://source-bucket/path/to/file.mkv
# @markdown ```
# @markdown
# @markdown **Set a persistent S3 destination prefix, then mirror many files**
# @markdown ```text
# @markdown /s3prefix archive/2026-Q2
# @markdown /s3upload
# @markdown
# @markdown https://example.com/a.iso
# @markdown https://example.com/b.iso
# @markdown https://example.com/c.iso
# @markdown ```
# @markdown
# @markdown **Extract an archive that lives in S3 → mirror contents to Drive**
# @markdown ```text
# @markdown /gdupload
# @markdown
# @markdown s3://my-bucket/backups/2026-05-01.tar.gz
# @markdown (archive_password)
# @markdown ```
# @markdown
# @markdown **Big-file (>2 GB) S3 → Telegram (auto-split into <2 GB parts)**
# @markdown ```text
# @markdown /s3leech
# @markdown
# @markdown s3://my-bucket/movies/big-blockbuster-5gb.mkv
# @markdown [Movie Title.mkv]
# @markdown ```
# @markdown
# @markdown **Whole bucket → Telegram (iterative + auto-resume on Colab crash)**
# @markdown ```text
# @markdown /s3leech
# @markdown
# @markdown s3://my-bucket/                          ← whole bucket
# @markdown ```
# @markdown <sub>Bot processes objects one-at-a-time, splits >2 GB to &lt;2 GB Telegram parts, persists tracker to <code>s3://&lt;S3_BUCKET_NAME&gt;/s3teletracker.json</code> after each object. If Colab crashes, just re-run the same command — already-completed objects are skipped automatically.</sub>
# @markdown
# @markdown **Mirror whole bucket → another bucket (S3-to-S3, iterative + resume)**
# @markdown ```text
# @markdown /s3bucket destination-bucket
# @markdown /s3upload
# @markdown
# @markdown s3://source-bucket/folder/
# @markdown ```
# @markdown
# @markdown </details>
# @markdown
# @markdown All S3 transfers are logged to `/content/Telegram-Leecher/s3teletracker.json` with `uploaded` and `downloaded` arrays.
# @markdown
# @markdown 📖 In-depth provider walkthroughs (creds, IAM policy, region tables, gotchas): see <a href="https://github.com/ajithvnr2001/Telegram-Leecher/blob/feat/s3-integration/docs/S3_GUIDE.md">docs/S3_GUIDE.md</a>


import subprocess, time, json, shutil, os
from IPython.display import clear_output
from threading import Thread

Working = True

banner = '''

 ____   ____.______  ._______  .______       _____._.______  .___  ____   ____
 \\   \\_/   /: __   \\ : .___  \\ :      \\      \\__ _:|: __   \\ : __| \\   \\_/   /
  \\___ ___/ |  \\____|| :   |  ||       |       |  :||  \\____|| : |  \\___ ___/ 
  /   _   \\ |   :  \\ |     :  ||   |   |       |   ||   :  \\ |   |  /   _   \\ 
 /___/ \\___\\|   |___\\ \\_. ___/ |___|   |       |   ||   |___\\|   | /___/ \\___\\
            |___|       :/         |___|       |___||___|    |___|            
                        :                                                     
                                                                              
 
              _____     __     __     __              __          
             / ___/__  / /__ _/ /    / / ___ ___ ____/ /  ___ ____
            / /__/ _ \\/ / _ `/ _ \\  / /_/ -_) -_) __/ _ \\/ -_) __/
            \\___/\\___/_/\\_,_/_.__/ /____|__/\\__/\\__/_//_/\\__/_/   

                                                

'''

print(banner)

def Loading():
    white = 37
    black = 0
    while Working:
        print("\r" + "░"*white + "▒▒"+ "▓"*black + "▒▒" + "░"*white, end="")
        black = (black + 2) % 75
        white = (white -1) if white != 0 else 37
        time.sleep(2)
    clear_output()


_Thread = Thread(target=Loading, name="Prepare", args=())
_Thread.start()

if len(str(DUMP_ID)) == 10 and "-100" not in str(DUMP_ID):
    n_dump = "-100" + str(DUMP_ID)
    DUMP_ID = int(n_dump)

if os.path.exists("/content/sample_data"):
    shutil.rmtree("/content/sample_data")

# IMPORTANT: this MUST point to the fork + branch that contains the S3
# integration and the Python 3.12 event-loop fix. The original upstream repo
# does NOT have those changes, so cloning it brings back the old code and the
# "RuntimeError: There is no current event loop" crash.
# Default to the feature branch (it always has every fix). Switch REPO_BRANCH
# to "main" only AFTER the PR is merged into your fork's main.
REPO_URL = "https://github.com/ajithvnr2001/Telegram-Leecher"  # @param {type:"string"}
REPO_BRANCH = "feat/s3-integration"  # @param {type:"string"}

# Always start from a clean checkout so a stale/old clone can't linger.
subprocess.run("rm -rf /content/Telegram-Leecher", shell=True)
cmd = f"git clone -b {REPO_BRANCH} {REPO_URL} /content/Telegram-Leecher"
proc = subprocess.run(cmd, shell=True)
# Fallback: if the chosen branch doesn't exist (e.g. it was deleted after a
# merge), fall back to the default branch so the clone still succeeds.
if not os.path.exists("/content/Telegram-Leecher/colab_leecher/__init__.py"):
    print(f"Branch '{REPO_BRANCH}' not found — cloning default branch instead.")
    subprocess.run("rm -rf /content/Telegram-Leecher", shell=True)
    subprocess.run(f"git clone {REPO_URL} /content/Telegram-Leecher", shell=True)

# ---------------------------------------------------------------------------
# Event-loop safety patch (Python 3.12 + uvloop)
# uvloop.install() swaps the event-loop policy but does NOT create a loop, and
# Python 3.12 asyncio.get_event_loop() raises 'no current event loop' when none
# is set — which Pyrogram's Client()/Dispatcher() hits on import. This patch
# guarantees a loop is created+set right before the Client is built, and is
# idempotent: it's a no-op if the cloned code already has the fix, and it
# repairs the file even if an older/upstream revision was somehow cloned.
# ---------------------------------------------------------------------------
init_path = "/content/Telegram-Leecher/colab_leecher/__init__.py"
try:
    with open(init_path, "r") as _f:
        _src = _f.read()
    if "asyncio.new_event_loop()" not in _src and "colab_bot = Client(" in _src:
        if "import asyncio" not in _src:
            _src = "import asyncio\n" + _src
        _src = _src.replace(
            "colab_bot = Client(",
            "loop = asyncio.new_event_loop()\nasyncio.set_event_loop(loop)\ncolab_bot = Client(",
            1,
        )
        with open(init_path, "w") as _f:
            _f.write(_src)
        print("✅ Applied Python 3.12 event-loop safety patch to colab_leecher/__init__.py")
    else:
        print("✅ Event-loop fix already present in colab_leecher/__init__.py")
except Exception as _e:
    print(f"⚠️  Could not apply event-loop safety patch: {_e}")

cmd = "apt update && apt install ffmpeg aria2"
proc = subprocess.run(cmd, shell=True)
cmd = "pip3 install -r /content/Telegram-Leecher/requirements.txt"
proc = subprocess.run(cmd, shell=True)

# Validate S3 config (warn-only — bot still starts; /s3* commands will tell the user
# what's missing if they're triggered without complete credentials).
_s3_partial = any([S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET_NAME])
_s3_complete = all([S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET_NAME])
if _s3_partial and not _s3_complete:
    print(
        "\n⚠️  S3 config is partially set — /s3upload and /s3leech will be unavailable until\n"
        "   S3_ACCESS_KEY, S3_SECRET_KEY and S3_BUCKET_NAME are all filled in.\n"
    )
elif _s3_complete:
    _endpoint_label = S3_ENDPOINT_URL if S3_ENDPOINT_URL else "AWS S3 (default)"
    print(f"\n☁️  S3 enabled → bucket=<{S3_BUCKET_NAME}> region=<{S3_REGION}> endpoint=<{_endpoint_label}>\n")

credentials = {
    "API_ID": API_ID,
    "API_HASH": API_HASH,
    "BOT_TOKEN": BOT_TOKEN,
    "USER_ID": USER_ID,
    "DUMP_ID": DUMP_ID,
    "S3_ACCESS_KEY": S3_ACCESS_KEY,
    "S3_SECRET_KEY": S3_SECRET_KEY,
    "S3_BUCKET_NAME": S3_BUCKET_NAME,
    "S3_ENDPOINT_URL": S3_ENDPOINT_URL,
    "S3_REGION": S3_REGION,
}

with open('/content/Telegram-Leecher/credentials.json', 'w') as file:
    file.write(json.dumps(credentials))

Working = False

if os.path.exists("/content/Telegram-Leecher/my_bot.session"):
    os.remove("/content/Telegram-Leecher/my_bot.session") # Remove previous bot session
    
print("\rStarting Bot....")

!cd /content/Telegram-Leecher/ && python3 -m colab_leecher #type:ignore
