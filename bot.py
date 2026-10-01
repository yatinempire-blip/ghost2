import os
import re
import random
import asyncio
import sys
import subprocess
import urllib.request
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])
    import yt_dlp

from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto, InputMediaVideo, ForceReply

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

# ===================== MEMORY =====================
user_modes = {}
user_watermark_text = {}          # user_id : "Crystal Cool Text"
waiting_for_watermark = set()     # users currently setting watermark

HASHTAGS = "\n\n#viralreels #explorepage #trendingaudio #fashionlookbook #modelaesthetic #4kcontent #foryoupage #outfitinspiration"

# ===================== FONT =====================
def ensure_font():
    if not os.path.exists(FONT_FILE):
        print("Downloading font...")
        try:
            urllib.request.urlretrieve(FONT_URL, FONT_FILE)
            print("Font ready")
        except Exception as e:
            print("Font download failed:", e)

ensure_font()

# ===================== HELPERS =====================
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

def get_main_menu():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📸 Image Stealth Wash"), KeyboardButton("🎥 Video Stealth Wash")],
            [KeyboardButton("🔕 Mute & Wash Video"), KeyboardButton("📺 YouTube Stealth Wash")],
            [KeyboardButton("🔗 Insta Link Stealth Wash")]
        ],
        resize_keyboard=True
    )

# ===================== START =====================
@app.on_message(filters.command(["start", "menu"]))
async def start_cmd(client, message):
    user_id = message.from_user.id
    waiting_for_watermark.add(user_id)

    await message.reply_text(
        "🤖 **GHOST OPERATOR V7.0**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Pehle apna **Watermark Text** bhejo.\n\n"
        "Example: `Crystal Cool` ya `Alishya Oberoi`\n\n"
        "Ye text har media pe lagega.\n"
        "Dubara change karna ho to `/start` karna.",
        reply_markup=ForceReply(selective=True)
    )

# ===================== WATERMARK SET =====================
@app.on_message(filters.text & filters.reply)
async def set_watermark_text(client, message):
    user_id = message.from_user.id

    if user_id not in waiting_for_watermark:
        return

    text = message.text.strip()
    if len(text) < 2 or len(text) > 30:
        await message.reply_text("Watermark 2 se 30 character ke beech hona chahiye. Dobara bhejo.")
        return

    user_watermark_text[user_id] = text
    waiting_for_watermark.discard(user_id)

    await message.reply_text(
        f"✅ Watermark set ho gaya: **{text}**\n\n"
        "Ab mode select karo ya seedha media / Instagram link bhejo.",
        reply_markup=get_main_menu()
    )

# ===================== MODE SELECT =====================
@app.on_message(filters.regex(r"^(📸 Image Stealth Wash|🎥 Video Stealth Wash|🔕 Mute & Wash Video|📺 YouTube Stealth Wash|🔗 Insta Link Stealth Wash)$"))
async def set_mode(client, message):
    user_id = message.from_user.id
    user_modes[user_id] = message.text
    await message.reply_text(f"✅ Mode: `{message.text}`", reply_markup=get_main_menu())

# ===================== PROCESS FILE =====================
async def process_file(file_path, user_id, mode, is_image=False):
    ext = file_path.rsplit(".", 1)[-1].lower()
    out_path = os.path.join(PROCESSED_DIR, f"clean_{user_id}_{random.randint(10000,99999)}.{ext}")

    wm_text = user_watermark_text.get(user_id, "Ghost")
    font_param = f":fontfile={FONT_FILE}" if os.path.exists(FONT_FILE) else ""

    # Simplified safe filter (less chance of -22 error)
    if is_image or ext in ["jpg", "jpeg", "png", "webp"]:
        vf = (
            f"crop=iw*0.97:ih*0.97,"
            f"eq=contrast=1.03:brightness=0.01,"
            f"noise=alls=1.5:allf=t+u,"
            f"drawtext=text='{wm_text}'{font_param}:x=(w-text_w)/2:y=h-th-30:"
            f"fontsize=36:fontcolor=white@0.9:shadowcolor=black@0.6:shadowx=2:shadowy=2"
        )
        cmd = [
            "ffmpeg", "-y", "-i", file_path,
            "-map_metadata", "-1",
            "-vf", vf,
            "-q:v", "2",
            out_path
        ]
    else:
        # Video
        speed = 1.04 if "YouTube" in mode else 1.05
        vf = (
            f"crop=iw*0.97:ih*0.97,"
            f"eq=contrast=1.03:brightness=0.01,"
            f"noise=alls=1.2:allf=t+u,"
            f"setpts=1/{speed}*PTS,"
            f"drawtext=text='{wm_text}'{font_param}:x=(w-text_w)/2:y=h-th-35:"
            f"fontsize=40:fontcolor=white@0.9:shadowcolor=black@0.6:shadowx=2:shadowy=2"
        )

        cmd = [
            "ffmpeg", "-y", "-i", file_path,
            "-map_metadata", "-1",
            "-vf", vf,
            "-af", f"atempo={speed}",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            out_path
        ]

        if mode == "🔕 Mute & Wash Video":
            cmd = [
                "ffmpeg", "-y", "-i", file_path,
                "-map_metadata", "-1",
                "-vf", vf,
                "-an",
                "-c:v", "libx264", "-crf", "18", "-preset", "fast",
                "-movflags", "+faststart",
                out_path
            ]

    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0 or not os.path.exists(out_path):
        err = stderr.decode()[-300:] if stderr else "Unknown"
        raise RuntimeError(err)

    return out_path

