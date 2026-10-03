import os
import random
import asyncio
import sys
import subprocess
import urllib.request

try:
    import yt_dlp
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])
    import yt_dlp

from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto, InputMediaVideo

# ===================== CREDENTIALS =====================
API_ID = 36511364
API_HASH = "249685fabdef6018e8c84dec25942b91"
BOT_TOKEN = "8608879552:AAHMWoFvAaiyQ_5xXOixRCdtZSotiIikrVw"
# =======================================================

app = Client("ghost_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DOWNLOAD_DIR = "downloads"
PROCESSED_DIR = "processed"
FONT_FILE = "DejaVuSans.ttf"
FONT_URL = "https://cdn.jsdelivr.net/npm/dejavu-fonts-ttf@2.37/ttf/DejaVuSans.ttf"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

user_modes = {}
user_watermark = {}          # uid : str or None
waiting_for_wm = set()
media_group_cache = {}

CAPTIONS = [
    "POV: You couldn't scroll past this look. 🙈 Rate this look 1 to 10! 🖤\n\nComplete 4K lookbook available in VIP. ✨\nJoin VIP ₹179/Month 💋\nLink in bio 👇",
    "This one hits different 🔥\n\nFull unreleased set is live in VIP Server.\nJoin now 🖤",
    "Too clean to ignore 👀\n\nVIP access for exclusive content.\nLink in bio 👇"
]

def ensure_font():
    if not os.path.exists(FONT_FILE):
        try:
            urllib.request.urlretrieve(FONT_URL, FONT_FILE)
        except:
            pass

ensure_font()

async def safe_edit(msg, text):
    try:
        await msg.edit_text(text)
    except:
        pass

async def safe_delete(msg):
    try:
        await msg.delete()
    except:
        pass

def get_start_kb():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("💧 Set Watermark"), KeyboardButton("❌ No Watermark")]],
        resize_keyboard=True
    )

def get_main_kb():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📸 Image Stealth Wash"), KeyboardButton("🎥 Video Stealth Wash")],
            [KeyboardButton("🔕 Mute & Wash Video"), KeyboardButton("📺 YouTube Stealth Wash")]
        ],
        resize_keyboard=True
    )

def escape_text(text):
    if not text:
        return ""
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")

@app.on_message(filters.command(["start", "menu"]))
async def start(client, message):
    uid = message.from_user.id
    waiting_for_wm.discard(uid)
    await message.reply_text(
        "🤖 **GHOST OPERATOR V9.0**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Watermark chahiye ya nahi?",
        reply_markup=get_start_kb()
    )

@app.on_message(filters.regex(r"^(💧 Set Watermark|❌ No Watermark)$"))
async def wm_choice(client, message):
    uid = message.from_user.id
    if "No Watermark" in message.text:
        user_watermark[uid] = None
        waiting_for_wm.discard(uid)
        await message.reply_text("✅ Bina Watermark ke ready.\nAb mode choose karo ya media bhejo.", reply_markup=get_main_kb())
    else:
        waiting_for_wm.add(uid)
        await message.reply_text("Watermark text bhejo (2-30 characters):")

@app.on_message(filters.text & \~filters.command(["start", "menu"]))
async def text_handler(client, message):
    uid = message.from_user.id
    text = message.text.strip()

    if uid in waiting_for_wm:
        if 2 <= len(text) <= 30:
            user_watermark[uid] = text
            waiting_for_wm.discard(uid)
            await message.reply_text(f"✅ Watermark set: **{text}**", reply_markup=get_main_kb())
        else:
            await message.reply_text("2 se 30 character ke beech likho.")
        return

    if text in ["📸 Image Stealth Wash", "🎥 Video Stealth Wash", "🔕 Mute & Wash Video", "📺 YouTube Stealth Wash"]:
        user_modes[uid] = text
        await message.reply_text(f"✅ Mode: `{text}`", reply_markup=get_main_kb())

