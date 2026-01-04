import os
import asyncio
import socket
import urllib.parse
from math import ceil, floor
from mimetypes import guess_type
from datetime import datetime
from collections import deque
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from telethon import TelegramClient
from telethon.sessions import MemorySession
from telethon.tl.custom import Message

try:
    from config import API_ID, API_HASH, BOT_TOKEN, LOG_CHANNEL_ID
    from utils import LOGGER
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    LOGGER = logging.getLogger(__name__)
    API_ID = os.getenv("API_ID")
    API_HASH = os.getenv("API_HASH")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))

HEROKU_APP_NAME = os.getenv("HEROKU_APP_NAME")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
RAILWAY_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN")
RAILWAY_STATIC_URL = os.getenv("RAILWAY_STATIC_URL")
FLY_APP_NAME = os.getenv("FLY_APP_NAME")
VERCEL_URL = os.getenv("VERCEL_URL")
CUSTOM_DOMAIN = os.getenv("CUSTOM_DOMAIN")

class Telegram:
    API_ID = API_ID
    API_HASH = API_HASH
    BOT_TOKEN = BOT_TOKEN
    CHANNEL_ID = LOG_CHANNEL_ID

class Server:
    BIND_ADDRESS = "0.0.0.0"
    PORT = int(os.getenv("PORT", 5000))
    BASE_URL = None

templates = Jinja2Templates(directory="templates")

error_messages = {
    400: "Invalid request.",
    401: "File code is required to download the file.",
    403: "Invalid file code.",
    404: "File not found.",
    416: "Invalid range.",
    500: "Internal server error.",
    503: "Service temporarily unavailable.",
}

def get_base_url_from_request(request: Request) -> str:
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    host = request.headers.get("host")

    if forwarded_host:
        scheme = forwarded_proto or "https"
        return f"{scheme}://{forwarded_host}"
    elif host:
        scheme = "https" if forwarded_proto == "https" else "http"
        return f"{scheme}://{host}"
    else:
        return Server.BASE_URL or f"http://localhost:{Server.PORT}"

def abort(status_code: int = 500, description: str = None):
    raise HTTPException(status_code=status_code, detail=description or error_messages.get(status_code))

def sanitize_filename(filename):
    try:
        filename.encode('latin-1')
        return filename
    except UnicodeEncodeError:
        encoded = urllib.parse.quote(filename, safe='')
        return encoded

def get_file_properties(message: Message):
    file_name = message.file.name
    file_size = message.file.size or 0
    mime_type = message.file.mime_type
    if not file_name:
        attributes = {
            "video": "mp4",
            "audio": "mp3",
            "voice": "ogg",
            "photo": "jpg",
            "video_note": "mp4",
        }
        for attribute in attributes:
            media = getattr(message, attribute, None)
            if media:
                file_type, file_format = attribute, attributes[attribute]
                break
        else:
            abort(400, "Invalid media type.")
        date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"{file_type}-{date}.{file_format}"
    if not mime_type:
        mime_type = guess_type(file_name)[0] or "application/octet-stream"
    return file_name, file_size, mime_type

class FileToLinkAPI(TelegramClient):
    def __init__(self, api_id, api_hash, bot_token):
        LOGGER.info("Creating Telethon FileToLink Client From BOT_TOKEN with MemorySession")
        super().__init__(
            MemorySession(),
            api_id,
            api_hash,
            connection_retries=-1,
            timeout=120,
            flood_sleep_threshold=0
        )
        self.bot_token = bot_token
        self.request_count = 0
        self.max_concurrent = 100
        self.semaphore = asyncio.Semaphore(self.max_concurrent)

    async def start_api(self):
        await self.start(bot_token=self.bot_token)
        LOGGER.info("Telethon FileToLink Client Created Successfully with MemorySession!")
        LOGGER.info("FileToLinkAPI started with max concurrent requests: %s", self.max_concurrent)

