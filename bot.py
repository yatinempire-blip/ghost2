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

# ================= MEMORY =================
user_modes = {}
user_watermark_text = {}
waiting_for_watermark = set()

HASHTAGS = "\n\n#viralreels #explorepage #trendingaudio #fashionlookbook #modelaesthetic #4kcontent #foryoupage #outfitinspiration"

def ensure_font():
    if not os.path.exists(FONT_FILE):
        try:
            urllib.request.urlretrieve(FONT_URL, FONT_FILE)
            print("Font downloaded")
        except Exception as e:
            print("Font error:", e)

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

def get_main_menu():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📸 Image Stealth Wash"), KeyboardButton("🎥 Video Stealth Wash")],
            [KeyboardButton("🔕 Mute & Wash Video"), KeyboardButton("📺 YouTube Stealth Wash")],
            [KeyboardButton("🔗 Insta Link Stealth Wash")]
        ],
        resize_keyboard=True
    )

# ================= START =================
@app.on_message(filters.command(["start", "menu"]))
async def start_cmd(client, message):
    user_id = message.from_user.id
    waiting_for_watermark.add(user_id)

    await message.reply_text(
        "🤖 **GHOST OPERATOR V7.1**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Apna **Watermark Text** bhejo (ek baar):\n\n"
        "Example: `Crystal Cool`\n"
        "Example: `Alishya Oberoi`\n\n"
        "Ye text ab se har media pe lagega.\n"
        "Change karna ho to phir se `/start` karo."
    )

# ================= TEXT HANDLER =================
@app.on_message(filters.text & ~filters.command(["start", "menu"]))
async def handle_text(client, message):
    user_id = message.from_user.id
    text = message.text.strip()

    # 1. Agar watermark set karne ka wait ho raha hai
    if user_id in waiting_for_watermark:
        if len(text) < 2 or len(text) > 40:
            await message.reply_text("Watermark 2 se 40 character ke beech mein likho. Dobara bhejo.")
            return

        user_watermark_text[user_id] = text
        waiting_for_watermark.discard(user_id)

        await message.reply_text(
            f"✅ Watermark set ho gaya: **{text}**\n\n"
            "Ab mode choose karo ya seedha photo/video/Instagram link bhejo.",
            reply_markup=get_main_menu()
        )
        return

    # 2. Mode buttons
    if text in ["📸 Image Stealth Wash", "🎥 Video Stealth Wash", "🔕 Mute & Wash Video", 
                "📺 YouTube Stealth Wash", "🔗 Insta Link Stealth Wash"]:
        user_modes[user_id] = text
        await message.reply_text(f"✅ Mode set: `{text}`", reply_markup=get_main_menu())
        return

    # 3. Instagram Link
    if "instagram.com" in text or "instagr.am" in text:
        if user_id not in user_watermark_text:
            await message.reply_text("Pehle `/start` karke watermark set karo.")
            return

        user_modes[user_id] = "🔗 Insta Link Stealth Wash"
        status = await message.reply_text("📥 Instagram media nikal raha hoon...")

        task_dir = os.path.join(DOWNLOAD_DIR, f"insta_{user_id}_{random.randint(1000,9999)}")
        os.makedirs(task_dir, exist_ok=True)
        processed = []

        try:
            caption = await asyncio.to_thread(download_instagram, text, task_dir)

            files = sorted([
                os.path.join(task_dir, f) for f in os.listdir(task_dir)
                if os.path.isfile(os.path.join(task_dir, f)) and not f.endswith((".json", ".info.json"))
            ])

            if not files:
                await safe_edit(status, "❌ Media nahi mila. Post private ho sakti hai.")
                return

            await safe_edit(status, f"🔄 {len(files)} files process ho rahi hain...")

            media_group = []
            for fpath in files:
                is_img = fpath.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
                out = await process_file(fpath, user_id, is_image=is_img)
                processed.append(out)

                if is_img:
                    media_group.append(InputMediaPhoto(media=out))
                else:
                    media_group.append(InputMediaVideo(media=out, supports_streaming=True))

            # Send in chunks of 10
            for i in range(0, len(media_group), 10):
                await client.send_media_group(user_id, media=media_group[i:i+10])

            await safe_delete(status)

            final_cap = f"{caption}\n\n{HASHTAGS}" if caption else HASHTAGS
            await message.reply_text(f"📝 **CAPTION:**\n`{final_cap}`")

        except Exception as e:
            await safe_edit(status, f"❌ Error: {str(e)[:250]}")
        finally:
            cleanup_folder(task_dir)
            for p in processed:
                try: os.remove(p)
                except: pass

