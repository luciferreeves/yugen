import os
from django.http import JsonResponse
from django.shortcuts import render
import requests
from homepage.utils import (
    get_trending_anime,
    get_popular_anime,
    get_top_anime,
    get_top_airing_anime,
    get_upcoming_anime,
    get_next_season,
)


def index(request):
    trending_anime = get_trending_anime()
    popular_anime = get_popular_anime()
    top_anime = get_top_anime()
    top_airing_anime = get_top_airing_anime()
    upcoming_anime = get_upcoming_anime()
    next_season = get_next_season()

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
