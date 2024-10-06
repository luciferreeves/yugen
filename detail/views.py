from django.shortcuts import redirect, render
from authentication.utils import get_single_anime_mal
from read.utils import get_manga_data
from watch.utils import attach_episode_metadata, get_anime_data, get_anime_seasons

def index(request):
    return redirect("home:index")

def anime(request, anime_id):
    anime_data = get_anime_data(anime_id, provider="zoro")

    if not anime_data:
        return redirect("home:index")

    if "status" in anime_data and anime_data["status"] != "Not yet aired":
        anime_episodes = anime_data["episodes"]
        anime_episodes = attach_episode_metadata(anime_data, anime_episodes)
    else:
        anime_episodes = []

    if request.user.mal_access_token and "malId" in anime_data:
        mal_data = get_single_anime_mal(request.user.mal_access_token, anime_data["malId"])
    else:
        mal_data = None

    seasons = get_anime_seasons(anime_id)
    context = {
        "anime": anime_data,
        "episodes": anime_episodes,
        "related": anime_data.get("relations", []),
        "recommendations": anime_data.get("recommendations", []),
        "seasons": seasons,
    }

    if mal_data:
        context["mal_data"] = mal_data
        context["mal_episode_range"] = range(1, mal_data["num_episodes"] + 1)

    if "nextAiringEpisode" in anime_data:
        context["nextAiringEpisode"] = anime_data["nextAiringEpisode"]

    return render(request, "detail/detail.html", context)

def manga(request, manga_id):
    manga_data = get_manga_data(manga_id)

    if not manga_data:
        return redirect("home:index")
    
    context = {
        "manga": manga_data,
        "related": manga_data.get("relations", []),
        "recommendations": manga_data.get("recommendations", []),
    }

    return render(request, "detail/manga.html", context)
