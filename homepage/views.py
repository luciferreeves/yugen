import os
from django.http import JsonResponse
from django.shortcuts import render
import requests
from watch.utils import get_from_redis_cache, store_in_redis_cache
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
        print("fetching homepage data from api")
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

    context = {
        "trending_anime": trending_anime["results"],
        "popular_anime": popular_anime["results"],
        "top_anime": top_anime["results"],
        "top_airing_anime": top_airing_anime["results"],
        "upcoming_anime": upcoming_anime["results"],
        "next_season": next_season
    }

    return render(request, "home/index.html", context)

def search_json(request):
    query = request.GET.get("q")

    base_url = f"{os.getenv("CONSUMET_URL")}/meta/anilist/advanced-search?query={query}&page=1&perPage=5&type=ANIME"
    response = requests.get(base_url)
    search_results = response.json()

    return JsonResponse(search_results)
