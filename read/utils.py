import base64
import json
import os

import requests
from watch.utils import get_from_redis_cache, store_in_redis_cache

def encode_chapter_info(provider, chapter_id):
    data = json.dumps({"p": provider, "id": chapter_id})
    return base64.urlsafe_b64encode(data.encode()).rstrip(b'=').decode()

def decode_chapter_info(encoded_info):
    padding = 4 - (len(encoded_info) % 4)
    encoded_info += "=" * padding
    data = json.loads(base64.urlsafe_b64decode(encoded_info).decode())
    return data["p"], data["id"]

def process_mangareader_chapters(manga_data):
    manga_data["chapters"] = list(filter(lambda x: "/en/" in x["id"], manga_data["chapters"]))
    for chapter in manga_data["chapters"]:
        chapter["encoded_id"] = encode_chapter_info("mangareader", chapter["id"])
    return manga_data

def process_generic_chapters(manga_data):
    for chapter in manga_data["chapters"]:
        chapter["encoded_id"] = encode_chapter_info("generic", chapter["id"])
    return manga_data

def get_data_from_managareader(manga_id):
    base_url = f"{os.getenv('CONSUMET_URL')}/meta/anilist-manga/info/{manga_id}?provider=mangareader"
    print(f"Trying URL: {base_url}")
    response = requests.get(base_url, timeout=10)
    manga_data = response.json()

    if "message" in manga_data:
        return None
    else:
        manga_data = process_mangareader_chapters(manga_data)
    
    return manga_data

def get_data_from_generic(manga_id):
    base_url = f"{os.getenv('CONSUMET_URL')}/meta/anilist-manga/info/{manga_id}"
    print(f"Trying URL: {base_url}")
    response = requests.get(base_url, timeout=10)
    manga_data = response.json()

    if "message" in manga_data:
        return None
    else:
        manga_data = process_generic_chapters(manga_data)
    
    return manga_data

def get_manga_data(manga_id):
    print(f"Fetching manga data: ID={manga_id}")

    cache_key = f"manga_{manga_id}_manga_data"
    manga_data = get_from_redis_cache(cache_key)
    generic_only_ids = [30013]
    provider = "generic" if manga_id in generic_only_ids else "mangareader"

    if not manga_data:
        manga_data = None
        if provider == "mangareader":
            manga_data = get_data_from_managareader(manga_id)

        if not manga_data or provider == "generic":
            manga_data = get_data_from_generic(manga_id)
        
        if "status" in manga_data and manga_data["status"] == "Completed":
            store_in_redis_cache(cache_key, json.dumps(manga_data), 3600 * 24 * 30)
        else:
            store_in_redis_cache(cache_key, json.dumps(manga_data), 3600 * 24)
    else:
        manga_data = json.loads(manga_data)

    return manga_data

def get_chapter_pages(provider, chapter_id):
    base_url = f"{os.getenv('CONSUMET_URL')}/meta/anilist-manga/read?chapterId={chapter_id}"
    if provider == "mangareader":
        base_url += "&provider=mangareader"
    print(f"Trying URL: {base_url}")

    response = requests.get(base_url, timeout=10)
    return response.json() if response.status_code == 200 else None

