

from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.etree import ElementTree as ET
from fastapi.responses import Response
from fastapi import UploadFile, File
import shutil
from fastapi import FastAPI, HTTPException
from datetime import datetime  # Import the datetime class from the datetime module
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


@app.get("/api/rss", response_class=Response, include_in_schema=False)
async def generate_rss_feed():
    rss = Element("rss", attrib={
        "version": "2.0",
        "xmlns:itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    })

    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = "The InnerView Podcast"
    SubElement(channel, "link").text = "https://instacast.live/"
    SubElement(channel, "description").text = "Explore the essence of storytelling with 'The InnerView Podcast'. Delve into personal journeys, uncovering the raw and real experiences that shape us."
    SubElement(channel, "itunes:author").text = "InstaCast AI"
    # Spotify does not use this tag, but it's added for completeness
    SubElement(channel, "itunes:email").text = "ahmed@behairy.me"
    SubElement(
        channel, "managingEditor").text = "ahmed@behairy.me (Podcast Author)"

    # Cover art according to Spotify's specifications
    itunes_image = SubElement(channel, "itunes:image")
    itunes_image.set(
        "href", "https://instacast.live/dashy-assets/images/innerview-thumbnail.png")

    # Example podcast episode
    item = SubElement(channel, "item")
    SubElement(item, "title").text = "Episode 1: How One Call Changed His Life"
    SubElement(
        item, "itunes:summary").text = "Meet Ahmed Behairy, a software engineer that delved into digital health after recieving one call that changed his life "
    SubElement(
        item, "description").text = "<![CDATA[<p>Episode Description</p>]]>"
    SubElement(item, "pubDate").text = datetime.utcnow().strftime(
        "%a, %d %b %Y %H:%M:%S +0000")
    guid = SubElement(item, "guid")
    guid.set("isPermaLink", "false")
    guid.text = "https://example.com/path/to/episode"
    enclosure = SubElement(item, "enclosure")
    enclosure.set(
        "url", "https://instacast.live/api/podcast/file?session_id=73b1bde7-4653-49d6-984b-cd99a3d40993&uuid=final_compilation")
    enclosure.set("type", "audio/mpeg")
    enclosure.set("length", "123456")  # File size in bytes

    rss_feed = tostring(rss, encoding="utf-8", method="xml")
    return Response(content=rss_feed, media_type="application/rss+xml")