# ================= PROCESS FILE =================
async def process_file(file_path, user_id, is_image=False):
    ext = file_path.rsplit(".", 1)[-1].lower()
    out_path = os.path.join(PROCESSED_DIR, f"clean_{user_id}_{random.randint(10000,99999)}.{ext}")

    wm = user_watermark_text.get(user_id, "Ghost")
    font = f":fontfile={FONT_FILE}" if os.path.exists(FONT_FILE) else ""

    if is_image or ext in ["jpg", "jpeg", "png", "webp"]:
        vf = (
            f"crop=iw*0.97:ih*0.97,"
            f"eq=contrast=1.03:brightness=0.01,"
            f"noise=alls=1.5:allf=t+u,"
            f"drawtext=text='{wm}'{font}:x=(w-text_w)/2:y=h-th-28:"
            f"fontsize=34:fontcolor=white@0.9:shadowcolor=black@0.6:shadowx=2:shadowy=2"
        )
        cmd = ["ffmpeg", "-y", "-i", file_path, "-map_metadata", "-1", "-vf", vf, "-q:v", "2", out_path]
    else:
        vf = (
            f"crop=iw*0.97:ih*0.97,"
            f"eq=contrast=1.03:brightness=0.01,"
            f"noise=alls=1.2:allf=t+u,"
            f"setpts=1/1.04*PTS,"
            f"drawtext=text='{wm}'{font}:x=(w-text_w)/2:y=h-th-32:"
            f"fontsize=38:fontcolor=white@0.9:shadowcolor=black@0.6:shadowx=2:shadowy=2"
        )
        cmd = [
            "ffmpeg", "-y", "-i", file_path,
            "-map_metadata", "-1",
            "-vf", vf,
            "-af", "atempo=1.04",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            out_path
        ]

    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    _, stderr = await proc.communicate()

    if proc.returncode != 0 or not os.path.exists(out_path):
        raise RuntimeError(stderr.decode()[-250:] if stderr else "FFmpeg failed")

    return out_path

def download_instagram(url, folder):
    opts = {
        "outtmpl": os.path.join(folder, "%(id)s_%(autonumber)02d.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "format": "best",
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": "https://www.instagram.com/",
        }
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if info:
            return (info.get("description") or info.get("title") or "").strip()
        return ""

def cleanup_folder(folder):
    if os.path.exists(folder):
        for f in os.listdir(folder):
            try: os.remove(os.path.join(folder, f))
            except: pass
        try: os.rmdir(folder)
        except: pass

# ================= MEDIA HANDLER =================
@app.on_message(filters.photo | filters.video | filters.document)
async def handle_media(client, message):
    user_id = message.from_user.id

    if user_id in waiting_for_watermark or user_id not in user_watermark_text:
        await message.reply_text("Pehle `/start` karke watermark set karo.")
        return

    if user_id not in user_modes:
        user_modes[user_id] = "📸 Image Stealth Wash" if message.photo else "🎥 Video Stealth Wash"

    status = await message.reply_text("🔄 Processing...")

    try:
        file_path = await message.download(file_name=os.path.join(DOWNLOAD_DIR, ""))
        is_img = bool(message.photo) or file_path.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))

        out = await process_file(file_path, user_id, is_image=is_img)

        if is_img:
            await message.reply_photo(out)
        else:
            await message.reply_video(out, supports_streaming=True)

        await safe_delete(status)

        try: os.remove(file_path)
        except: pass
        try: os.remove(out)
        except: pass

    except Exception as e:
        await safe_edit(status, f"❌ Error: {str(e)[:250]}")

if __name__ == "__main__":
    print("🚀 Ghost Operator V7.1 Started")
    app.run()
