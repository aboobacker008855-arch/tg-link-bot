# Telegram Public Link Generator Bot

A starter bot inspired by the screenshot:
- `/start` welcome screen
- Help / About / Close buttons
- File -> public HTTP download link
- Basic file information
- `/myfiles` list
- `/stats` admin stats
- `/broadcast` admin broadcast
- configurable channel button
- disclaimer / adult-content warning
- FastAPI public file server

## Important
This template stores downloaded files on the server. It is intended for files you own or have permission to distribute.

### Setup
1. Create a bot with @BotFather and put the token in `.env`.
2. Set `PUBLIC_BASE_URL` to your server's HTTPS URL.
3. Install dependencies:
   `pip install -r requirements.txt`
4. Run:
   `python bot.py`

### File size
Telegram's standard Bot API has download-size limitations. For large files, use a self-hosted/local Telegram Bot API server or adapt the downloader to a suitable storage/Telegram client architecture.

### Environment variables
See `.env.example`.