# ===================== INSTAGRAM =====================
def download_instagram(url, folder):
    ydl_opts = {
        "outtmpl": os.path.join(folder, "%(id)s_%(autonumber)02d.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "format": "best",
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.instagram.com/",
        }
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        caption = ""
        if info:
            caption = info.get("description") or info.get("title") or ""
        return caption.strip()

# ===================== TEXT HANDLER (Instagram Links) =====================
@app.on_message(filters.text & ~filters.command(["start", "menu"]))
async def handle_text(client, message):
    user_id = message.from_user.id
    text = message.text.strip()

    if user_id in waiting_for_watermark:
        return

    if "instagram.com" not in text and "instagr.am" not in text:
        return

    # Default mode
    user_modes[user_id] = "🔗 Insta Link Stealth Wash"
    if user_id not in user_watermark_text:
        user_watermark_text[user_id] = "Ghost"

    status = await message.reply_text("📥 Instagram se media nikal raha hoon...")
    task_dir = os.path.join(DOWNLOAD_DIR, f"insta_{user_id}_{random.randint(1000,9999)}")
    os.makedirs(task_dir, exist_ok=True)
    processed = []

    try:
        caption = await asyncio.to_thread(download_instagram, text, task_dir)

        files = sorted([
            os.path.join(task_dir, f) for f in os.listdir(task_dir)
            if os.path.isfile(os.path.join(task_dir, f)) and not f.endswith((".json", ".info.json", ".description"))
        ])

        if not files:
            await safe_edit(status, "❌ Media nahi nikal paya. Post private ho sakti hai ya Instagram block kar raha hai.")
            return

        await safe_edit(status, f"🔄 {len(files)} files process ho rahi hain...")

        media_group = []
        for fpath in files:
            is_img = fpath.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
            out = await process_file(fpath, user_id, "🔗 Insta Link Stealth Wash", is_image=is_img)
            processed.append(out)

            if is_img:
                media_group.append(InputMediaPhoto(media=out))
            else:
                media_group.append(InputMediaVideo(media=out, supports_streaming=True))

        # Send as album (up to 10 at a time if more than 10)
        for i in range(0, len(media_group), 10):
            chunk = media_group[i:i+10]
            await client.send_media_group(chat_id=user_id, media=chunk)

        await safe_delete(status)

        final_caption = f"{caption}\n\n{HASHTAGS}" if caption else HASHTAGS
        await message.reply_text(f"📝 **CAPTION:**\n`{final_caption}`")

    except Exception as e:
        await safe_edit(status, f"❌ Error: {str(e)[:300]}")
    finally:
        # Cleanup
        for f in os.listdir(task_dir) if os.path.exists(task_dir) else []:
            try: os.remove(os.path.join(task_dir, f))
            except: pass
        try: os.rmdir(task_dir)
        except: pass
        for p in processed:
            try: os.remove(p)
            except: pass

# ===================== MEDIA HANDLER =====================
@app.on_message(filters.photo | filters.video | filters.document)
async def handle_media(client, message):
    user_id = message.from_user.id

    if user_id in waiting_for_watermark:
        await message.reply_text("Pehle `/start` karke watermark set karo.")
        return

    if user_id not in user_modes:
        user_modes[user_id] = "📸 Image Stealth Wash" if message.photo else "🎥 Video Stealth Wash"
    if user_id not in user_watermark_text:
        user_watermark_text[user_id] = "Ghost"

    mode = user_modes[user_id]
    status = await message.reply_text("🔄 Processing...")

    try:
        file_path = await message.download(file_name=os.path.join(DOWNLOAD_DIR, ""))
        is_img = message.photo or file_path.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))

        out = await process_file(file_path, user_id, mode, is_image=is_img)

        if is_img:
            await message.reply_photo(photo=out)
        else:
            await message.reply_video(video=out, supports_streaming=True)

        await safe_delete(status)

        # Cleanup
        try: os.remove(file_path)
        except: pass
        try: os.remove(out)
        except: pass

    except Exception as e:
        await safe_edit(status, f"❌ Error: {str(e)[:280]}")

# ===================== RUN =====================
if __name__ == "__main__":
    print("🚀 Ghost Operator V7.0 Started")
    app.run()
