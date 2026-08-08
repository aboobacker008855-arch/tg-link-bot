import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_ID = int(os.environ.get("API_ID", "30758714"))
API_HASH = os.environ.get("API_HASH", "32214e6bfbb651a4f64a707c775eca45")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8588152483:AAGDpwdvhMGPwuIImeeoffhSU6fcA9maw3c")

DOMAIN = os.environ.get("RENDER_EXTERNAL_URL", "https://tg-link-bot-882m.onrender.com")

app = Client("4gb_stream_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply_text("👋 **Public Link Generator Bot is Active!**")

@app.on_message(filters.document | filters.video | filters.audio)
async def handle_file(client, message):
    status_msg = await message.reply_text("⏳ *Generating High Speed Link...*")
    
    media = message.document or message.video or message.audio
    file_name = getattr(media, "file_name", "Telegram_File")
    
    size_mb = media.file_size / (1024 * 1024)
    file_size = f"{round(size_mb / 1024, 2)} GiB" if size_mb >= 1024 else f"{round(size_mb, 2)} MiB"
    
    stream_url = f"{DOMAIN}/watch/{message.id}"
    download_url = f"{DOMAIN}/download/{message.id}"
    
    text = (
        f"__**Your Fast Link Generated!**__\n\n"
        f"📁 **File Name:**\n`{file_name}`\n\n"
        f"📦 **File Size:** `{file_size}`\n\n"
        f"For Updates related to bot -> @JANGO\n"
        f"For any query/discussion -> @JANGO\n\n"
        f"Link Generated Using **Public Link Generator Bot**"
    )
    
    reply_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🖥️ Watch", url=stream_url),
                InlineKeyboardButton("Download ⚡", url=download_url)
            ]
        ]
    )
    
    await status_msg.edit_text(text, reply_markup=reply_markup, disable_web_page_preview=True)

if __name__ == "__main__":
    print("Bot is starting...")
    app.run()
