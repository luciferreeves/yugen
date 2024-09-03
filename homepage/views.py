import os
from django.http import JsonResponse
from django.shortcuts import render
from django.db import connection
import requests
from watch.utils import get_from_redis_cache, store_in_redis_cache, get_episode_metadata
import json
from homepage.utils import (
    get_trending_anime,
    get_popular_anime,
    get_top_anime,
    get_top_airing_anime,
    get_upcoming_anime,
    get_next_season,
)
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

@lru_cache(maxsize=1)
def get_homepage_data():
    homepage_data = get_from_redis_cache("homepage_data")
    
    if not homepage_data:
        homepage_data = {
            "trending_anime": get_trending_anime(),
            "popular_anime": get_popular_anime(),
            "top_anime": get_top_anime(),
            "top_airing_anime": get_top_airing_anime(),
            "upcoming_anime": get_upcoming_anime(),
            "next_season": get_next_season()
        }
        store_in_redis_cache("homepage_data", json.dumps(homepage_data), 3600)  # Cache for 1 hour
    else:
        homepage_data = json.loads(homepage_data)
    
    return homepage_data

def index(request):
    homepage_data = get_homepage_data()
    
    context = {
        "trending_anime": homepage_data["trending_anime"]["results"],
        "popular_anime": homepage_data["popular_anime"]["results"],
        "top_anime": homepage_data["top_anime"]["results"],
        "top_airing_anime": homepage_data["top_airing_anime"]["results"],
        "upcoming_anime": homepage_data["upcoming_anime"]["results"],
        "next_season": homepage_data["next_season"],
    }

    if request.user.preferences.show_history_on_home:
        context["user_history_data"] = gather_watch_history(request)

    return render(request, "home/index.html", context)

def gather_watch_history(request, limit=10):
    user = request.user
    latest_history = get_user_watch_history(user.id, limit)
    anime_ids = [entry['anime_id'] for entry in latest_history]
    anime_data_map = get_bulk_anime_data(anime_ids)

    return [
        {
            "anime_id": entry['anime_id'],
            "title": anime_data_map[entry['anime_id']]["title"],
            "cover": anime_data_map[entry['anime_id']]["cover"],
            "episode": entry['episode'] if entry['last_watched'] else 1,
            "metadata": get_episode_metadata(anime_data_map[entry['anime_id']], entry['episode'] if entry['last_watched'] else 1)
        }
        for entry in latest_history
    ]

@lru_cache(maxsize=100)
def get_user_watch_history(user_id, limit):
    query = """
        WITH ranked_history AS (
            SELECT 
                id, 
                anime_id, 
                episode, 
                last_watched, 
                last_updated,
                ROW_NUMBER() OVER (PARTITION BY anime_id ORDER BY last_updated DESC) AS rn
            FROM user_profile_userhistory
            WHERE user_id = %s
        )
        SELECT id, anime_id, episode, last_watched, last_updated
        FROM ranked_history
        WHERE rn = 1
        ORDER BY last_updated DESC
        LIMIT %s
    """
    
    with connection.cursor() as cursor:
        cursor.execute(query, [user_id, limit])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def get_bulk_anime_data(anime_ids):
    anime_data_map = {}
    missing_ids = []

    # Check cache first (including potential caches from other functions)
    for anime_id in anime_ids:
        cached_data = get_cached_anime_data(anime_id)
        if cached_data:
            anime_data_map[anime_id] = cached_data
        else:
            missing_ids.append(anime_id)

    # Fetch missing data in parallel
    if missing_ids:
        with ThreadPoolExecutor(max_workers=min(10, len(missing_ids))) as executor:
            future_to_id = {executor.submit(fetch_anime_data, anime_id): anime_id for anime_id in missing_ids}
            for future in as_completed(future_to_id):
                anime_id = future_to_id[future]
                try:
                    data = future.result()
                    anime_data_map[anime_id] = data
                    store_in_redis_cache(f"anime_{anime_id}_anime_data", json.dumps(data), 86400)  # Cache for 24 hours
                except Exception as exc:
                    print(f"Anime ID {anime_id} generated an exception: {exc}")

    return anime_data_map

def get_cached_anime_data(anime_id):
    cache_keys = [
        f"anime_{anime_id}_anime_data",
        f"anime_{anime_id}_details",  # Example of a cache key that might be used by another function
        f"anime_info_{anime_id}"      # Another example
    ]
    
    for key in cache_keys:
        cached_data = get_from_redis_cache(key)
        if cached_data:
            return json.loads(cached_data)
    
    return None

@lru_cache(maxsize=1000)
def fetch_anime_data(anime_id):
    base_url = f"{os.getenv('CONSUMET_URL')}/meta/anilist/info/{anime_id}?provider=zoro"
    try:
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching data for anime ID {anime_id}: {e}")
        return None


def search_json(request):
    query = request.GET.get("q")

    base_url = f"{os.getenv("CONSUMET_URL")}/meta/anilist/advanced-search?query={query}&page=1&perPage=5&type=ANIME"
    response = requests.get(base_url)
    search_results = response.json()

    return JsonResponse(search_results)
