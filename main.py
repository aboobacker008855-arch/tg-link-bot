import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
import os
import sqlite3
from pathlib import Path
from urllib.parse import quote
import secrets
from aiohttp import web

TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8080")
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "500"))
PORT = int(os.getenv("PORT", "10000"))

STORAGE_DIR = Path("storage")
STORAGE_DIR.mkdir(exist_ok=True)

db_path = Path("bot_database.db")
db_conn = sqlite3.connect(db_path, check_same_thread=False)
DB = db_conn.cursor()
DB.execute("""
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    original_name TEXT,
    stored_name TEXT,
    size INTEGER
)
""")
db_conn.commit()

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

import google.generativeai as genai
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    ai_model = genai.GenerativeModel("gemini-pro")

def start_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Help 💡", callback_data="help"),
                InlineKeyboardButton(text="About ℹ️", callback_data="about"),
                InlineKeyboardButton(text="Close ❌", callback_data="close")
            ],
            [
                InlineKeyboardButton(text="📢 Bot Channel", url="https://t.me/your_channel_link")
            ]
        ]
    )

def help_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔙 Back", callback_data="back_to_home"),
                InlineKeyboardButton(text="Close ❌", callback_data="close")
            ],
            [
                InlineKeyboardButton(text="Comments 📝", callback_data="bot_comments")
            ]
        ]
    )

def help_text():
    return (
        "📖 <b>Bot Features & Help Menu</b>\n\n"
        "📁 <b>File Streaming & Downloads:</b>\n"
        "• എനിക്ക് ഏതെങ്കിലും ഫയലോ വീഡിയോയോ അയച്ചു തരുമ്പോൾ, ഞാൻ Fast Direct Download / Streaming ലിങ്ക് ഉണ്ടാക്കി തരാം!\n\n"
        "🤖 <b>Free AI Chat:</b>\n"
        "• /ai [ചോദ്യം] - AI-യോട് എന്തും ചോദിക്കാം.\n\n"
        "🎨 <b>AI Image Generation:</b>\n"
        "• /generate [Prompt] - AI ഉപയോഗിച്ച് HD ചിത്രങ്ങൾ ഉണ്ടാക്കാം."
    )

def about_text():
    return (
        "ℹ️ <b>About This Bot</b>\n\n"
        "I'm Telegram Files Streaming Bot as well as a Direct Links Generator."
    )

@dp.message(Command("start"))
async def start_cmd(message: Message):
    welcome_text = (
        f"👋 Hey, <b>{message.from_user.first_name}</b>\n\n"
        "<i>I'm Telegram Files Streaming Bot as well as a Direct Links Generator</i>\n\n"
        "Click on Help to get more information\n\n"
        "WARNING ⚠️\n"
        "🔞 Adult content leads to a permanent ban."
    )
    await message.answer(welcome_text, reply_markup=start_menu())

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(help_text(), reply_markup=help_menu())

@dp.message(Command("about"))
async def about_cmd(message: Message):
    await message.answer(about_text(), reply_markup=start_menu())

@dp.message(Command("ai"))
async def ai_chat(message: Message):
    if not GEMINI_API_KEY:
        await message.answer("❌ Gemini API Key is not set in Render environment variables.")
        return
    text = message.text.split(" ", 1)
    if len(text) < 2:
        await message.answer("💡 Usage: <code>/ai What is Python?</code>")
        return
    query = text[1]
    msg = await message.answer("🤖 Thinking...")
    try:
        response = ai_model.generate_content(query)
        await msg.edit_text(response.text)
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)}")

@dp.message(Command("generate"))
async def generate_image(message: Message):
    text = message.text.split(" ", 1)
    if len(text) < 2:
        await message.answer("💡 Usage: <code>/generate a futuristic anime city</code>")
        return
    prompt = text[1]
    msg = await message.answer("🎨 Generating image, please wait...")
    image_url = f"https://image.pollinations.ai/prompt/{quote(prompt)}"
    try:
        await message.answer_photo(photo=image_url, caption=f"✨ Generated for: {prompt}")
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"❌ Failed to generate image. Try another prompt.")