async def get_local_ip():
    loop = asyncio.get_event_loop()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setblocking(False)
    try:
        await loop.sock_connect(s, ("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

async def detect_base_url():
    if CUSTOM_DOMAIN:
        base_url = f"https://{CUSTOM_DOMAIN}" if not CUSTOM_DOMAIN.startswith("http") else CUSTOM_DOMAIN
        LOGGER.info(f"Using CUSTOM_DOMAIN: {base_url}")
        return base_url

    if HEROKU_APP_NAME:
        base_url = f"https://{HEROKU_APP_NAME}.herokuapp.com"
        LOGGER.info(f"Detected Heroku deployment: {base_url}")
        return base_url

    if RENDER_EXTERNAL_URL:
        base_url = RENDER_EXTERNAL_URL.rstrip('/')
        LOGGER.info(f"Detected Render deployment: {base_url}")
        return base_url

    if RAILWAY_PUBLIC_DOMAIN:
        base_url = f"https://{RAILWAY_PUBLIC_DOMAIN}"
        LOGGER.info(f"Detected Railway deployment (public domain): {base_url}")
        return base_url

    if RAILWAY_STATIC_URL:
        base_url = RAILWAY_STATIC_URL.rstrip('/')
        LOGGER.info(f"Detected Railway deployment (static URL): {base_url}")
        return base_url

    if FLY_APP_NAME:
        base_url = f"https://{FLY_APP_NAME}.fly.dev"
        LOGGER.info(f"Detected Fly.io deployment: {base_url}")
        return base_url

    if VERCEL_URL:
        base_url = f"https://{VERCEL_URL}"
        LOGGER.info(f"Detected Vercel deployment: {base_url}")
        return base_url

    ip = await get_local_ip()
    base_url = f"http://{ip}:{Server.PORT}"
    LOGGER.info(f"No platform detected, using local IP: {base_url}")
    return base_url

@asynccontextmanager
async def lifespan(app: FastAPI):
    Server.BASE_URL = await detect_base_url()
    await api_instance.start_api()
    LOGGER.info(f"API running on: {Server.BASE_URL}")
    yield
    LOGGER.info("Shutting down API")
    await api_instance.disconnect()

app = FastAPI(lifespan=lifespan, title="FileToLink")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        return HTMLResponse(content=f"<h1>FileToLink API</h1><p>Status: Running</p><p>Error loading template: {str(e)}</p>")

@app.get("/stream/{file_id}", response_class=HTMLResponse)
async def stream_file(file_id: int, request: Request):
    code = request.query_params.get("code") or abort(401)
    async with api_instance.semaphore:
        me = await api_instance.get_me()
        api_name = "@" + me.username
        LOGGER.info("Stream request - File ID: %s, Using API: %s", file_id, api_name)

        file_task = asyncio.create_task(api_instance.get_messages(Telegram.CHANNEL_ID, ids=int(file_id)))

        try:
            file = await asyncio.wait_for(file_task, timeout=10.0)
            if not file:
                LOGGER.warning("Message %s not found in channel %s", file_id, Telegram.CHANNEL_ID)
                abort(404)
        except asyncio.TimeoutError:
            LOGGER.error("Timeout retrieving message %s", file_id)
            abort(500, "Request timeout")
        except Exception as e:
            LOGGER.error("Failed to retrieve message %s using API %s: %s", file_id, api_name, e)
            abort(500)

        if code != file.raw_text:
            LOGGER.warning("Access denied - Invalid code for file %s: provided=%s, expected=%s", file_id, code, file.raw_text)
            abort(403)

        file_name, file_size, mime_type = get_file_properties(file)
        LOGGER.info("File properties - Name: %s, Size: %s, Type: %s", file_name, file_size, mime_type)

        quoted_code = urllib.parse.quote(code)
        base_url = get_base_url_from_request(request)
        file_url = f"{base_url}/dl/{file_id}?code={quoted_code}"
        file_size_mb = f"{file_size / (1024 * 1024):.2f} MB"

        try:
            return templates.TemplateResponse("player.html", {
                "request": request,
                "file_name": file_name,
                "file_size_mb": file_size_mb,
                "file_url": file_url,
                "mime_type": mime_type
            })
        except Exception as e:
            return HTMLResponse(content=f"<h1>{file_name}</h1><p>Size: {file_size_mb}</p><a href='{file_url}'>Download</a>")

@app.get("/dl/{file_id}")
async def transmit_file(file_id: int, request: Request):
    code = request.query_params.get("code") or abort(401)

    if code.endswith("=stream"):
        code_clean = code[:-7]
        quoted_code = urllib.parse.quote(code_clean)
        base_url = get_base_url_from_request(request)
        async with api_instance.semaphore:
            me = await api_instance.get_me()
            api_name = "@" + me.username
            LOGGER.info("Stream request redirected from dl - File ID: %s, Using API: %s", file_id, api_name)

            file_task = asyncio.create_task(api_instance.get_messages(Telegram.CHANNEL_ID, ids=int(file_id)))

            try:
                file = await asyncio.wait_for(file_task, timeout=10.0)
                if not file:
                    LOGGER.warning("Message %s not found in channel %s", file_id, Telegram.CHANNEL_ID)
                    abort(404)
            except asyncio.TimeoutError:
                LOGGER.error("Timeout retrieving message %s", file_id)
                abort(500, "Request timeout")
            except Exception as e:
                LOGGER.error("Failed to retrieve message %s using API %s: %s", file_id, api_name, e)
                abort(500)

            if code_clean != file.raw_text:
                LOGGER.warning("Access denied - Invalid code for file %s: provided=%s, expected=%s", file_id, code_clean, file.raw_text)
                abort(403)

            file_name, file_size, mime_type = get_file_properties(file)
            LOGGER.info("File properties - Name: %s, Size: %s, Type: %s", file_name, file_size, mime_type)

            file_url = f"{base_url}/dl/{file_id}?code={quoted_code}"
            file_size_mb = f"{file_size / (1024 * 1024):.2f} MB"

            try:
                return templates.TemplateResponse("player.html", {
                    "request": request,
                    "file_name": file_name,
                    "file_size_mb": file_size_mb,
                    "file_url": file_url,
                    "mime_type": mime_type
                })
            except Exception as e:
                return HTMLResponse(content=f"<h1>{file_name}</h1><p>Size: {file_size_mb}</p><a href='{file_url}'>Download</a>")

    async with api_instance.semaphore:
        me = await api_instance.get_me()
        api_name = "@" + me.username
        LOGGER.info("File download request - File ID: %s, Using API: %s", file_id, api_name)

        file_task = asyncio.create_task(api_instance.get_messages(Telegram.CHANNEL_ID, ids=int(file_id)))

        try:
            file = await asyncio.wait_for(file_task, timeout=10.0)
            if not file:
                LOGGER.warning("Message %s not found in channel %s", file_id, Telegram.CHANNEL_ID)
                abort(404)
        except asyncio.TimeoutError:
            LOGGER.error("Timeout retrieving message %s", file_id)
            abort(500, "Request timeout")
        except Exception as e:
            LOGGER.error("Failed to retrieve message %s using API %s: %s", file_id, api_name, e)
            abort(500)

        if code != file.raw_text:
            LOGGER.warning("Access denied - Invalid code for file %s: provided=%s, expected=%s", file_id, code, file.raw_text)
            abort(403)

        file_name, file_size, mime_type = get_file_properties(file)
        LOGGER.info("File properties - Name: %s, Size: %s, Type: %s", file_name, file_size, mime_type)

        range_header = request.headers.get("Range", "")
        if range_header:
            from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
            from_bytes = int(from_bytes)
            until_bytes = int(until_bytes) if until_bytes else file_size - 1
            LOGGER.info("Range request - Bytes: %s-%s/%s", from_bytes, until_bytes, file_size)
        else:
            from_bytes = 0
            until_bytes = file_size - 1
            LOGGER.info("Full file request - Size: %s bytes", file_size)

        if (until_bytes > file_size) or (from_bytes < 0) or (until_bytes < from_bytes):
            LOGGER.error("Invalid range request - Bytes: %s-%s/%s", from_bytes, until_bytes, file_size)
            abort(416, "Invalid range.")

        chunk_size = 4 * 1024 * 1024
        until_bytes = min(until_bytes, file_size - 1)
        offset = from_bytes - (from_bytes % chunk_size)
        first_part_cut = from_bytes - offset
        last_part_cut = until_bytes % chunk_size + 1
        req_length = until_bytes - from_bytes + 1
        part_count = ceil(until_bytes / chunk_size) - floor(offset / chunk_size)

        sanitized_filename = sanitize_filename(file_name)

        headers = {
            "Content-Type": f"{mime_type}",
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Length": str(req_length),
            "Content-Disposition": f"attachment; filename*=UTF-8''{sanitized_filename}",
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600",
            "Connection": "keep-alive",
        }

        LOGGER.info("Starting file download - API: %s, Chunks: %s, Chunk size: %s", api_name, part_count, chunk_size)

        async def file_generator():
            current_part = 1
            prefetch_buffer = asyncio.Queue(maxsize=50)
            buffer_task = None

            async def aggressive_prefetch():
                chunk_tasks = deque()
                max_parallel_chunks = 10

                async for chunk in api_instance.iter_download(
                    file,
                    offset=offset,
                    chunk_size=chunk_size,
                    stride=chunk_size,
                    file_size=file_size,
                    request_size=1024 * 1024,
                ):
                    while len(chunk_tasks) >= max_parallel_chunks:
                        done_task = chunk_tasks.popleft()
                        await done_task

                    chunk_task = asyncio.create_task(prefetch_buffer.put(chunk))
                    chunk_tasks.append(chunk_task)

                for task in chunk_tasks:
                    await task

                await prefetch_buffer.put(None)

            buffer_task = asyncio.create_task(aggressive_prefetch())

            try:
                while current_part <= part_count:
                    try:
                        chunk = await asyncio.wait_for(prefetch_buffer.get(), timeout=15.0)
                    except asyncio.TimeoutError:
                        LOGGER.warning("Prefetch timeout - retrying")
                        continue

                    if chunk is None:
                        break

                    if part_count == 1:
                        yield chunk[first_part_cut:last_part_cut]
                    elif current_part == 1:
                        yield chunk[first_part_cut:]
                    elif current_part == part_count:
                        yield chunk[:last_part_cut]
                    else:
                        yield chunk

                    current_part += 1

                LOGGER.info("File download completed successfully - File: %s, API: %s", file_name, api_name)
            except Exception as e:
                LOGGER.error("Error during file download - File: %s, API: %s, Error: %s", file_name, api_name, e)
                raise
            finally:
                if buffer_task and not buffer_task.done():
                    buffer_task.cancel()
                    try:
                        await buffer_task
                    except asyncio.CancelledError:
                        pass
                LOGGER.info("API %s processing completed", api_name)

        return StreamingResponse(
            file_generator(),
            headers=headers,
            status_code=206 if range_header else 200,
            media_type=mime_type
        )

@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    error_message = error_messages.get(exc.status_code)
    return Response(content=exc.detail or error_message, status_code=exc.status_code)

api_instance = FileToLinkAPI(
    api_id=Telegram.API_ID,
    api_hash=Telegram.API_HASH,
    bot_token=Telegram.BOT_TOKEN
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "__main__:app",
        host=Server.BIND_ADDRESS,
        port=Server.PORT,
        workers=1,
        loop="uvloop",
        limit_concurrency=2000,
        backlog=4096,
        timeout_keep_alive=75,
        h11_max_incomplete_event_size=16777216
    )