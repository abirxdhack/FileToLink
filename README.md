# âœ¨ Smart Web Stream API

![Smart Web Stream API](https://i.ibb.co/Hh4kF2b/icon.png)

**Smart Web Stream API** is a high-performance, production-ready API for streaming and downloading Telegram files with enterprise-grade features. Built with **FastAPI** and **Telethon**, it offers ultra-low-latency streaming, intelligent concurrent request handling, aggressive prefetching, and seamless multi-platform deployment. Crafted by **Abir Arafat Chawdhury ðŸ‡§ðŸ‡©**.

**Repository**: [github.com/abirxdhack/FileToLink](https://github.com/abirxdhack/FileToLink)

---

## ðŸš€ Features

- **Telegram Integration** âœ¨  
  Seamlessly access Telegram files via Telethon with MemorySession for optimal performance
  
- **High-Speed Streaming** ðŸ–¥ï¸  
  Stream media with minimal latency using aggressive prefetching and parallel chunk processing
  
- **Intelligent Concurrency** âš¡  
  Handle up to 100 concurrent requests with semaphore-based load balancing
  
- **Secure Downloads** ðŸ”’  
  Code-based authentication system for protected file access
  
- **Range-Based Downloads** ðŸ“  
  Full HTTP Range header support for resumable downloads and partial content delivery
  
- **Multi-Platform Deployment** ðŸŒ  
  Auto-detection for Heroku, Render, Railway, Fly.io, Vercel, and custom domains
  
- **Advanced Chunk Management** ðŸ”„  
  4MB chunk size with intelligent buffering and parallel prefetching (up to 10 chunks)
  
- **Production-Ready** ðŸ­  
  Built with uvloop, optimized uvicorn settings, and comprehensive error handling
  
- **Template Support** ðŸŽ¨  
  Jinja2-powered HTML player for in-browser streaming
  
- **Robust Error Handling** âš ï¸  
  Clear error responses for all scenarios (400, 401, 403, 404, 416, 500, 503)

---

## ðŸ› ï¸ Setup

### Prerequisites
- Python 3.8+
- `pip3`
- `screen` (for persistent sessions)
- Telegram API credentials & bot token
- Telegram channel for file storage and logging

### Installation Steps

1. **Clone Repository**  
   ```bash
   git clone https://github.com/abirxdhack/FileToLink.git
   cd FileToLink
   ```

2. **Install Dependencies**  
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Configure API**  
   Create `config.py` in the root directory:
   ```python
   API_ID = YOUR_API_ID
   API_HASH = "YOUR_API_HASH"
   BOT_TOKEN = "YOUR_BOT_TOKEN"
   LOG_CHANNEL_ID = YOUR_CHANNEL_ID
   ```
   
   **Getting Credentials:**
   - Get `API_ID` & `API_HASH` from [my.telegram.org](https://my.telegram.org)
   - Create a bot via [BotFather](https://t.me/BotFather) for `BOT_TOKEN`
   - Set `LOG_CHANNEL_ID` (e.g., `-1001234567890`) and ensure bot is admin

4. **Set Up Templates**  
   Create a `templates/` directory with `index.html` and `player.html` for the web interface

5. **Run API Locally**  
   ```bash
   screen -S FileToLink
   python3 api.py
   ```
   - Detach: `Ctrl+A`, then `Ctrl+D`
   - Reattach: `screen -r FileToLink`

6. **Environment Variables**  
   For custom configurations:
   ```bash
   export PORT=8000
   export CUSTOM_DOMAIN=yourdomain.com
   ```

---

## ðŸŒ Deployment

### Platform Auto-Detection

The API automatically detects your deployment platform and configures the base URL:

- **Heroku**: Set `HEROKU_APP_NAME`
- **Render**: Automatically uses `RENDER_EXTERNAL_URL`
- **Railway**: Uses `RAILWAY_PUBLIC_DOMAIN` or `RAILWAY_STATIC_URL`
- **Fly.io**: Set `FLY_APP_NAME`
- **Vercel**: Automatically uses `VERCEL_URL`
- **Custom Domain**: Set `CUSTOM_DOMAIN` for any platform

### Example: Vercel Deployment

```bash
npm i -g vercel
vercel --prod
```

Set environment variables in Vercel dashboard:
- `API_ID`
- `API_HASH`
- `BOT_TOKEN`
- `LOG_CHANNEL_ID`

---

## ðŸ“¡ API Endpoints

### **GET /**  
Returns the API homepage with status information.

- **Response**: HTML content
- **Example**:
  ```bash
  curl -X GET "https://your-domain.com/"
  ```

---

### **GET /stream/{file_id}**  
Streams a Telegram file with an embedded HTML player.

- **Parameters**:
  - `file_id` (int): Message ID in the log channel
  - `code` (str): Authentication code (query parameter)
  
- **Response**: HTML player with video/audio controls
- **Example**:
  ```bash
  curl -X GET "https://your-domain.com/stream/12345?code=abc123xyz"
  ```

---

### **GET /dl/{file_id}**  
Downloads a Telegram file with full range support.

- **Parameters**:
  - `file_id` (int): Message ID in the log channel
  - `code` (str): Authentication code (query parameter)
  - `Range` (header, optional): Byte range for partial downloads
  
- **Special Feature**: Add `=stream` to the code to redirect to the player
  ```
  /dl/12345?code=abc123xyz=stream
  ```

- **Response**: File stream with appropriate headers
- **Examples**:
  ```bash
  curl -X GET "https://your-domain.com/dl/12345?code=abc123xyz"
  
  curl -X GET "https://your-domain.com/dl/12345?code=abc123xyz" \
    -H "Range: bytes=0-1048575"
  
  curl -X GET "https://your-domain.com/dl/12345?code=abc123xyz=stream"
  ```

---

## ðŸš€ Cloudflare Workers Proxy

Use this Cloudflare Workers script as a proxy or superfast way to stream from your main API URL. This improves performance by caching static assets and forwarding requests with optimized headers.

### Cloudflare Workers Code

```javascript
const API_HOST = "filetolink-three.vercel.app";

async function handleRequest(event) {
    const url = new URL(event.request.url);
    const pathname = url.pathname;
    const search = url.search;
    const pathWithParams = pathname + search;

    if (pathname.startsWith("/static/")) {
        return retrieveStatic(event, pathWithParams);
    } else {
        return forwardRequest(event, pathWithParams);
    }
}

async function retrieveStatic(event, pathname) {
    let response = await caches.default.match(event.request);
    if (!response) {
        response = await fetch(`https://${API_HOST}${pathname}`);
        const headers = new Headers(response.headers);
        headers.set("Cache-Control", "public, max-age=86400");
        
        const cachedResponse = new Response(response.body, {
            status: response.status,
            statusText: response.statusText,
            headers: headers
        });
        
        event.waitUntil(caches.default.put(event.request, cachedResponse.clone()));
        return cachedResponse;
    }
    return response;
}

async function forwardRequest(event, pathWithSearch) {
    const originalRequest = event.request;
    const headers = new Headers(originalRequest.headers);
    
    headers.delete("cookie");
    headers.set("X-Forwarded-For", originalRequest.headers.get("CF-Connecting-IP") || "");
    headers.set("X-Forwarded-Proto", "https");
    headers.set("X-Forwarded-Host", new URL(originalRequest.url).host);
    
    const modifiedRequest = new Request(`https://${API_HOST}${pathWithSearch}`, {
        method: originalRequest.method,
        headers: headers,
        body: originalRequest.body,
        redirect: "follow"
    });
    
    try {
        const response = await fetch(modifiedRequest);
        const newHeaders = new Headers(response.headers);
        
        newHeaders.set("Access-Control-Allow-Origin", "*");
        newHeaders.set("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS");
        newHeaders.set("Access-Control-Allow-Headers", "Range, Content-Type");
        
        return new Response(response.body, {
            status: response.status,
            statusText: response.statusText,
            headers: newHeaders
        });
    } catch (error) {
        return new Response("Service temporarily unavailable", {
            status: 503,
            headers: {
                "Content-Type": "text/plain"
            }
        });
    }
}

addEventListener("fetch", (event) => {
    event.passThroughOnException();
    event.respondWith(handleRequest(event));
});
```

### How to Deploy

1. Go to [Cloudflare Workers](https://workers.cloudflare.com/)
2. Create a new Worker
3. Replace the worker code with the script above
4. Update `API_HOST` with your actual API domain
5. Deploy and use the Workers URL as your proxy

**Benefits:**
- Caches static assets for 24 hours
- Adds CORS headers automatically
- Forwards client IP and host information
- Provides failover with 503 responses
- Improves global latency with Cloudflare's edge network

---

## ðŸ¤– Telegram Bot Integration

Integrate the API into your Telegram bot to generate streaming and download links using the `/fdl` command.

### Bot Code Example

```python
import asyncio
import urllib.parse
from datetime import datetime
from mimetypes import guess_type
from aiogram import Bot
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode
from pyrogram.types import Message as SmartMessage
from pyrogram.enums import ChatMemberStatus
from bot import dp, SmartPyro
from bot.helpers.utils import new_task
from bot.helpers.botutils import send_message
from bot.helpers.commands import BotCommands
from bot.helpers.logger import LOGGER
from bot.helpers.notify import Smart_Notify
from bot.helpers.buttons import SmartButtons
from bot.helpers.defend import SmartDefender
from config import LOG_CHANNEL_ID, FILE_API_URL
import aiohttp

async def check_api_health():
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            base_url = FILE_API_URL.rstrip('/')
            async with session.get(f"{base_url}/") as response:
                return response.status == 200
    except:
        return False

async def get_telegram_file_id(message: Message):
    if message.document:
        return message.document.file_id
    elif message.video:
        return message.video.file_id
    elif message.audio:
        return message.audio.file_id
    elif message.photo:
        return message.photo[-1].file_id
    elif message.video_note:
        return message.video_note.file_id
    return None

async def get_file_properties(message: Message):
    file_name = None
    file_size = 0
    mime_type = None
    resolution = None
    
    if message.document:
        file_name = message.document.file_name
        file_size = message.document.file_size
        mime_type = message.document.mime_type
    elif message.video:
        file_name = getattr(message.video, 'file_name', None)
        file_size = message.video.file_size
        mime_type = message.video.mime_type
        resolution = f"{message.video.width}x{message.video.height}" if message.video.width and message.video.height else None
    elif message.audio:
        file_name = getattr(message.audio, 'file_name', None)
        file_size = message.audio.file_size
        mime_type = message.audio.mime_type
    elif message.photo:
        file_size = message.photo[-1].file_size
        mime_type = "image/jpeg"
        resolution = f"{message.photo[-1].width}x{message.photo[-1].height}"
    elif message.video_note:
        file_size = message.video_note.file_size
        mime_type = "video/mp4"
    
    if not file_name:
        attributes = {
            "video": "mp4",
            "audio": "mp3",
            "video_note": "mp4",
            "photo": "jpg",
        }
        for attribute in attributes:
            if getattr(message, attribute, None):
                file_type, file_format = attribute, attributes[attribute]
                break
        else:
            raise ValueError("Invalid media type.")
        
        date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"{file_type}-{date}"
        if resolution:
            file_name += f" ({resolution})"
        file_name += f".{file_format}"
    
    if not mime_type:
        mime_type = guess_type(file_name)[0] or "application/octet-stream"
    
    return file_name, file_size, mime_type

async def format_file_size(file_size: int):
    if file_size < 1024 * 1024:
        return f"{file_size / 1024:.2f} KB"
    elif file_size < 1024 * 1024 * 1024:
        return f"{file_size / (1024 * 1024):.2f} MB"
    else:
        return f"{file_size / (1024 * 1024 * 1024):.2f} GB"

async def find_existing_message(code: str, limit: int = 100):
    try:
        async for message in SmartPyro.get_chat_history(LOG_CHANNEL_ID, limit=limit):
            if message.caption == code:
                return message.id
    except Exception as e:
        LOGGER.error(f"Error searching for existing message: {e}")
    return None

async def handle_file_download(message: Message, bot: Bot):
    if not message.reply_to_message:
        await send_message(
            chat_id=message.chat.id,
            text="<b>Please Reply To File For Link âŒ</b>",
            parse_mode=ParseMode.HTML
        )
        return
    
    reply_message = message.reply_to_message
    if not (reply_message.document or reply_message.video or reply_message.photo or 
            reply_message.audio or reply_message.video_note):
        await send_message(
            chat_id=message.chat.id,
            text="<b>âŒ Only Video, Audio & Files are supported</b>",
            parse_mode=ParseMode.HTML
        )
        return
    
    processing_msg = await send_message(
        chat_id=message.chat.id,
        text="<b>Processing Your File...</b>",
        parse_mode=ParseMode.HTML
    )
    
    try:
        api_is_running = await check_api_health()
        if not api_is_running:
            await bot.edit_message_text(
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id,
                text="<b>Sorry File To Link Api Is Offline âŒ</b>",
                parse_mode=ParseMode.HTML
            )
            LOGGER.error("API is offline")
            return
        
        bot_member = await SmartPyro.get_chat_member(LOG_CHANNEL_ID, "me")
        if bot_member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await bot.edit_message_text(
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id,
                text="<b>Error: Bot must be an admin in the log channel</b>",
                parse_mode=ParseMode.HTML
            )
            return
        
        bot_me = await bot.get_me()
        bot_user_id = bot_me.id
        telegram_file_id = await get_telegram_file_id(reply_message)
        
        if not telegram_file_id:
            await bot.edit_message_text(
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id,
                text="<b>Error: Could not get file ID</b>",
                parse_mode=ParseMode.HTML
            )
            return
        
        file_name, file_size, mime_type = await get_file_properties(reply_message)
        code = f"{telegram_file_id}-{bot_user_id}"
        
        existing_message_id = await find_existing_message(code)
        
        if existing_message_id:
            message_id = existing_message_id
            LOGGER.info(f"Found existing message: {message_id}")
        else:
            if message.chat.id == LOG_CHANNEL_ID:
                sent = await SmartPyro.copy_message(
                    chat_id=LOG_CHANNEL_ID,
                    from_chat_id=LOG_CHANNEL_ID,
                    message_id=reply_message.message_id,
                    caption=code
                )
                message_id = sent.id
            else:
                sent = await reply_message.forward(LOG_CHANNEL_ID)
                temp_id = sent.message_id
                sent = await SmartPyro.copy_message(
                    chat_id=LOG_CHANNEL_ID,
                    from_chat_id=LOG_CHANNEL_ID,
                    message_id=temp_id,
                    caption=code
                )
                message_id = sent.id
            LOGGER.info(f"Created new message: {message_id}")
        
        quoted_code = urllib.parse.quote(code)
        base_url = FILE_API_URL.rstrip('/')
        download_link = f"{base_url}/dl/{message_id}?code={quoted_code}"
        is_video = mime_type.startswith('video') or reply_message.video or reply_message.video_note
        stream_link = f"{base_url}/dl/{message_id}?code={quoted_code}=stream" if is_video else None
        
        smart_buttons = SmartButtons()
        if is_video:
            smart_buttons.button("ðŸ“¥ Download", url=download_link)
            smart_buttons.button("â–¶ï¸ Stream", url=stream_link)
            keyboard = smart_buttons.build_menu(b_cols=1)
        else:
            smart_buttons.button("ðŸ“¥ Download", url=download_link)
            keyboard = smart_buttons.build_menu(b_cols=1)
        
        if is_video:
            response = (
                f"<b>Video Name:</b> {file_name}\n"
                f"<b>Size:</b> {await format_file_size(file_size)}\n\n"
                f"<b>Download:</b> <code>{download_link}</code>\n\n"
                f"<b>Stream:</b> <code>{stream_link}</code>\n\n"
                f"<b>â€¢ Open in any browser or player.</b>\n"
                f"<b>â€¢ Stream works on PC & Android browsers.</b>"
            )
        else:
            response = (
                f"<b>File Name:</b> {file_name}\n"
                f"<b>File Size:</b> {await format_file_size(file_size)}\n\n"
                f"<b>File Link:</b> <code>{download_link}</code>\n\n"
                f"<b>Use the link to download the file directly.</b>"
            )
        
        await bot.edit_message_text(
            chat_id=processing_msg.chat.id,
            message_id=processing_msg.message_id,
            text=response,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
        LOGGER.info(f"Generated links for message: {message_id}")
        
    except Exception as e:
        LOGGER.error(f"Error generating links: {str(e)}")
        await Smart_Notify(bot, f"{BotCommands}fdl", e, processing_msg)
        await bot.edit_message_text(
            chat_id=processing_msg.chat.id,
            message_id=processing_msg.message_id,
            text=f"<b>âŒ An error occurred while processing your file</b>",
            parse_mode=ParseMode.HTML
        )

@dp.message(Command(commands=["fdl"], prefix=BotCommands))
@new_task
@SmartDefender
async def fdl_command(message: Message, bot: Bot):
    await handle_file_download(message, bot)
```

### How It Works

1. User sends `/fdl` command while replying to a file
2. Bot validates the file type and API availability
3. Bot checks admin permissions in the log channel
4. Generates unique code based on file ID and bot ID
5. Forwards file to log channel or reuses existing message
6. Creates download and stream links
7. Sends formatted response with inline buttons

### Configuration

Set these variables in your bot's `config.py`:
```python
FILE_API_URL = "https://your-domain.com"
LOG_CHANNEL_ID = -1001234567890
```

---

## âš™ï¸ Technical Details

### Performance Optimizations

- **MemorySession**: No disk I/O for session storage
- **Uvloop**: High-performance event loop
- **Semaphore Limiting**: Prevents overload with 100 concurrent requests
- **Aggressive Prefetching**: Downloads up to 10 chunks in parallel
- **Buffer Queue**: 50-chunk queue for smooth streaming
- **4MB Chunks**: Optimal balance between memory and throughput
- **Request Size**: 1MB internal requests for efficient Telegram API usage

### Server Configuration

```python
uvicorn.run(
    "__main__:app",
    host="0.0.0.0",
    port=5000,
    workers=1,
    loop="uvloop",
    limit_concurrency=2000,
    backlog=4096,
    timeout_keep_alive=75,
    h11_max_incomplete_event_size=16777216
)
```

### Error Codes

| Code | Description |
|------|-------------|
| 400 | Invalid request |
| 401 | File code is required |
| 403 | Invalid file code |
| 404 | File not found |
| 416 | Invalid range |
| 500 | Internal server error |
| 503 | Service temporarily unavailable |

---

## ðŸ¤ Contributing

1. Fork [github.com/abirxdhack/FileToLink](https://github.com/abirxdhack/FileToLink)
2. Create a branch: `git checkout -b feature/YourFeature`
3. Commit changes: `git commit -m "Add YourFeature"`
4. Push: `git push origin feature/YourFeature`
5. Open a pull request

---

## ðŸ“© Contact

For custom bots or APIs in Python, PHP, Node.js, or more:
- **Telegram**: [t.me/ISmartCoder](https://t.me/ISmartCoder)
- **GitHub**: [github.com/TheSmartDevs](https://github.com/TheSmartDevs)
- **Community**: [t.me/TheSmartDev](https://t.me/TheSmartDev)

---

**License**: MIT License. See [LICENSE](LICENSE)

**Crafted by [Abir Arafat Chawdhury ðŸ‡§ðŸ‡©](https://t.me/ISmartCoder)**  
Â© 2025 Smart Web Stream