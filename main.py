import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from telethon import TelegramClient
import mimetypes

API_ID = 34645169
API_HASH = '1560e22f188b1214d690156c73f527ca'
BOT_TOKEN = '8482962043:AAEIAqBZTyYvZ_UsJaTr7q6HXVYHz7oyTpQ'
CHANNEL_ID = -1003584774161

client = TelegramClient('bot_session', API_ID, API_HASH)
app = FastAPI()

@app.on_event("startup")
async def startup():
    await client.start(bot_token=BOT_TOKEN)
    print(">>> BOT BERHASIL LOGIN KE TELEGRAM! <<<")

async def stream_file_generator(message, offset, limit):
    async for chunk in client.download_file(message.media, offset=offset, limit=limit):
        yield chunk

@app.get("/")
async def root():
    return {"status": "Server Aktif", "message": "Gunakan /stream/{message_id} untuk nonton"}

@app.get("/stream/{msg_id}")
async def stream_video(msg_id: int, request: Request):
    try:
        # 1. Cari pesan di channel berdasarkan ID
        message = await client.get_messages(CHANNEL_ID, ids=msg_id)
        
        # Cek apakah pesan ada dan punya file media
        if not message or not message.file:
            return Response("File tidak ditemukan atau bukan media", status_code=404)

        file_size = message.file.size
        # Deteksi tipe file (misal: video/mp4)
        mime_type = message.file.mime_type or "application/octet-stream"
        
        # 2. Logika 'Range Header' (Wajib buat Streaming HP)
        # HP akan minta: "Kirimin dong dari detik ke-5 sampai detik ke-10 aja"
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

        # 3. Kirim respon streaming
        return StreamingResponse(
            stream_file_generator(message, start, content_length),
            status_code=206, 
            headers=headers
        )

    except Exception as e:
        print(f"Error: {e}")
        return Response(f"Internal Server Error: {str(e)}", status_code=500)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)