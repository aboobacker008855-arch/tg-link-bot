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
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8926177079:AAH5meh2Kwmk-pb7Mc16lWZ-HfDL1SUEYUk")
PORT = int(os.environ.get("PORT", "8080"))

RAW_DOMAIN = os.environ.get("RENDER_EXTERNAL_URL", "https://tg-link-bot-882m.onrender.com")
if not RAW_DOMAIN.startswith("http"):
    RAW_DOMAIN = f"https://{RAW_DOMAIN}"
DOMAIN = RAW_DOMAIN.rstrip('/')

app = Client("4gb_stream_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
routes = web.RouteTableDef()
server = web.Application()

@routes.get("/")
async def root_handler(request):
    return web.Response(text="Bot is Running!", status=200)

@routes.get("/watch/{chat_id}/{message_id}")
async def watch_handler(request):
    return await handle_stream(request, is_download=False)

@routes.get("/download/{chat_id}/{message_id}")
async def download_handler(request):
    return await handle_stream(request, is_download=True)

async def handle_stream(request, is_download=False):
    try:
        chat_id = int(request.match_info['chat_id'])
        message_id = int(request.match_info['message_id'])

        msg = await app.get_messages(chat_id=chat_id, message_ids=message_id)
        media = msg.document or msg.video or msg.audio or msg.animation or msg.voice
        
        if not media:
            return web.Response(text="File not found.", status=404)

        file_name = getattr(media, "file_name", "Telegram_Video.mp4")
        file_size = getattr(media, "file_size", 0)

        # Download ആണെങ്കിൽ 'attachment', Stream ആണെങ്കിൽ 'inline'
        disposition = "attachment" if is_download else "inline"
        content_type = "application/octet-stream" if is_download else "video/mp4"

        headers = {
            'Content-Type': content_type,
            'Content-Disposition': f'{disposition}; filename="{file_name}"',
            'Content-Length': str(file_size),
            'Accept-Ranges': 'bytes',
            'Connection': 'keep-alive'
        }

        response = web.StreamResponse(status=200, headers=headers)
        await response.prepare(request)

        async for chunk in app.stream_media(msg, limit=0):
            await response.write(chunk)

        return response

    except Exception as e:
        return web.Response(text=f"Streaming Error: {str(e)}", status=500)

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    await message.reply_text("👋 **Public Link Generator Bot is Active!**\n\nഎനിക്ക് ഏതെങ്കിലും ഫയലോ വീഡിയോയോ അയച്ചു തരൂ, ഞാൻ ഡൗൺലോഡ്/സ്ട്രീമിംഗ് ലിങ്ക് ഉണ്ടാക്കി തരാം!")

@app.on_message(filters.private & ~filters.command(["start"]))
async def handle_file(client, message):
    media = message.document or message.video or message.audio or message.animation or message.voice
    
    if not media:
        await message.reply_text("❌ ദയവായി ഏതെങ്കിലും **ഫയൽ/വീഡിയോ** മാത്രം അയക്കുക!")
        return
    
    status_msg = await message.reply_text("⏳ *Generating High Speed Link...*")
    
    file_name = getattr(media, "file_name", "Telegram_Media.mp4")
    file_size_bytes = getattr(media, "file_size", 0)
    
    size_mb = file_size_bytes / (1024 * 1024)
    file_size = f"{round(size_mb / 1024, 2)} GiB" if size_mb >= 1024 else f"{round(size_mb, 2)} MiB"
    
    chat_id = message.chat.id
    msg_id = message.id
    
    stream_url = f"{DOMAIN}/watch/{chat_id}/{msg_id}"
    download_url = f"{DOMAIN}/download/{chat_id}/{msg_id}"
    
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
                InlineKeyboardButton("🖥️ Watch Direct", url=stream_url),
                InlineKeyboardButton("Download ⚡", url=download_url)
            ]
        ]
    )
    
    await status_msg.edit_text(text, reply_markup=reply_markup, disable_web_page_preview=True)

async def main():
    await app.start()
    print("Pyrogram Started!")
    
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
