

from pydantic import BaseModel, EmailStr
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


class EpisodeMetadata(BaseModel):
    podcast_id: str
    episode_id: str
    title: str
    user: str
    email: EmailStr


@app.get("/api/podcast/list")
async def podcast_list():
    from db import podcasts

    return podcasts


@app.get("/api/podcast/details")
async def podcast_details(podcast_id: str,):
    from db import podcasts
    podcast = next(
        (podcast for podcast in podcasts if podcast['id'] == podcast_id), None)
    return podcast


@app.get("/api/podcast/episode")
async def episode(podcast_id: str, episode_id: str,):
    from redis_db import get_episode_metadata
    return get_episode_metadata(podcast_id, episode_id)


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


# @app.get("/api/podcast/save")
# async def podcast_save(session_id):
#     studio.compile_audio_with_intro(session_id)
#     return {"session_id": session_id, "voice_id": 'final_compliation'}


@app.get("/api/podcast/episodes_catalog")
async def get_episodes_catalog():
    from redis_db import find_keys_by_pattern, get_episode_metadata_by_key
    from db import podcasts  # Assuming this imports a list of all podcasts

    episodes_catalog = []

    # Retrieve episodes for all podcasts
    for podcast in podcasts:
        # Construct the search pattern for Redis keys based on podcast ID
        search_pattern = f"{podcast['id']}-*"

        # Retrieve all matching keys for the current podcast
        keys = find_keys_by_pattern(search_pattern)

        for key in keys:
            episode_metadata = get_episode_metadata_by_key(key)
            if episode_metadata:
                episode_metadata['episode_id'] = key.split("-", 1)[1]
                # Merge episode metadata with podcast details to create a flat structure
                # If you wish to include some podcast details, modify this line accordingly
                flat_episode_data = {**podcast, **episode_metadata}
                episodes_catalog.append(flat_episode_data)

    return episodes_catalog


@app.get("/api/podcast/episodes")
async def get_episodes(podcast_id: str):
    from redis_db import find_keys_by_pattern, get_episode_metadata_by_key
    from db import podcasts  # Importing here to follow your original structure

    # Retrieve the podcast object
    podcast = next((pod for pod in podcasts if pod['id'] == podcast_id), None)

    if podcast is None:
        raise HTTPException(status_code=404, detail="Podcast not found.")

    # Construct the search pattern for Redis keys
    search_pattern = f"{podcast_id}-*"

    # Retrieve all matching keys
    keys = find_keys_by_pattern(search_pattern)

    if not keys:
        raise HTTPException(
            status_code=404, detail="No episodes found for the given podcast ID.")

    # Retrieve metadata for each key and merge it with the podcast data
    episodes = []
    for key in keys:
        episode_metadata = get_episode_metadata_by_key(key)
        if episode_metadata:
            # Merge episode metadata with podcast details, creating a flat structure
            flat_episode_data = {**podcast, **episode_metadata}
            episodes.append(flat_episode_data)

    return episodes


