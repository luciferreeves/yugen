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
from functools import lru_cache
from user_profile.models import UserHistory

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
        context["user_history_data"] = gather_watch_history(request.user)

    return render(request, "home/index.html", context)


def search(request):
    return render(request, "home/search.html")


def gather_watch_history(user, limit=None):
    history = UserHistory.objects.filter(user=user, last_watched=True).order_by("-last_updated")
    if limit:
        history = history[:limit]

    return history


def search_json(request):
    query = request.GET.get("q")

    base_url = f"{os.getenv("CONSUMET_URL")}/meta/anilist/advanced-search?query={query}&page=1&perPage=5&type=ANIME"
    response = requests.get(base_url)
    search_results = response.json()

    return JsonResponse(search_results)
