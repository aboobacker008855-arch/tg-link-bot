import os
import asyncio
from urllib.parse import quote
import aiohttp

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

API_ID = int(os.environ.get("API_ID", "30758714"))
API_HASH = os.environ.get("API_HASH", "32214e6bfbb651a4f64a707c775eca45")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8926177079:AAH5meh2Kwmk-pb7Mc16lWZ-HfDL1SUEYUk")
PORT = int(os.environ.get("PORT", "8080"))

SHORTENER_API = os.environ.get("SHORTENER_API", "")
SHORTENER_URL = os.environ.get("SHORTENER_URL", "")

RAW_DOMAIN = os.environ.get("RENDER_EXTERNAL_URL", "https://tg-link-bot-882m.onrender.com")
if not RAW_DOMAIN.startswith("http"):
    RAW_DOMAIN = f"https://{RAW_DOMAIN}"
DOMAIN = RAW_DOMAIN.rstrip('/')

app = Client("4gb_stream_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
routes = web.RouteTableDef()
server = web.Application()

async def get_short_link(long_url):
    if not SHORTENER_API or not SHORTENER_URL:
        return long_url
    try:
        api_req = f"https://{SHORTENER_URL}/api?api={SHORTENER_API}&url={quote(long_url)}"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_req) as resp:
                data = await resp.json()
                return data.get("shortenedUrl", long_url)
    except Exception:
        return long_url

@routes.get("/")
async def root_handler(request):
    return web.Response(text="Bot is Running!", status=200)

@routes.get("/download/{chat_id}/{message_id}")
@routes.get("/watch/{chat_id}/{message_id}")
async def stream_handler(request):
    try:
        chat_id = int(request.match_info['chat_id'])
        message_id = int(request.match_info['message_id'])

        msg = await app.get_messages(chat_id=chat_id, message_ids=message_id)
        media = msg.document or msg.video or msg.audio or msg.animation or msg.voice
        
        if not media:
            return web.Response(text="File not found.", status=404)

        file_name = getattr(media, "file_name", "Telegram_Video.mp4")
        file_size = getattr(media, "file_size", 0)

        is_download = request.path.startswith("/download")
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
    text = (
        "👋 **Public Link Generator & Free AI Bot is Active!**\n\n"
        "📁 **File Features:**\n"
        "എനിക്ക് ഏതെങ്കിലും ഫയലോ വീഡിയോയോ അയച്ചു തരൂ, ഞാൻ Fast Stream / Download ലിങ്ക് ഉണ്ടാക്കി തരാം!\n\n"
        "🤖 **AI Features:**\n"
        "• `/ai [ചോദ്യം]` - AI-യോട് എന്തും ചോദിക്കാം (Free Fast AI)\n"
        "• `/generate [image prompt]` - AI ചിത്രങ്ങൾ ഉണ്ടാക്കാം"
    )
    await message.reply_text(text)

@app.on_message(filters.command("ai") & filters.private)
async def ai_handler(client, message):
    if len(message.command) < 2:
        await message.reply_text("💡 **ഉപയോഗിക്കേണ്ട വിധം:** `/ai What is Python?`")
        return

    query = message.text.split(maxsplit=1)[1]
    status_msg = await message.reply_text("🤖 *Thinking...*")
    
    url = f"https://text.pollinations.ai/{quote(query)}?model=openai"
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    reply = await resp.text()
                    await status_msg.edit_text(reply)
                else:
                    await status_msg.edit_text("❌ AI മറുപടി തരാൻ അല്പം വൈകുന്നു. വീണ്ടും ഒരുതവണ കൂടി ശ്രമിക്കൂ!")
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")

@app.on_message(filters.command("generate") & filters.private)
async def image_handler(client, message):
    if len(message.command) < 2:
        await message.reply_text("💡 **ഉപയോഗിക്കേണ്ട വിധം:** `/generate a futuristic anime hero`")
        return

    prompt = message.text.split(maxsplit=1)[1]
    status_msg = await message.reply_text("🎨 *Generating HD Image...*")

    image_url = f"https://image.pollinations.ai/prompt/{quote(prompt)}?width=1024&height=1024&nologo=true"

    try:
        await message.reply_photo(photo=image_url, caption=f"✨ **Prompt:** `{prompt}`")
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ Image generation failed: {str(e)}")

@app.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.animation | filters.voice))
async def handle_file(client, message):
    media = message.document or message.video or message.audio or message.animation or message.voice
    
    status_msg = await message.reply_text("⏳ *Generating High Speed Link...*")
    
    file_name = getattr(media, "file_name", "Telegram_Media.mp4")
    file_size_bytes = getattr(media, "file_size", 0)
    
    size_mb = file_size_bytes / (1024 * 1024)
    file_size = f"{round(size_mb / 1024, 2)} GiB" if size_mb >= 1024 else f"{round(size_mb, 2)} MiB"
    
    chat_id = message.chat.id
    msg_id = message.id
    
    raw_stream_url = f"{DOMAIN}/watch/{chat_id}/{msg_id}"
    raw_download_url = f"{DOMAIN}/download/{chat_id}/{msg_id}"

    stream_url = await get_short_link(raw_stream_url)
    download_url = await get_short_link(raw_download_url)
    
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

@app.on_message(filters.private & ~filters.command(["start", "ai", "generate"]))
async def unknown_msg(client, message):
    await message.reply_text("❌ ദയവായി ഏതെങ്കിലും **ഫയൽ/വീഡിയോ** അയക്കുക, അല്ലെങ്കിൽ `/ai`, `/generate` ഉപയോഗിക്കുക!")

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