@app.post("/api/podcast/save")
async def podcast_save(episode_metadata: EpisodeMetadata):
    from redis_db import save_episode_metadata
    try:
        # Assuming studio.compile_audio_with_intro is an async function
        studio.compile_audio_with_intro(episode_metadata.episode_id)
        # Save metadata to Redis using podcast_id and episode_id
        save_episode_metadata(
            episode_metadata.podcast_id,
            episode_metadata.episode_id,
            episode_metadata.title,
            episode_metadata.user,
            episode_metadata.email
        )
        return {"podcast_id": episode_metadata.podcast_id, "session_id": episode_metadata.episode_id, "voice_id": 'final_compilation'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/podcast/file')
async def file(session_id: str, uuid: str):
    file_path = f"{AUDIO_FILE_DIR}/{session_id}/{uuid}.mp3"

    try:
        # Attempt to return the file response
        return FileResponse(path=file_path, media_type='audio/mpeg', filename=f"{uuid}.mp3")
    except FileNotFoundError:
        # If the file does not exist, return a 404 error
        raise HTTPException(status_code=404, detail="File not found")


@app.get("/api/rss", response_class=Response)
async def generate_rss_feed(podcast_id: str = "innerview"):
    from redis_db import find_keys_by_pattern, get_episode_metadata_by_key
    from xml.etree.ElementTree import Element, SubElement, tostring

    # Assuming 'podcasts' is a list of dicts, each representing a podcast
    from db import podcasts
    podcast = next((p for p in podcasts if p['id'] == podcast_id), None)

    if not podcast:
        raise HTTPException(
            status_code=404, detail=f"Podcast {podcast_id} not found.")

    # Construct the search pattern for Redis keys based on podcast ID
    search_pattern = f"{podcast_id}-*"

    # Retrieve all matching keys for the podcast
    keys = find_keys_by_pattern(search_pattern)

    rss = Element("rss", attrib={
        "version": "2.0",
        "xmlns:itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    })
    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = podcast.get(
        "title", "The InnerView Podcast")
    SubElement(channel, "link").text = podcast.get(
        "link", "https://instacast.live")
    SubElement(channel, "description").text = podcast.get(
        "description", "Podcast Description")
    SubElement(channel, "itunes:author").text = podcast.get(
        "author", "InstaCast AI")

    # Generate RSS items for each episode
    for key in keys:
        episode = get_episode_metadata_by_key(key)
        episode_id = key.split("-", 1)[1]
        if episode:
            item = SubElement(channel, "item")
            SubElement(item, "title").text = episode.get(
                "user", "Episode Title") + "| " + episode.get(
                "title", "Episode Summary")
            SubElement(item, "itunes:summary").text = episode.get(
                "title", "Episode Summary")
            SubElement(
                item, "description").text = f"<![CDATA[{episode.get('description', 'Episode Description')}]>"
            SubElement(item, "pubDate").text = episode.get(
                "pubDate", datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000"))
            guid = SubElement(item, "guid")
            guid.set("isPermaLink", "false")
            guid.text = episode.get("guid", "Unique Identifier")
            enclosure = SubElement(item, "enclosure")
            enclosure.set("url", episode.get(
                "fileUrl", "https://instacast.live/api/podcast/file?session_id="+episode_id+"&uuid=final_compilation"))
            enclosure.set("type", "audio/mpeg")
            # File size in bytes
            enclosure.set("length", str(episode.get("fileSize", "123456")))

    rss_feed = tostring(rss, encoding="utf-8", method="xml")
    return Response(content=rss_feed, media_type="application/rss+xml")


# @app.get("/api/rss", response_class=Response, include_in_schema=False)
# async def generate_rss_feed():
#     rss = Element("rss", attrib={
#         "version": "2.0",
#         "xmlns:itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
#     })

#     channel = SubElement(rss, "channel")
#     SubElement(channel, "title").text = "The InnerView Podcast"
#     SubElement(channel, "link").text = "https://instacast.live/"
#     SubElement(channel, "description").text = "Explore the essence of storytelling with 'The InnerView Podcast'. Delve into personal journeys, uncovering the raw and real experiences that shape us."
#     SubElement(channel, "itunes:author").text = "InstaCast AI"
#     # Spotify does not use this tag, but it's added for completeness
#     # Correctly adding the email address under the itunes:owner tag
#     itunes_owner = SubElement(channel, "itunes:owner")
#     SubElement(itunes_owner, "itunes:name").text = "Podcast Author"
#     SubElement(itunes_owner, "itunes:email").text = "ahmed@behairy.me"

#     # Cover art according to Spotify's specifications
#     itunes_image = SubElement(channel, "itunes:image")
#     itunes_image.set(
#         "href", "https://instacast.live/dashy-assets/images/innerview-thumbnail.png")

#     # Example podcast episode
#     item = SubElement(channel, "item")
#     SubElement(item, "title").text = "Episode 1: How One Call Changed His Life"
#     SubElement(
#         item, "itunes:summary").text = "Meet Ahmed Behairy, a software engineer that delved into digital health after recieving one call that changed his life "
#     SubElement(
#         item, "description").text = "<![CDATA[<p>Episode Description</p>]]>"
#     SubElement(item, "pubDate").text = datetime.utcnow().strftime(
#         "%a, %d %b %Y %H:%M:%S +0000")
#     guid = SubElement(item, "guid")
#     guid.set("isPermaLink", "false")
#     guid.text = "https://example.com/path/to/episode"
#     enclosure = SubElement(item, "enclosure")
#     enclosure.set(
#         "url", "https://instacast.live/api/podcast/file?session_id=73b1bde7-4653-49d6-984b-cd99a3d40993&uuid=final_compilation")
#     enclosure.set("type", "audio/mpeg")
#     enclosure.set("length", "123456")  # File size in bytes

#     rss_feed = tostring(rss, encoding="utf-8", method="xml")
#     return Response(content=rss_feed, media_type="application/rss+xml")
