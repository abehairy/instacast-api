

from fastapi import UploadFile, File
import shutil
from fastapi import FastAPI, HTTPException

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import innerview_ai
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


@app.post("api/podcast/speak")
async def podcast_speak(podcast_id: str, file: UploadFile = File(...)):
    file_location = f"{AUDIO_FILE_DIR}/{podcast_id}/{uuid.uuid4()}-{file.filename}"
    os.makedirs(os.path.dirname(file_location), exist_ok=True)

    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)

    text = await studio.transcribe_audio(file_location)
    print(text)
    response = innerview_ai.chat(text)
    print(response)
    file_uuid = uuid.uuid4()
    voice = await studio.generate_speech(response, 'alloy', f'{AUDIO_FILE_DIR}/{podcast_id}/{file_uuid}.mp3')

    return {"text": response, "voice_id": file_uuid}


@app.get("api/podcast/start")
async def podcast_start():
    podcast_id = uuid.uuid4()
    os.makedirs(os.path.dirname(
        f'{AUDIO_FILE_DIR}/{podcast_id}/fake.test'), exist_ok=True)

    text = 'Hi and welcome to our show where we do a delve deep inside your life and take a deep look on how things can become as part of a bigger humanity condition'
    intro = await studio.make_intro(text, podcast_id)

    return {"podcast_id": podcast_id, "text": text, "voice_id": 'intro'}


@app.get("api/podcast/save")
async def podcast_save(podcast_id):
    studio.compile_audio_with_intro(podcast_id)
    return {"podcast_id": podcast_id, "voice_id": 'final_compliation'}


@app.get('api/podcast/file')
async def file(podcast_id: str, uuid: str):
    # Construct the file path using the provided UUID
    file_path = f"{AUDIO_FILE_DIR}/{podcast_id}/{uuid}.mp3"

    try:
        # Attempt to return the file response
        return FileResponse(path=file_path, media_type='audio/mpeg', filename=f"{uuid}.mp3")
    except FileNotFoundError:
        # If the file does not exist, return a 404 error
        raise HTTPException(status_code=404, detail="File not found")
