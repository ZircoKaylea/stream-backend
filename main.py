import os
import uvicorn
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from telethon import TelegramClient

# Load Environment Variables
load_dotenv()

# Ambil variable dengan pengecekan
try:
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
except (TypeError, ValueError):
    print("CRITICAL ERROR: Variable Environment tidak ditemukan atau salah format!")
    print("Pastikan API_ID, API_HASH, BOT_TOKEN, CHANNEL_ID sudah di-set di Koyeb.")
    # Kita biarkan error meledak agar ketahuan di log kalau ini penyebabnya
    raise

# Inisialisasi Client Telegram
client = TelegramClient('bot_session', API_ID, API_HASH)

# --- BAGIAN BARU: LIFESPAN (PENGGANTI STARTUP) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dijalankan saat server nyala
    print(">>> SYSTEM STARTING... MENGHUBUNGKAN KE TELEGRAM...")
    try:
        await client.start(bot_token=BOT_TOKEN)
        print(">>> SUKSES! BOT BERHASIL LOGIN & SIAP STREAMING <<<")
    except Exception as e:
        print(f">>> GAGAL LOGIN: {e}")
        raise e
    yield
    # Dijalankan saat server mati
    await client.disconnect()

app = FastAPI(lifespan=lifespan)

# --- ROUTE STREAMING ---
async def stream_file_generator(message, offset, limit):
    async for chunk in client.download_file(message.media, offset=offset, limit=limit):
        yield chunk

@app.get("/")
async def root():
    return {"status": "Server Running", "mode": "Koyeb Production"}

@app.get("/stream/{msg_id}")
async def stream_video(msg_id: int, request: Request):
    try:
        # Ambil pesan dari channel
        message = await client.get_messages(CHANNEL_ID, ids=msg_id)
        
        if not message or not message.file:
            return Response("File not found", status_code=404)

        file_size = message.file.size
        mime_type = message.file.mime_type or "video/mp4"
        
        # Logika Range Header (Seek/Geser Durasi)
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
        return Response(f"Error: {str(e)}", status_code=500)
