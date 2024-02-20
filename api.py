

import os
import uuid
import studio
import ai_host
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from fastapi import UploadFile, File
import shutil
from fastapi import FastAPI, HTTPException
from fastapi import FastAPI, Depends, HTTPException, Header
from jose import jwt, JWTError
from typing import Optional
import httpx
from supabase import create_client

url: str = "https://ksuzseqojigqoxqhzlnt.supabase.co"
key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtzdXpzZXFvamlncW94cWh6bG50Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MDgxNzA0MDgsImV4cCI6MjAyMzc0NjQwOH0.nF2--mvungU8684wKso9V_tQ3locm8WaYRIZesXKbhs"
supabase_client = create_client(url, key)

app = FastAPI()

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure this directory exists and contains your audio files
AUDIO_FILE_DIR = "audio_files"


async def get_current_user(token: str = Header(...)):
    try:
        # You need to replace 'your-supabase-secret' with your actual secret key
        # or fetch Supabase's public keys to verify the JWT properly
        payload = jwt.decode(
            token, "fW4WH3aIZLdXOnUy/880/c51rnM11R0c2IrC5LsboFpiIKZSGaTg38pC5cGlspCtcN/hR/Dev3IUx2uNuRd3OQ==", algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=400, detail="Invalid JWT token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid JWT token")


@app.get("/api/podcast/list")
async def podcast_list():
    from db import podcasts

    return podcasts


@app.get("/api/podcast/details")
async def podcast_list(podcast_id: str,):
    from db import podcasts
    podcast = next(
        (podcast for podcast in podcasts if podcast['id'] == podcast_id), None)
    return podcast


@app.post("/api/podcast/speak")
async def podcast_speak(session_id: str, podcast_id: str, file: UploadFile = File(...)):
    file_location = f"{AUDIO_FILE_DIR}/{session_id}/{uuid.uuid4()}-{file.filename}"
    os.makedirs(os.path.dirname(file_location), exist_ok=True)

    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)

    text = await studio.transcribe_audio(file_location)

    from db import podcasts
    podcast = next(
        (podcast for podcast in podcasts if podcast['id'] == podcast_id), None)
    system_prompt = podcast['systemPrompt']
    host = podcast['host']

    response = ai_host.chat(system_prompt, session_id, text)
    # @TODO: Fix this:  Truncate the response to the first 4096 characters if it's longer
    truncated_response = response[:4096] if len(response) > 4096 else response

    file_uuid = uuid.uuid4()
    voice = await studio.generate_speech(truncated_response, host or "alloy", f'{AUDIO_FILE_DIR}/{session_id}/{file_uuid}.mp3')

    return {"text": response, "voice_id": file_uuid}


@app.get("/api/podcast/test")
async def podcast_test():
    query = supabase_client.table("podcasts").select("*").execute()

    return {'session_id': query}


@app.get("/api/podcast/start")
async def podcast_start(podcast_id):
    session_id = uuid.uuid4()
    os.makedirs(os.path.dirname(
        f'{AUDIO_FILE_DIR}/{session_id}/fake.test'), exist_ok=True)

    from db import podcasts
    podcast = next(
        (podcast for podcast in podcasts if podcast['id'] == podcast_id), None)
    text = podcast['introPrompt']

    intro = await studio.make_intro(text, session_id)

    return {"session_id": session_id, "text": text, "voice_id": 'intro'}


@app.get("/api/podcast/save")
async def podcast_save(session_id):
    studio.compile_audio_with_intro(session_id)
    return {"session_id": session_id, "voice_id": 'final_compliation'}


@app.get('/api/podcast/file')
async def file(session_id: str, uuid: str):
    file_path = f"{AUDIO_FILE_DIR}/{session_id}/{uuid}.mp3"

    try:
        # Attempt to return the file response
        return FileResponse(path=file_path, media_type='audio/mpeg', filename=f"{uuid}.mp3")
    except FileNotFoundError:
        # If the file does not exist, return a 404 error
        raise HTTPException(status_code=404, detail="File not found")
