

from fastapi import UploadFile, File
import shutil
from fastapi import FastAPI, HTTPException

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import ai_host
import studio
import uuid
import os

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


@app.get("/api/podcast/list")
async def podcast_list():
    from db import podcasts

    return podcasts


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
    return {'session_id': 'hello world'}


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