async def process_media(file_path, uid, is_image=False, mute=False):
    ext = file_path.rsplit(".", 1)[-1].lower()
    out = os.path.join(PROCESSED_DIR, f"g_{uid}_{random.randint(10000,99999)}.{ext}")

    wm = user_watermark.get(uid)
    font = f":fontfile={FONT_FILE}" if os.path.exists(FONT_FILE) else ""

    draw = ""
    if wm:
        safe_wm = escape_text(wm)
        draw = (
            f",drawtext=text='{safe_wm}'{font}:x=(w-text_w)/2:y=h-th-18:"
            f"fontsize=19:fontcolor=white@0.87:borderw=1:bordercolor=black@0.4:"
            f"shadowcolor=black@0.55:shadowx=1:shadowy=1"
        )

    crop = round(random.uniform(0.965, 0.978), 3)
    noise = round(random.uniform(1.3, 2.1), 1)
    contrast = round(random.uniform(1.025, 1.05), 3)
    bright = round(random.uniform(0.009, 0.016), 3)

    if is_image or ext in ["jpg", "jpeg", "png", "webp"]:
        vf = f"crop=iw*{crop}:ih*{crop},eq=contrast={contrast}:brightness={bright},noise=alls={noise}:allf=t+u{draw}"
        cmd = ["ffmpeg", "-y", "-i", file_path, "-map_metadata", "-1", "-vf", vf, "-q:v", "2", out]
    else:
        speed = round(random.uniform(1.035, 1.055), 3)
        vf = f"crop=iw*{crop}:ih*{crop},eq=contrast={contrast}:brightness={bright},noise=alls={noise}:allf=t+u,setpts=1/{speed}*PTS{draw}"
        cmd = [
            "ffmpeg", "-y", "-i", file_path, "-map_metadata", "-1",
            "-vf", vf,
            "-c:v", "libx264", "-crf", "17", "-preset", "fast",
            "-movflags", "+faststart", out
        ]
        if mute:
            cmd.insert(-1, "-an")
        else:
            cmd.extend(["-af", f"atempo={speed}", "-c:a", "aac", "-b:a", "128k"])

    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    _, err = await proc.communicate()

    if proc.returncode != 0 or not os.path.exists(out):
        raise RuntimeError(err.decode()[-250:] if err else "FFmpeg error")

    return out

@app.on_message(filters.photo | filters.video | filters.document)
async def media_handler(client, message):
    uid = message.from_user.id

    if uid not in user_watermark:
        await message.reply_text("Pehle /start karke watermark choice karo.")
        return

    if uid not in user_modes:
        user_modes[uid] = "📸 Image Stealth Wash" if message.photo else "🎥 Video Stealth Wash"

    # ===== ALBUM HANDLING =====
    if message.media_group_id:
        mgid = message.media_group_id
        if mgid not in media_group_cache:
            media_group_cache[mgid] = []
            asyncio.create_task(process_album(client, message, mgid, uid))
        media_group_cache[mgid].append(message)
        return

    # ===== SINGLE FILE =====
    status = await message.reply_text("🔄 Processing...")
    try:
        path = await message.download(file_name=os.path.join(DOWNLOAD_DIR, ""))
        is_img = bool(message.photo) or path.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
        mute = user_modes.get(uid) == "🔕 Mute & Wash Video"

        out = await process_media(path, uid, is_img, mute)

        if is_img:
            await message.reply_photo(out)
        else:
            await message.reply_video(out, supports_streaming=True)

        # Single file → alag caption
        await message.reply_text(f"📝 **CAPTION:**\n`{random.choice(CAPTIONS)}`")

        await safe_delete(status)
        try: os.remove(path)
        except: pass
        try: os.remove(out)
        except: pass

    except Exception as e:
        await safe_edit(status, f"❌ {str(e)[:220]}")

async def process_album(client, original, mgid, uid):
    await asyncio.sleep(3.5)  # wait for all files to arrive
    messages = media_group_cache.pop(mgid, [])
    if not messages:
        return

    status = await original.reply_text(f"⏳ Album process ho raha hai ({len(messages)} files)...")
    processed = []
    media_list = []

    try:
        mute = user_modes.get(uid) == "🔕 Mute & Wash Video"

        for msg in messages:
            path = await msg.download(file_name=os.path.join(DOWNLOAD_DIR, ""))
            is_img = bool(msg.photo) or path.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
            out = await process_media(path, uid, is_img, mute)
            processed.append(out)

            if is_img:
                media_list.append(InputMediaPhoto(out))
            else:
                media_list.append(InputMediaVideo(out, supports_streaming=True))

            try: os.remove(path)
            except: pass

        # Send as one album (max 10 at a time)
        for i in range(0, len(media_list), 10):
            await client.send_media_group(uid, media=media_list[i:i+10])

        # ===== SIRF EK CAPTION =====
        await original.reply_text(f"📝 **CAPTION:**\n`{random.choice(CAPTIONS)}`")

        await safe_delete(status)

    except Exception as e:
        await safe_edit(status, f"❌ {str(e)[:200]}")
    finally:
        for p in processed:
            try: os.remove(p)
            except: pass

if __name__ == "__main__":
    print("🚀 Ghost Operator V9.0 Started")
    app.run()
