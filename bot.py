import os
import re
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

API_ID = 36511364
API_HASH = "249685fabdef6018e8c84dec25942b91"
BOT_TOKEN = "8608879552:AAHMWoFvAaiyQ_5xXOixRCdtZSotiIikrVw"

app = Client("ghost_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DOWNLOAD_DIR = "downloads"
PROCESSED_DIR = "processed"
FONT_FILE = "DejaVuSans.ttf"
FONT_URL = "https://cdn.jsdelivr.net/npm/dejavu-fonts-ttf@2.37/ttf/DejaVuSans.ttf"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

user_modes = {}
user_watermark = {}          # uid: str or None
waiting_for_wm = set()
media_group_cache = {}

HASHTAGS = "\n\n#viralreels #explorepage #trendingaudio #fashionlookbook #modelaesthetic #4kcontent #foryoupage #outfitinspiration"

def ensure_font():
    if not os.path.exists(FONT_FILE):
        try:
            urllib.request.urlretrieve(FONT_URL, FONT_FILE)
            print("Font downloaded")
        except Exception as e:
            print("Font download failed:", e)

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
            [KeyboardButton("🔕 Mute & Wash Video"), KeyboardButton("📺 YouTube Stealth Wash")],
            [KeyboardButton("🔗 Insta Link Stealth Wash")]
        ],
        resize_keyboard=True
    )

def escape_drawtext(text: str) -> str:
    """FFmpeg drawtext ke liye special characters escape karo"""
    if not text:
        return ""
    text = text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    return text

@app.on_message(filters.command(["start", "menu"]))
async def start(client, message):
    uid = message.from_user.id
    waiting_for_wm.discard(uid)
    await message.reply_text(
        "🤖 **GHOST OPERATOR V8.1 FINAL**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Watermark chahiye ya nahi?",
        reply_markup=get_start_kb()
    )

@app.on_message(filters.regex(r"^(💧 Set Watermark|❌ No Watermark)$"))
async def wm_choice(client, message):
    uid = message.from_user.id
    if "No Watermark" in message.text:
        user_watermark[uid] = None
        waiting_for_wm.discard(uid)
        await message.reply_text("✅ Bina Watermark ke ready.\nAb mode choose karo ya media/link bhejo.", reply_markup=get_main_kb())
    else:
        waiting_for_wm.add(uid)
        await message.reply_text("Watermark text bhejo (2-30 characters):\nExample: `Crystal Cool`")

@app.on_message(filters.text & ~filters.command(["start", "menu"]))
async def text_handler(client, message):
    uid = message.from_user.id
    text = message.text.strip()

    # Watermark set karna
    if uid in waiting_for_wm:
        if 2 <= len(text) <= 30:
            user_watermark[uid] = text
            waiting_for_wm.discard(uid)
            await message.reply_text(f"✅ Watermark set: **{text}**", reply_markup=get_main_kb())
        else:
            await message.reply_text("2 se 30 character ke beech likho.")
        return

    # Mode select
    if text in ["📸 Image Stealth Wash", "🎥 Video Stealth Wash", "🔕 Mute & Wash Video", "📺 YouTube Stealth Wash", "🔗 Insta Link Stealth Wash"]:
        user_modes[uid] = text
        await message.reply_text(f"✅ Mode set: `{text}`", reply_markup=get_main_kb())
        return

    # Instagram Link
    if "instagram.com" in text or "instagr.am" in text:
        if uid not in user_watermark:
            await message.reply_text("Pehle /start karke watermark choice karo.")
            return

        status = await message.reply_text("📥 Instagram media nikal raha hoon...")
        task_dir = os.path.join(DOWNLOAD_DIR, f"insta_{uid}_{random.randint(1000,9999)}")
        os.makedirs(task_dir, exist_ok=True)
        processed = []

        try:
            caption = await asyncio.to_thread(download_instagram, text, task_dir)
            files = sorted([
                os.path.join(task_dir, f) for f in os.listdir(task_dir)
                if os.path.isfile(os.path.join(task_dir, f)) and not f.endswith((".json", ".info.json", ".description"))
            ])

            if not files:
                await safe_edit(status, "❌ Media nahi nikal paya.\nInstagram ne is server ke IP ko block kiya hua hai.")
                return

            await safe_edit(status, f"🔄 {len(files)} files process ho rahi hain...")

            media_list = []
            for fpath in files:
                is_img = fpath.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
                out = await process_media(fpath, uid, is_img)
                processed.append(out)
                if is_img:
                    media_list.append(InputMediaPhoto(out))
                else:
                    media_list.append(InputMediaVideo(out, supports_streaming=True))

            for i in range(0, len(media_list), 10):
                await client.send_media_group(uid, media=media_list[i:i+10])

            await safe_delete(status)
            final = f"{caption}\n\n{HASHTAGS}" if caption else HASHTAGS
            await message.reply_text(f"📝 **CAPTION:**\n`{final}`")

        except Exception as e:
            await safe_edit(status, f"❌ Error: {str(e)[:250]}")
        finally:
            cleanup(task_dir)
            for p in processed:
                try: os.remove(p)
                except: pass

