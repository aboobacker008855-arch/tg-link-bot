import asyncio
import os
import secrets
import sqlite3
from pathlib import Path
from urllib.parse import quote

import aiofiles
import requests
import google.generativeai as genai
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import uvicorn

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/")
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "./storage"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}

# GEMINI API SETUP
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing in .env")
if not PUBLIC_BASE_URL:
    raise RuntimeError("PUBLIC_BASE_URL is missing in .env")

STORAGE_DIR.mkdir(parents=True, exist_ok=True)
DB = sqlite3.connect("bot.db", check_same_thread=False)
DB.execute("""CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    original_name TEXT NOT NULL,
    stored_name TEXT NOT NULL UNIQUE,
    size INTEGER NOT NULL
)""")
DB.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)""")
DB.commit()

app = FastAPI(title="Telegram Public Link Generator")

dp = Dispatcher()

def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Help", callback_data="help"),
            InlineKeyboardButton(text="About", callback_data="about"),
            InlineKeyboardButton(text="Close", callback_data="close"),
        ],
        [InlineKeyboardButton(text="📢 Bot Channel", url=CHANNEL_URL)]
    ])

def help_text():
    return (
        "📚 <b>Help & Commands</b>\n\n"
        "<b>File Features:</b>\n"
        "• Send file/video -> Direct Stream/Download Link\n"
        "• /myfiles — Your recent links\n\n"
        "<b>AI Features:</b>\n"
        "• /ai [question] — Ask anything to Gemini AI\n"
        "• /generate [prompt] — Generate HD Images\n\n"
        f"⚠️ Download limit: {MAX_FILE_SIZE_MB} MB."
    )

def about_text():
    return (
        "ℹ️ <b>About</b>\n\n"
        "All-in-One Telegram Bot: File Streaming, Direct Links & AI Assistant!"
    )

@dp.message(CommandStart())
async def start(message: Message):
    DB.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (message.from_user.id,))
    DB.commit()
    name = message.from_user.first_name or "there"
    await message.answer(
        f"👋 Hey, <b>{name}</b>!\n\n"
        "Welcome to All-in-One Public Link Generator & AI Bot!\n\n"
        "Send me any file to get a link, or use `/ai [question]` to chat with AI!\n\n"
        "Click on Help for more info.",
        reply_markup=menu()
    )

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(help_text(), reply_markup=menu())

@dp.message(Command("about"))
async def about_cmd(message: Message):
    await message.answer(about_text(), reply_markup=menu())

# 🤖 1. AI CHAT FEATURE (/ai command)
@dp.message(Command("ai"))
async def ai_chat(message: Message):
    if not GEMINI_API_KEY:
        await message.answer("❌ Gemini API Key is not set in Render environment variables!")
        return

    text = message.text.split(" ", 1)
    if len(text) < 2:
        await message.answer("💡 Usage: `/ai What is Python?`", parse_mode="Markdown")
        return

    query = text[1]
    msg = await message.answer("🤖 Thinking...")
    try:
        response = ai_model.generate_content(query)
        await msg.edit_text(response.text)
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)}")

# 🎨 2. AI IMAGE GENERATOR FEATURE (/generate command)
@dp.message(Command("generate"))
async def generate_image(message: Message):
    text = message.text.split(" ", 1)
    if len(text) < 2:
        await message.answer("💡 Usage: `/generate a futuristic anime warrior`", parse_mode="Markdown")
        return

    prompt = text[1]
    msg = await message.answer("🎨 Generating image, please wait...")
    
    # Pollinations AI API
    image_url = f"https://image.pollinations.ai/prompt/{quote(prompt)}?width=1024&height=1024&nologo=true"
    
    try:
        await message.answer_photo(photo=image_url, caption=f"✨ <b>Prompt:</b> {prompt}")
        await msg.delete()
    except Exception as e:
        await msg.edit_text("❌ Failed to generate image. Try another prompt.")

@dp.message(Command("myfiles"))
async def myfiles(message: Message):
    rows = DB.execute(
        "SELECT original_name, stored_name, size FROM files WHERE user_id=? ORDER BY id DESC LIMIT 20",
        (message.from_user.id,)
    ).fetchall()
    if not rows:
        await message.answer("You don't have any generated links yet.")
        return
    lines = ["📂 <b>Your recent files</b>\n"]
    for name, stored, size in rows:
        url = f"{PUBLIC_BASE_URL}/d/{quote(stored)}"
        lines.append(f"• {name} — {size/1024/1024:.2f} MB\n{url}")
    await message.answer("\n".join(lines), disable_web_page_preview=True)

@dp.callback_query(F.data == "help")
async def help_cb(c: CallbackQuery):
    await c.message.edit_text(help_text(), reply_markup=menu())
    await c.answer()

@dp.callback_query(F.data == "about")
async def about_cb(c: CallbackQuery):
    await c.message.edit_text(about_text(), reply_markup=menu())
    await c.answer()

@dp.callback_query(F.data == "close")
async def close_cb(c: CallbackQuery):
    await c.message.delete()
    await c.answer()

async def download_to_disk(bot: Bot, file_id: str, stored_name: str):
    tg_file = await bot.get_file(file_id)
    destination = STORAGE_DIR / stored_name
    await bot.download_file(tg_file.file_path, destination=destination)
    return destination

async def process_file(message: Message, file_id: str, original_name: str, size: int):
    if size > MAX_FILE_SIZE_MB * 1024 * 1024:
        await message.answer(
            f"❌ File is too large. Limit: {MAX_FILE_SIZE_MB} MB."
        )
        return

    stored = secrets.token_urlsafe(18) + Path(original_name).suffix.lower()
    await message.answer("⏳ Upload received. Generating your public link...")
    try:
        path = await download_to_disk(message.bot, file_id, stored)
    except Exception as e:
        await message.answer("❌ Could not download the file from Telegram.")
        print("download error:", repr(e))
        return

    DB.execute(
        "INSERT INTO files(user_id, original_name, stored_name, size) VALUES (?,?,?,?)",
        (message.from_user.id, original_name, stored, size)
    )
    DB.commit()
    url = f"{PUBLIC_BASE_URL}/d/{quote(stored)}"
    await message.answer(
        "✅ <b>Link generated!</b>\n\n"
        f"📄 <b>Name:</b> {original_name}\n"
        f"📦 <b>Size:</b> {size/1024/1024:.2f} MB\n\n"
        f"🔗 <b>Download:</b>\n{url}",
        disable_web_page_preview=True
    )

@dp.message(F.document)
async def document_handler(message: Message):
    d = message.document
    await process_file(message, d.file_id, d.file_name or "file", d.file_size or 0)

@dp.message(F.video)
async def video_handler(message: Message):
    v = message.video
    await process_file(message, v.file_id, f"video_{v.file_unique_id}.mp4", v.file_size or 0)

@dp.message(F.audio)
async def audio_handler(message: Message):
    a = message.audio
    name = a.file_name or f"audio_{a.file_unique_id}"
    await process_file(message, a.file_id, name, a.file_size or 0)

@dp.message(F.photo)
async def photo_handler(message: Message):
    p = message.photo[-1]
    await process_file(message, p.file_id, f"photo_{p.file_unique_id}.jpg", p.file_size or 0)

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/d/{stored_name}")
async def download(stored_name: str):
    safe = Path(stored_name).name
    path = STORAGE_DIR / safe
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=safe)

async def main():
    bot = Bot(BOT_TOKEN)
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await asyncio.gather(dp.start_polling(bot), server.serve())

if __name__ == "__main__":
    asyncio.run(main())

