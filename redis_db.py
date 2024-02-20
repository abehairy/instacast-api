import redis
import json
from typing import List

# Initialize Redis client
redis_client = redis.Redis(host='localhost', port=6379,
                           db=0, decode_responses=True)


def get_episode_metadata_by_key(key: str):
    # Retrieve metadata from Redis using the constructed key
    metadata = redis_client.get(key)
    if metadata:
        # Parse the metadata from a JSON string to a Python dictionary
        return json.loads(metadata)
    return None


def get_episode_metadata(podcast_id: str, episode_id: str):
    """
    Retrieve episode metadata from Redis using a key composed of the podcast_slug
    and the episode_id.
    """
    # Construct the key using the podcast_id and episode_id
    key = f"{podcast_id}-{episode_id}"

    # Retrieve metadata from Redis using the constructed key
    metadata = redis_client.get(key)
    if metadata:
        # Parse the metadata from a JSON string to a Python dictionary
        return json.loads(metadata)
    return None


def save_episode_metadata(podcast_id: str, episode_id: str, title: str, user: str, email: str, photo: str = None):
    """
    Save episode metadata in Redis.

    Args:
        podcast_id (str): The ID of the podcast.
        episode_id (str): The ID of the episode.
        title (str): The title of the episode.
        user (str): The user associated with the episode.
        email (str): The email of the user.
    """
    # Construct the key using the podcast_slug and episode_id
    key = f"{podcast_id}-{episode_id}"

    # Create a dictionary for the episode metadata
    metadata = {
        "title": title,
        "user": user,
        "email": email,
        "photo": photo
    }

    # Serialize the metadata dictionary to a JSON string
    metadata_json = json.dumps(metadata)

    # Save the serialized metadata to Redis using the constructed key
    redis_client.set(key, metadata_json)


def find_keys_by_pattern(pattern: str) -> List[str]:
    "Find all keys matching the pattern"
    cursor = '0'
    keys = []
    while cursor != 0:
        cursor, matches = redis_client.scan(
            cursor=cursor, match=pattern, count=100)
        keys.extend(matches)
    return keys