async def process_media(file_path, uid, is_image=False):
    ext = file_path.rsplit(".", 1)[-1].lower()
    out = os.path.join(PROCESSED_DIR, f"g_{uid}_{random.randint(10000,99999)}.{ext}")

    wm = user_watermark.get(uid)
    font_part = f":fontfile={FONT_FILE}" if os.path.exists(FONT_FILE) else ""

    # Premium watermark
    draw = ""
    if wm:
        safe_wm = escape_drawtext(wm)
        draw = (
            f",drawtext=text='{safe_wm}'{font_part}:x=(w-text_w)/2:y=h-th-18:"
            f"fontsize=19:fontcolor=white@0.87:borderw=1:bordercolor=black@0.45:"
            f"shadowcolor=black@0.55:shadowx=1:shadowy=1"
        )

    # Strong random stealth
    crop = round(random.uniform(0.964, 0.978), 3)
    noise = round(random.uniform(1.3, 2.2), 1)
    contrast = round(random.uniform(1.025, 1.055), 3)
    bright = round(random.uniform(0.009, 0.017), 3)

    if is_image or ext in ["jpg", "jpeg", "png", "webp"]:
        vf = f"crop=iw*{crop}:ih*{crop},eq=contrast={contrast}:brightness={bright},noise=alls={noise}:allf=t+u{draw}"
        cmd = ["ffmpeg", "-y", "-i", file_path, "-map_metadata", "-1", "-vf", vf, "-q:v", "2", out]
    else:
        speed = round(random.uniform(1.035, 1.055), 3)
        vf = f"crop=iw*{crop}:ih*{crop},eq=contrast={contrast}:brightness={bright},noise=alls={noise}:allf=t+u,setpts=1/{speed}*PTS{draw}"
        cmd = [
            "ffmpeg", "-y", "-i", file_path, "-map_metadata", "-1",
            "-vf", vf, "-af", f"atempo={speed}",
            "-c:v", "libx264", "-crf", "17", "-preset", "fast",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out
        ]

    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    _, err = await proc.communicate()

    if proc.returncode != 0 or not os.path.exists(out):
        raise RuntimeError(err.decode()[-280:] if err else "FFmpeg failed")

    return out

def download_instagram(url, folder):
    opts = {
        "outtmpl": os.path.join(folder, "%(id)s_%(autonumber)02d.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "format": "best",
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.instagram.com/",
            "Origin": "https://www.instagram.com",
        }
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if info:
            return (info.get("description") or info.get("title") or "").strip()
        return ""

def cleanup(folder):
    if os.path.exists(folder):
        for f in os.listdir(folder):
            try: os.remove(os.path.join(folder, f))
            except: pass
        try: os.rmdir(folder)
        except: pass

@app.on_message(filters.photo | filters.video | filters.document)
async def media_handler(client, message):
    uid = message.from_user.id

    if uid not in user_watermark:
        await message.reply_text("Pehle /start karke watermark choice karo.")
        return

    if uid not in user_modes:
        user_modes[uid] = "📸 Image Stealth Wash" if message.photo else "🎥 Video Stealth Wash"

    # Album support
    if message.media_group_id:
        mgid = message.media_group_id
        if mgid not in media_group_cache:
            media_group_cache[mgid] = []
            asyncio.create_task(process_album(client, message, mgid, uid))
        media_group_cache[mgid].append(message)
        return

    status = await message.reply_text("🔄 Processing...")
    try:
        path = await message.download(file_name=os.path.join(DOWNLOAD_DIR, ""))
        is_img = bool(message.photo) or path.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
        out = await process_media(path, uid, is_img)

        if is_img:
            await message.reply_photo(out)
        else:
            await message.reply_video(out, supports_streaming=True)

        await safe_delete(status)
        try: os.remove(path)
        except: pass
        try: os.remove(out)
        except: pass
    except Exception as e:
        await safe_edit(status, f"❌ {str(e)[:230]}")

async def process_album(client, original, mgid, uid):
    await asyncio.sleep(3.5)
    messages = media_group_cache.pop(mgid, [])
    if not messages:
        return

    status = await original.reply_text(f"⏳ Album process ho raha hai ({len(messages)} files)...")
    processed = []
    media_list = []

    try:
        for msg in messages:
            path = await msg.download(file_name=os.path.join(DOWNLOAD_DIR, ""))
            is_img = bool(msg.photo) or path.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
            out = await process_media(path, uid, is_img)
            processed.append(out)
            if is_img:
                media_list.append(InputMediaPhoto(out))
            else:
                media_list.append(InputMediaVideo(out, supports_streaming=True))
            try: os.remove(path)
            except: pass

        for i in range(0, len(media_list), 10):
            await client.send_media_group(uid, media=media_list[i:i+10])

        await safe_delete(status)
    except Exception as e:
        await safe_edit(status, f"❌ {str(e)[:200]}")
    finally:
        for p in processed:
            try: os.remove(p)
            except: pass

if __name__ == "__main__":
    print("🚀 Ghost Operator V8.1 FINAL Started")
    app.run()
