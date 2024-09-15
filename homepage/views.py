import os
from django.http import JsonResponse
from django.shortcuts import render
import requests
from datetime import datetime
from watch.utils import get_from_redis_cache, store_in_redis_cache
import json
from homepage.utils import (
    find_target_anime,
    get_anime_schedule,
    get_start_end_times,
    get_trending_anime,
    get_popular_anime,
    get_top_anime,
    get_top_airing_anime,
    get_upcoming_anime,
    get_next_season,
    group_anime_schedules,
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
        context["user_history_data"] = gather_watch_history(request.user, 10)

    return render(request, "home/index.html", context)


def search(request):
    q = request.GET.get("q")
    page = request.GET.get("page", 1)
    sort = request.GET.get("sort")
    status = request.GET.get("status")
    season = request.GET.get("season")
    year = request.GET.get("year")
    genres = request.GET.get("genres")
    type = request.GET.get("type")
    per_page = 48

    base_url = f"{os.getenv("CONSUMET_URL")}/meta/anilist/advanced-search?page={page}&perPage={per_page}&type=ANIME"
    if q:
        base_url += f"&query={q}"
    if sort:
        base_url += f"&sort={sort}"
    if status:
        base_url += f"&status={status}"
    if season:
        base_url += f"&season={season}"
    if year:
        base_url += f"&year={year}"
    if genres:
        base_url += f"&genres={genres}"
    if type:
        base_url += f"&format={type}"

    response = requests.get(base_url)
    search_results = response.json()
    
    years = list(range(1940, datetime.now().year + 1))[::-1]

    context = {
        "results": search_results["results"] if "results" in search_results else [],
        "page": search_results["currentPage"] if "currentPage" in search_results else 1,
        "total_pages": search_results["totalPages"] if "totalPages" in search_results else 1,
        "has_next": search_results["hasNextPage"] if "hasNextPage" in search_results else False,
        "total_results": search_results["totalResults"] if "totalResults" in search_results else 0,
        "q": q if q else "",
        "sort": sort,
        "years": years,
        "year": year,
        "season": season,
        "status": status,
        "genres": genres,
        "type": type,
    }

    return render(request, "home/search.html", context)


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

def watchlist(request):
    watchlist = gather_watch_history(request.user)

    context = {
        "watchlist": watchlist,
    }

    return render(request, "home/watchlist.html", context)

def schedule(request):
    start = request.GET.get("start")
    end = request.GET.get("end")

    times = get_start_end_times()
    today = times[
        next(
            (
                index
                for index, time in enumerate(times)
                if time["today"]
            ),
            None,
        )
    ]

    schedule_data = get_anime_schedule(today["start"], today["end"])
    grouped_schedule_data = group_anime_schedules(schedule_data)
    target, last_two = find_target_anime(grouped_schedule_data)

    if start and end:
        today = next(
            (
                time
                for time in times
                if time["start"] == int(start) and time["end"] == int(end)
            ),
            None,
        )

        if today:
            schedule_data = get_anime_schedule(today["start"], today["end"])
            grouped_schedule_data = group_anime_schedules(schedule_data)

            # change today in times
            for time in times:
                time["today"] = False
            today["today"] = True
    else:
        start = today["start"]
        end = today["end"]

    context = {
        "schedule": grouped_schedule_data,
        "next_airing": target,
        "recently_aired": last_two,
        "times": times,
        "start": start,
        "end": end,
    }

    return render(request, "home/schedule.html", context)
