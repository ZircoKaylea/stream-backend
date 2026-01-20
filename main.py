import uvicorn
import os
import mimetypes
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from telethon import TelegramClient

load_dotenv()

try:
    API_ID = int(os.getenv("API_ID")) 
    API_HASH = os.getenv("API_HASH")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
except TypeError:
    print("Error env")
    raise SystemExit

client = TelegramClient('bot_session', API_ID, API_HASH)
app = FastAPI()

@app.on_event("startup")
async def startup():
    await client.start(bot_token=BOT_TOKEN)
    print("Sukses")

async def stream_file_generator(message, offset, limit):
    async for chunk in client.download_file(message.media, offset=offset, limit=limit):
        yield chunk

@app.get("/")
async def root():
    return {"status": "Server Running", "mode": "Secure Environment"}

@app.get("/stream/{msg_id}")
async def stream_video(msg_id: int, request: Request):
    try:
        message = await client.get_messages(CHANNEL_ID, ids=msg_id)
        
        if not message or not message.file:
            return Response("File not found or not a media", status_code=404)

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
        return Response(f"Internal Server Error: {str(e)}", status_code=500)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

