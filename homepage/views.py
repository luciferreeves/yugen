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

def index(request):
    homepage_data_cached = get_from_redis_cache("homepage_data")

    if not homepage_data_cached:
        trending_anime = get_trending_anime()
        popular_anime = get_popular_anime()
        top_anime = get_top_anime()
        top_airing_anime = get_top_airing_anime()
        upcoming_anime = get_upcoming_anime()
        next_season = get_next_season()

        homepage_data = {
            "trending_anime": trending_anime,
            "popular_anime": popular_anime,
            "top_anime": top_anime,
            "top_airing_anime": top_airing_anime,
            "upcoming_anime": upcoming_anime,
            "next_season": next_season
        }
        
        store_in_redis_cache("homepage_data", json.dumps(homepage_data))
    else:
        homepage_data = json.loads(homepage_data_cached)
        trending_anime = homepage_data["trending_anime"]
        popular_anime = homepage_data["popular_anime"]
        top_anime = homepage_data["top_anime"]
        top_airing_anime = homepage_data["top_airing_anime"]
        upcoming_anime = homepage_data["upcoming_anime"]
        next_season = homepage_data["next_season"]

    if request.user.preferences.show_history_on_home:
        user_history_data = gather_watch_history(request, limit=10)

    context = {
        "trending_anime": trending_anime["results"],
        "popular_anime": popular_anime["results"],
        "top_anime": top_anime["results"],
        "top_airing_anime": top_airing_anime["results"],
        "upcoming_anime": upcoming_anime["results"],
        "next_season": next_season,
        "user_history_data": user_history_data if request.user.preferences.show_history_on_home else None
    }

    return render(request, "home/index.html", context)

def gather_watch_history(request, limit=None):
    user = request.user
    
    with connection.cursor() as cursor:
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
        """
        if limit:
            query += " LIMIT %s"
            cursor.execute(query, [user.id, limit])
        else:
            cursor.execute(query, [user.id])
        
        columns = [col[0] for col in cursor.description]
        latest_history = [dict(zip(columns, row)) for row in cursor.fetchall()]

    user_history_data = []

    for history_entry in latest_history:
        anime_id = history_entry['anime_id']
        last_watched = history_entry['episode'] if history_entry['last_watched'] else 1

        anime_data = None
        try:
            anime_data = json.loads(get_from_redis_cache(f"anime_{anime_id}_anime_data"))
        except:
            base_url = f"{os.getenv('CONSUMET_URL')}/meta/anilist/info/{anime_id}?provider=zoro"
            response = requests.get(base_url)
            anime_data = response.json()
            store_in_redis_cache(f"anime_{anime_id}_anime_data", json.dumps(anime_data))

        # attach metadata to episodes
        episode_metadata = get_episode_metadata(anime_data, last_watched)

        user_history_data.append({
            "anime_id": anime_id,
            "title": anime_data["title"],
            "cover": anime_data["cover"],
            "episode": last_watched,
            "metadata": episode_metadata
        })

    return user_history_data


def search_json(request):
    query = request.GET.get("q")

    base_url = f"{os.getenv("CONSUMET_URL")}/meta/anilist/advanced-search?query={query}&page=1&perPage=5&type=ANIME"
    response = requests.get(base_url)
    search_results = response.json()

    return JsonResponse(search_results)
