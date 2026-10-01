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
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
    import yt_dlp

from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto, InputMediaVideo

API_ID = 36511364
API_HASH = "249685fabdef6018e8c84dec25942b91"
BOT_TOKEN = "8608879552:AAHwDrvWXsBSR2H7E8B-E4gPVOie-052urw"

app = Client("ghost_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DOWNLOAD_DIR = "downloads"
PROCESSED_DIR = "processed"
FONT_FILE = "DejaVuSans.ttf"
FONT_URL = "https://cdn.jsdelivr.net/npm/dejavu-fonts-ttf@2.37/ttf/DejaVuSans.ttf"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

def ensure_font():
    if not os.path.exists(FONT_FILE):
        print("Downloading font...")
        try:
            urllib.request.urlretrieve(FONT_URL, FONT_FILE)
            print("Font downloaded")
        except Exception as e:
            print(f"Font download failed: {e}")
    else:
        print("Font already present")

ensure_font()

user_modes = {}
user_watermarks = {}
media_group_cache = {}

HASHTAGS = "\n\n#viralreels #explorepage #trendingaudio #fashionlookbook #modelaesthetic #4kcontent #foryoupage #outfitinspiration"

CAPTIONS_SET = [
    (
        "POV: You couldn't scroll past this look. 🙈 Rate this look 1 to 10 in the comments! 🖤\n\n"
        "I’ve uploaded the complete 4K unreleased lookbook into my VIP Telegram Server! 🤫✨\n\n"
        "Join VIP for just ₹179 / Month! 💋\n"
        "Link in bio! 👇🖤" + HASHTAGS,
        "Want to video call & chat with me directly? 🙈 Click the link in my bio now! 👇🖤"
    )
]

async def safe_edit(msg, text):
    if not msg:
        return
    try:
        await msg.edit_text(text)
    except:
        pass

async def safe_delete(msg):
    if not msg:
        return
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

@app.on_message(filters.command(["start", "menu"]))
async def start_cmd(client, message):
    await message.reply_text(
        "🤖 **GHOST OPERATOR ACTIVE (V6.2 FINAL)**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Send any media or Instagram link directly!",
        reply_markup=get_main_menu()
    )

@app.on_message(filters.regex(r"^(✅ Yes, Add Watermark|❌ No Watermark)$"))
async def set_watermark(client, message):
    user_id = message.from_user.id
    user_watermarks[user_id] = "Yes" in message.text
    status = "ON 🟢" if user_watermarks[user_id] else "OFF 🔴"
    await message.reply_text(f"💧 **Watermark:** {status}", reply_markup=get_main_menu())

@app.on_message(filters.regex(r"^(📸 Image Stealth Wash|🎥 Video Stealth Wash|🔕 Mute & Wash Video|📺 YouTube Stealth Wash.*|🔗 Insta Link Stealth Wash)$"))
async def set_mode(client, message):
    user_modes[message.from_user.id] = message.text
    await message.reply_text(f"✅ Mode set: `{message.text}`", reply_markup=get_main_menu())

def build_delogo():
    return (
        "delogo=x=10:y=10:w=180:h=55:show=0,"
        "delogo=x=w-190:y=10:w=180:h=55:show=0,"
        "delogo=x=10:y=h-65:w=180:h=55:show=0,"
        "delogo=x=w-190:y=h-65:w=180:h=55:show=0,"
        "delogo=x=(w-240)/2:y=h-75:w=240:h=65:show=0"
    )

def get_wm_text(mode):
    if "YouTube" in mode:
        return "Professionals Group"
    if "Insta" in mode:
        return "Trusted FF Marketplace"
    return "Alishya Oberoi"

async def process_single_file(client, message_or_path, user_id, mode, apply_wm):
    if isinstance(message_or_path, str):
        file_path = message_or_path
    else:
        file_path = await message_or_path.download(file_name=os.path.join(DOWNLOAD_DIR, ""))

    ext = file_path.rsplit(".", 1)[-1].lower()
    out_name = f"clean_{user_id}_{random.randint(10000,99999)}.{ext}"
    processed_path = os.path.join(PROCESSED_DIR, out_name)

    delogo = build_delogo()
    font = f"fontfile={FONT_FILE}" if os.path.exists(FONT_FILE) else ""

    is_image = ext in ["jpg", "jpeg", "png", "webp"] or mode == "📸 Image Stealth Wash"

    if is_image:
        vf = (
            f"{delogo},"
            "crop=iw*0.975:ih*0.975,"
            "scale=iw:ih,"
            "eq=contrast=1.025:brightness=0.012,"
            "noise=alls=2:allf=t+u"
        )
        if apply_wm:
            text = get_wm_text(mode)
            vf += (
                f",drawtext=text='{text}':{font}:"
                "x=(w-text_w)/2:y=h-th-38:"
                "fontsize=40:fontcolor=white@0.87:"
                "shadowcolor=black@0.6:shadowx=2:shadowy=2"
            )
        cmd = [
            "ffmpeg", "-y", "-i", file_path,
            "-map_metadata", "-1",
            "-vf", vf,
            "-q:v", "2",
            processed_path
        ]
    else:
        if "YouTube" in mode:
            speed, crop, contrast, bright, sat, crf, preset = 1.035, 0.96, 1.04, 0.015, 1.06, 19, "medium"
        else:
            speed, crop, contrast, bright, sat, crf, preset = 1.045, 0.975, 1.03, 0.01, 1.0, 18, "fast"

        vf = (
            f"{delogo},"
            f"crop=iw*{crop}:ih*{crop},"
            "scale=iw:ih,"
            f"eq=contrast={contrast}:brightness={bright}:saturation={sat},"
            "noise=alls=1.5:allf=t+u,"
            f"setpts=1/{speed}*PTS"
        )
        if apply_wm:
            text = get_wm_text(mode)
            vf += (
                f",drawtext=text='{text}':{font}:"
                "x=(w-text_w)/2:y=h-th-42:"
                "fontsize=44:fontcolor=white@0.89:"
                "shadowcolor=black@0.65:shadowx=2:shadowy=2"
            )

        cmd = [
            "ffmpeg", "-y", "-i", file_path,
            "-map_metadata", "-1",
            "-vf", vf,
        ]

        if mode == "🔕 Mute & Wash Video":
            cmd += ["-an"]
        else:
            af = f"atempo={speed}"
            if "YouTube" in mode:
                af += ",asetrate=44100*1.008"
            cmd += ["-af", af, "-c:a", "aac", "-b:a", "128k"]

        cmd += [
            "-c:v", "libx264",
            "-crf", str(crf),
            "-preset", preset,
            "-movflags", "+faststart",
            processed_path
        ]

    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(stderr.decode()[-400:] if stderr else "FFmpeg error")

    if os.path.exists(file_path) and DOWNLOAD_DIR in file_path:
        try:
            os.remove(file_path)
        except:
            pass

    return processed_path

async def process_album_task(client, original_message, mg_id, user_id, mode, apply_wm):
    await asyncio.sleep(3.2)
    messages = media_group_cache.pop(mg_id, [])
    if not messages:
        return

    status = await original_message.reply_text(f"⏳ Processing Album ({len(messages)} files)...")
    processed = []
    media_list = []

    try:
        for msg in messages:
            path = await process_single_file(client, msg, user_id, mode, apply_wm)
            processed.append(path)
            ext = path.rsplit(".", 1)[-1].lower()
            if ext in ["jpg", "jpeg", "png", "webp"]:
                media_list.append(InputMediaPhoto(media=path))
            else:
                media_list.append(InputMediaVideo(media=path, supports_streaming=True))

        await client.send_media_group(chat_id=user_id, media=media_list)
        cap, _ = random.choice(CAPTIONS_SET)
        await original_message.reply_text(f"📝 **CAPTION:**\n`{cap}`")
        await safe_delete(status)
    except Exception as e:
        await safe_edit(status, f"❌ Error: {str(e)[:250]}")
    finally:
        for p in processed:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass

def fetch_insta(url, folder):
    opts = {
        "outtmpl": os.path.join(folder, "%(id)s_%(autonumber)02d.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "extract_flat": False,
        "format": "best",
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.instagram.com/",
        }
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if not info:
            return ""
        return (info.get("description") or info.get("title") or "").strip()

@app.on_message(filters.text)
async def handle_text(client, message):
    user_id = message.from_user.id
    text = message.text.strip() if message.text else ""

    # Skip commands
    if text.startswith("/start") or text.startswith("/menu"):
        return

    if text in ["📸 Image Stealth Wash", "🎥 Video Stealth Wash", "🔕 Mute & Wash Video",
                "📺 YouTube Stealth Wash", "🔗 Insta Link Stealth Wash",
                "✅ Yes, Add Watermark", "❌ No Watermark"]:
        return

    if "instagram.com" in text or "instagr.am" in text:
        user_modes[user_id] = "🔗 Insta Link Stealth Wash"
        user_watermarks.setdefault(user_id, True)
        apply_wm = user_watermarks[user_id]

        urls = re.findall(r"https?://[^\s]+", text)
        url = urls[0] if urls else text

        status = await message.reply_text("📥 Fetching Instagram media...")
        task_dir = os.path.join(DOWNLOAD_DIR, f"insta_{user_id}_{random.randint(1000,9999)}")
        os.makedirs(task_dir, exist_ok=True)
        processed = []

        try:
            caption = await asyncio.to_thread(fetch_insta, url, task_dir)
            files = sorted([
                os.path.join(task_dir, f) for f in os.listdir(task_dir)
                if os.path.isfile(os.path.join(task_dir, f)) and not f.endswith((".json", ".info.json"))
            ])

            if not files:
                await safe_edit(status, "❌ Media extract nahi hua. Post private ho sakti hai.")
                return

            await safe_edit(status, f"🔄 Processing {len(files)} file(s)...")

            media_list = []
            for f in files:
                out = await process_single_file(client, f, user_id, "🔗 Insta Link Stealth Wash", apply_wm)
                processed.append(out)
                ext = out.rsplit(".", 1)[-1].lower()
                if ext in ["jpg", "jpeg", "png", "webp"]:
                    media_list.append(InputMediaPhoto(media=out))
                else:
                    media_list.append(InputMediaVideo(media=out, supports_streaming=True))

            if len(media_list) == 1:
                item = media_list[0]
                if isinstance(item, InputMediaPhoto):
                    await message.reply_photo(photo=item.media)
                else:
                    await message.reply_video(video=item.media, supports_streaming=True)
            else:
                await client.send_media_group(chat_id=user_id, media=media_list)

            await safe_delete(status)

            final_cap = f"{caption}\n\n{HASHTAGS}" if caption else HASHTAGS
            await message.reply_text(f"📝 **CAPTION:**\n`{final_cap}`")

        except Exception as e:
            await safe_edit(status, f"❌ Error: {str(e)[:300]}")
        finally:
            for f in os.listdir(task_dir) if os.path.exists(task_dir) else []:
                try:
                    os.remove(os.path.join(task_dir, f))
                except:
                    pass
            try:
                os.rmdir(task_dir)
            except:
                pass
            for p in processed:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except:
                        pass

@app.on_message(filters.photo | filters.video | filters.document)
async def handle_media(client, message):
    user_id = message.from_user.id

    if user_id not in user_modes:
        user_modes[user_id] = "📸 Image Stealth Wash" if message.photo else "🎥 Video Stealth Wash"
    if user_id not in user_watermarks:
        user_watermarks[user_id] = True

    mode = user_modes[user_id]
    apply_wm = user_watermarks[user_id]

    if message.media_group_id:
        mg_id = message.media_group_id
        if mg_id not in media_group_cache:
            media_group_cache[mg_id] = []
            asyncio.create_task(process_album_task(client, message, mg_id, user_id, mode, apply_wm))
        media_group_cache[mg_id].append(message)
        return

    status = await message.reply_text("🔄 Processing with full stealth wash...")

    try:
        path = await process_single_file(client, message, user_id, mode, apply_wm)

        if path.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            await message.reply_photo(photo=path)
        else:
            await message.reply_video(video=path, supports_streaming=True)

        await safe_delete(status)

        cap, _ = random.choice(CAPTIONS_SET)
        await message.reply_text(f"📝 **CAPTION:**\n`{cap}`")

        if os.path.exists(path):
            os.remove(path)

    except Exception as e:
        await safe_edit(status, f"❌ Error: {str(e)[:280]}")

if __name__ == "__main__":
    print("🚀 Ghost Operator V6.2 FINAL started")
    print(f"Font: {'READY' if os.path.exists(FONT_FILE) else 'MISSING'}")
    app.run()