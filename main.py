import os
import uvicorn
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from telethon import TelegramClient
from telethon.sessions import MemorySession

load_dotenv()

try:
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
except (TypeError, ValueError):
    print("CRITICAL ERROR: Variable Environment salah!")
    raise

client = TelegramClient(MemorySession(), API_ID, API_HASH)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(">>> SYSTEM STARTING...")
    try:
        await client.start(bot_token=BOT_TOKEN)
        print(">>> SUKSES LOGIN! <<<")
    except Exception as e:
        print(f">>> GAGAL LOGIN: {e}")
        raise e
    yield
    await client.disconnect()

app = FastAPI(lifespan=lifespan)

async def stream_file_generator(message, offset, limit):
    async for chunk in client.download_file(message.media, offset=offset, limit=limit):
        yield chunk

@app.get("/")
async def root():
    return {"status": "Server Ready", "type": "Memory Session Mode"}

@app.get("/stream/{msg_id}")
async def stream_video(msg_id: int, request: Request):
    try:
        message = await client.get_messages(CHANNEL_ID, ids=msg_id)
        
        if not message or not message.file:
            return Response("File not found (Cek ID Pesan!)", status_code=404)

        file_size = message.file.size
        mime_type = message.file.mime_type or "video/mp4"
        
        range_header = request.headers.get("range")
        start, end = 0, file_size - 1
        
        if range_header:
            range_value = range_header.replace("bytes=", "").split("-")
            start = int(range_value[0])
            if range_value[1]:
                end = int(range_value[1])
        
        content_length = (end - start) + 1
        
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Type": mime_type,
        }

        return StreamingResponse(
            stream_file_generator(message, start, content_length),
            status_code=206, 
            headers=headers
        )

    except Exception as e:
        print(f"Error Stream: {e}")
        return Response(f"Internal Error: {str(e)}", status_code=500)
