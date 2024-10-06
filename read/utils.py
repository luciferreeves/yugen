import json
import os
import requests
from functools import lru_cache
from watch.utils import get_from_redis_cache, store_in_redis_cache

@lru_cache(maxsize=128)
def get_manga_info(manga_id):
    base_url = f"{os.getenv('CONSUMET_URL')}/meta/anilist-manga/info/{manga_id}"
    print(f"Trying URL: {base_url}")
    response = requests.get(base_url, timeout=10)
    manga_data = response.json()

    if "message" in manga_data:
        return None
    else:
        mangadex_id = fetch_mangadex_id(manga_data['title']['romaji'])
        print(f"Mangadex ID: {mangadex_id}")
        if mangadex_id:
            manga_data["mangadex_id"] = mangadex_id
            manga_data["chapters"] = fetch_mangadex_chapters(mangadex_id)
        else:
            manga_data["mangadex_id"] = None
    
    return manga_data

@lru_cache(maxsize=128)
def fetch_mangadex_id(title):
    url = "https://api.mangadex.org/manga"
    params = {
        "title": title,
        "limit": 1,
        "order[relevance]": "desc",
        "includes[]": ["cover_art"],
        "contentRating[]": ["safe", "suggestive", "erotica", "pornographic"],
        "hasAvailableChapters": "true"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data["data"]:
            return data["data"][0]["id"]
    print(response.json())
    return None

@lru_cache(maxsize=128)
def fetch_mangadex_chapters(mangadex_id):
    url = f"https://api.mangadex.org/manga/{mangadex_id}/feed"
    params = {
        "translatedLanguage[]": ["en"],
        "order[chapter]": "asc",
        "limit": 500,
        "offset": 0
    }
    all_chapters = []
    total = float('inf')

    while len(all_chapters) < total:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"Error fetching chapters: {response.status_code}")
            print(response.json())
            return None

        data = response.json()
        total = data['total']
        all_chapters.extend(data['data'])
        params['offset'] += params['limit']

        if len(data['data']) < params['limit']:
            break

    filtered_chapters = []
    seen_chapters = set()

    for chapter in all_chapters:
        if chapter["type"] == "chapter":
            attributes = chapter["attributes"]
            chapter_number = attributes.get("chapter")
            pages = attributes.get("pages", 0)

            if pages == 0:
                continue

            seen_chapters.add(chapter_number)
            filtered_chapters.append(chapter)

    return filtered_chapters

def get_manga_data(manga_id):
    print(f"Fetching manga data: ID={manga_id}")
    cache_key = f"manga_{manga_id}_manga_data"
    manga_data = get_from_redis_cache(cache_key)

    if not manga_data:
        manga_data = get_manga_info(manga_id)
        
        if manga_data and "status" in manga_data and manga_data["status"] == "Completed":
            store_in_redis_cache(cache_key, json.dumps(manga_data), 3600 * 24 * 30)
        elif manga_data:
            store_in_redis_cache(cache_key, json.dumps(manga_data), 3600 * 24)
    else:
        manga_data = json.loads(manga_data)

    return manga_data

@lru_cache(maxsize=128)
def get_chapter_pages(chapter_id):
    url = f"https://api.mangadex.org/at-home/server/{chapter_id}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch data for chapter {chapter_id}")
        return None

    chapter_data = response.json()
    base_url = chapter_data['baseUrl']
    chapter_hash = chapter_data['chapter']['hash']
    data = chapter_data['chapter']['data']

    return [{"page": i + 1, "img": f"{base_url}/data/{chapter_hash}/{page}"} for i, page in enumerate(data)]