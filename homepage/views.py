from django.shortcuts import render
from homepage.utils import (
    get_trending_anime,
    get_popular_anime,
    get_top_anime,
    get_top_airing_anime,
    get_upcoming_anime,
)


def index(request):
    trending_anime = get_trending_anime()
    popular_anime = get_popular_anime()
    top_anime = get_top_anime()
    top_airing_anime = get_top_airing_anime()
    upcoming_anime = get_upcoming_anime()

    context = {
        "trending_anime": trending_anime["results"],
        "popular_anime": popular_anime["results"],
        "top_anime": top_anime["results"],
        "top_airing_anime": top_airing_anime["results"],
        "upcoming_anime": upcoming_anime["results"],
    }

    return render(request, "home/index.html", context)
