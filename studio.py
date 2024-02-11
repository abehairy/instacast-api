from pydub import AudioSegment
import requests
import asyncio
import os
import aiohttp
import json
openai_api_key = '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'


def compile_audio_with_intro(podcast_id):
    folder_path = f'audio_files/{podcast_id}'
    output_file = f'{folder_path}/final_compilation.mp3'
    background_music_path = 'audio_files/intro_background.mp3'  # Adjust as necessary
    # List audio files sorted by creation date
    audio_files = [os.path.join(folder_path, f)
                   for f in os.listdir(folder_path) if f.endswith('.mp3') or f.endswith('.webm')]
    audio_files.sort(key=lambda x: os.path.getctime(x))

    # Load the background music and reduce its volume
    background_music = AudioSegment.from_file(background_music_path) - 5

    # Adjust the background music length and apply fade effects for the intro
    fade_duration = 5000  # 5 seconds for fade-in and fade-out
    intro_duration = 10000  # 10 seconds of intro music
    background_music = background_music[:intro_duration].fade_in(
        fade_duration).fade_out(fade_duration)

    # Initialize an empty audio segment for compilation
    compiled_audio = background_music

    # Load each audio file and append to the compilation
    for file in audio_files:
        voice_clip = AudioSegment.from_file(file)
        compiled_audio += voice_clip

    # Export the compiled audio file
    compiled_audio.export(output_file, format='mp3')

    print(f"Compilation complete. File saved as: {output_file}")


async def make_intro(intro_text, podcast_id, voice='alloy'):
    intro_voice = await generate_speech(
        intro_text, voice)
    # Load the audio files
    print(intro_voice)
    voice_clip = AudioSegment.from_file(intro_voice)
    print(voice_clip)
    background_music = AudioSegment.from_file(
        "audio_files/intro_background.mp3")

    # Reduce the volume of the background music
    background_music = background_music - 10  # Decrease volume by 20 dB

    # Make the background music match the length of the voice clip
    if len(background_music) > len(voice_clip):
        background_music = background_music[:len(voice_clip)]
    else:
        # Loop the background music if it's shorter than the voice clip
        background_music = background_music * \
            (len(voice_clip) // len(background_music) + 1)
        background_music = background_music[:len(voice_clip)]

    # Apply fade-in and fade-out effects to the background music
    fade_duration = 5000  # 5 seconds
    background_music = background_music.fade_in(
        fade_duration).fade_out(fade_duration)

    # Mix the voice clip with the background music
    mixed_clip = voice_clip.overlay(background_music)

    # Export the mixed audio file
    mixed_clip.export(
        f"audio_files/{podcast_id}/intro.mp3", format="mp3")


async def transcribe_audio(audio_file_path, model='whisper-1'):
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
    }
    from aiohttp import FormData

    data = FormData()
    data.add_field('file',
                   open(audio_file_path, 'rb'),
                   filename=audio_file_path,
                   content_type='audio/webm')
    data.add_field('model', model)

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=data) as response:
            if response.status == 200:
                result = await response.json()
                print(f"Transcription: {result['text']}")
                return result['text']
            else:
                print(f"Failed to transcribe audio. Status code: {response.status} - Response: {await response.text()}")
                return None


async def generate_speech(text, voice='alloy', output_file='audio_files/output.mp3'):
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json",
    }

    data = {
        "model": "tts-1",
        "input": text or "Today is a wonderful day to build something people love!",
        "voice": voice,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post("https://api.openai.com/v1/audio/speech", headers=headers, data=json.dumps(data)) as response:
            if response.status == 200:
                # Assuming the response content is the audio file
                with open(output_file, 'wb') as audio_file:
                    audio_file.write(await response.read())
                print(f"Audio file saved as {output_file}")
                return output_file
            else:
                print(f"Failed to generate speech. Status code: {response.status} - Response: {await response.text()}")

# To run the async function outside of an async environment
if __name__ == "__main__":
    # Replace with your folder path
    podcast_id = '51c13bd2-73af-4f37-96c5-e62fcc3afedf'
    compile_audio_with_intro(podcast_id)
