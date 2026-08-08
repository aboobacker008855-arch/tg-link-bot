import os
import asyncio

try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

API_ID = int(os.environ.get("API_ID", "30758714"))
API_HASH = os.environ.get("API_HASH", "32214e6bfbb651a4f64a707c775eca45")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8588152483:AAGDpwdvhMGPwuIImeeoffhSU6fcA9maw3c")
PORT = int(os.environ.get("PORT", "8080"))

DOMAIN = os.environ.get("RENDER_EXTERNAL_URL", "https://tg-link-bot-882m.onrender.com")

app = Client("4gb_stream_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
routes = web.RouteTableDef()

@routes.get("/")
async def root_handler(request):
    return web.Response(text="Bot is Running!", status=200)

@routes.get("/download/{message_id}")
@routes.get("/watch/{message_id}")
async def stream_handler(request):
    try:
        message_id = int(request.match_info['message_id'])
        chat_id = request.app.get('user_chat_id')
        
        if not chat_id:
            return web.Response(text="Chat ID missing. Resend file to Telegram bot.", status=400)

        msg = await app.get_messages(chat_id=chat_id, message_ids=message_id)
        media = msg.document or msg.video or msg.audio or msg.animation
        
        if not media:
            return web.Response(text="File not found.", status=404)

        file_name = getattr(media, "file_name", "Telegram_File.mkv")
        file_size = media.file_size

        headers = {
            'Content-Type': 'application/octet-stream',
            'Content-Disposition': f'attachment; filename="{file_name}"',
            'Content-Length': str(file_size),
            'Accept-Ranges': 'bytes',
            'Connection': 'keep-alive'
        }

        response = web.StreamResponse(status=200, headers=headers)
        await response.prepare(request)

        async for chunk in app.stream_media(msg):
            await response.write(chunk)

        return response

    except Exception as e:
        return web.Response(text=f"Streaming Error: {str(e)}", status=500)

@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply_text("👋 **Public Link Generator Bot is Active!**\n\nഎനിക്ക് ഏതെങ്കിലും ഫയലോ വീഡിയോയോ അയച്ചു തരൂ, ഞാൻ ഡൗൺലോഡ്/സ്ട്രീമിംഗ് ലിങ്ക് ഉണ്ടാക്കി തരാം!")

@app.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.animation))
async def handle_file(client, message):
    server['user_chat_id'] = message.chat.id
    status_msg = await message.reply_text("⏳ *Generating High Speed Link...*")
    
    media = message.document or message.video or message.audio or message.animation
    file_name = getattr(media, "file_name", "Telegram_File.mkv")
    
    size_mb = media.file_size / (1024 * 1024)
    file_size = f"{round(size_mb / 1024, 2)} GiB" if size_mb >= 1024 else f"{round(size_mb, 2)} MiB"
    
    stream_url = f"{DOMAIN}/watch/{message.id}"
    download_url = f"{DOMAIN}/download/{message.id}"
    
    text = (
        f"__**Your Fast Link Generated!**__\n\n"
        f"📁 **File Name:**\n`{file_name}`\n\n"
        f"📦 **File Size:** `{file_size}`\n\n"
        f"For Updates related to bot -> @myran13\n"
        f"For any query/discussion -> @myran13\n\n"
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

async def main():
    await app.start()
    print("Pyrogram Started!")
    
    server = web.Application()
    server['user_chat_id'] = None
    server.add_routes(routes)
    
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print("Web Server Started!")
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
