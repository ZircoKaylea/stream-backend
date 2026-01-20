import uvicorn
import os
import mimetypes
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from telethon import TelegramClient

# 1. Load data rahasia dari file .env (untuk di komputer lokal)
# Kalau di Koyeb, baris ini otomatis diabaikan karena tidak ada file .env
load_dotenv()

# 2. Ambil Variable Aman
# Kita pakai os.getenv agar tidak menulis password langsung di codingan
try:
    API_ID = int(os.getenv("API_ID")) 
    API_HASH = os.getenv("API_HASH")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
except TypeError:
    # Error handling kalau lupa setting .env atau Koyeb Variables
    print("ERROR: Variable Environment belum disetting! Cek .env atau Settings Koyeb.")
    raise SystemExit

# Inisialisasi Client Telegram
client = TelegramClient('bot_session', API_ID, API_HASH)
app = FastAPI()

@app.on_event("startup")
async def startup():
    # Login ke Telegram saat server nyala
    await client.start(bot_token=BOT_TOKEN)
    print(">>> BOT BERHASIL LOGIN! SIAP STREAMING <<<")

# Generator: Mengambil potongan data (chunks) dari Telegram
async def stream_file_generator(message, offset, limit):
    async for chunk in client.download_file(message.media, offset=offset, limit=limit):
        yield chunk

@app.get("/")
async def root():
    return {"status": "Server Running", "mode": "Secure Environment"}

@app.get("/stream/{msg_id}")
async def stream_video(msg_id: int, request: Request):
    try:
        # Ambil pesan dari channel target
        message = await client.get_messages(CHANNEL_ID, ids=msg_id)
        
        # Cek apakah pesan valid dan ada filenya
        if not message or not message.file:
            return Response("File not found or not a media", status_code=404)

        file_size = message.file.size
        # Deteksi tipe file, default ke mp4 kalau tidak terdeteksi
        mime_type = message.file.mime_type or "video/mp4"
        
        # --- LOGIKA RANGE HEADER (PENTING UNTUK VIDEO PLAYER) ---
        # Mengatur agar video bisa digeser (seek) durasinya
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

        # Kirim respons streaming (Status 206 Partial Content)
        return StreamingResponse(
            stream_file_generator(message, start, content_length),
            status_code=206, 
            headers=headers
        )

    except Exception as e:
        print(f"Error Stream: {e}")
        return Response(f"Internal Server Error: {str(e)}", status_code=500)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