@dp.message(Command("myfiles"))
async def myfiles(message: Message):
    rows = DB.execute(
        "SELECT original_name, stored_name, size FROM files WHERE user_id = ?",
        (message.from_user.id,)
    ).fetchall()
    if not rows:
        await message.answer("You don't have any generated links yet.")
        return
    lines = ["📁 <b>Your recent files</b>\n"]
    for name, stored, size in rows:
        url = f"{PUBLIC_BASE_URL}/d/{quote(stored)}"
        lines.append(f"• {name} — {size/1024/1024:.2f} MB\n{url}")
    await message.answer("\n".join(lines), disable_web_page_preview=True)

@dp.callback_query(F.data == "help")
async def help_cb(c: CallbackQuery):
    await c.message.edit_text(help_text(), reply_markup=help_menu())
    await c.answer()

@dp.callback_query(F.data == "bot_comments")
async def comments_callback(c: CallbackQuery):
    comment_text = (
        "💭 <b>Bot Features & Shortcuts</b>\n\n"
        "താഴെയുള്ള ബട്ടണുകളിൽ ക്ലിക്ക് ചെയ്താൽ, നേരെ മെസ്സേജ് ടൈപ്പ് ചെയ്യുന്ന സ്ഥലത്ത് കമാൻഡ് ഓട്ടോമാറ്റിക്കായി വരും! 👇"
    )
    features_markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🤖 Free AI Chat", switch_inline_query_current_chat="/ai ")
            ],
            [
                InlineKeyboardButton(text="🎨 AI Image Generation", switch_inline_query_current_chat="/generate ")
            ],
            [
                InlineKeyboardButton(text="🔙 Back to Help", callback_data="help")
            ]
        ]
    )
    await c.message.edit_text(text=comment_text, reply_markup=features_markup)
    await c.answer()

@dp.callback_query(F.data == "back_to_home")
async def back_to_home_cb(c: CallbackQuery):
    welcome_text = (
        f"👋 Hey, <b>{c.from_user.first_name}</b>\n\n"
        "<i>I'm Telegram Files Streaming Bot as well as a Direct Links Generator</i>\n\n"
        "Click on Help to get more information\n\n"
        "WARNING ⚠️\n"
        "🔞 Adult content leads to a permanent ban."
    )
    await c.message.edit_text(welcome_text, reply_markup=start_menu())
    await c.answer()

@dp.callback_query(F.data == "about")
async def about_cb(c: CallbackQuery):
    await c.message.edit_text(about_text(), reply_markup=start_menu())
    await c.answer()

@dp.callback_query(F.data == "close")
async def close_cb(c: CallbackQuery):
    await c.message.delete()
    await c.answer()

async def download_to_disk(bot: Bot, file_id: str, stored_name: str) -> Path:
    tg_file = await bot.get_file(file_id)
    destination = STORAGE_DIR / stored_name
    await bot.download_file(tg_file.file_path, destination=destination)
    return destination

@dp.message(F.document | F.video | F.audio)
async def process_file(message: Message):
    file_obj = message.document or message.video or message.audio
    if file_obj.file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        await message.answer(f"❌ File is too large. Limit: {MAX_FILE_SIZE_MB} MB.")
        return
    stored = secrets.token_urlsafe(18) + Path(file_obj.file_name or "file").suffix
    await message.answer("⏳ Upload received. Generating your public link...")
    try:
        path = await download_to_disk(message.bot, file_obj.file_id, stored)
    except Exception as e:
        await message.answer("❌ Could not download the file from Telegram.")
        return
    DB.execute(
        "INSERT INTO files(user_id, original_name, stored_name, size) VALUES (?, ?, ?, ?)",
        (message.from_user.id, file_obj.file_name or "file", stored, file_obj.file_size)
    )
    db_conn.commit()
    url = f"{PUBLIC_BASE_URL}/d/{quote(stored)}"
    await message.answer(
        f"✅ <b>Link generated!</b>\n\n"
        f"📄 <b>Name:</b> {file_obj.file_name or 'file'}\n"
        f"🔗 <b>Direct Link:</b> {url}",
        disable_web_page_preview=True
    )

# Web server to satisfy Render port binding requirement
async def handle(request):
    return web.Response(text="Bot is running!")

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

async def main():
    await web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
