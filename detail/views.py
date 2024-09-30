from django.shortcuts import redirect, render
from authentication.utils import get_single_anime_mal
from watch.utils import attach_episode_metadata, get_anime_data, get_seasons_by_zid

def index(request):
    return redirect("home:index")

def detail(request, anime_id):
    anime_data = get_anime_data(anime_id)
    anime_episodes = anime_data["episodes"]
    anime_episodes = attach_episode_metadata(anime_data, anime_episodes)

    if request.user.mal_access_token and "malId" in anime_data:
        mal_data = get_single_anime_mal(request.user.mal_access_token, anime_data["malId"])
    else:
        mal_data = None

    context = {
        "anime": anime_data,
        "episodes": anime_episodes,
        "related": anime_data.get("relations", []),
        "recommendations": anime_data.get("recommendations", []),
    }

    if mal_data:
        context["mal_data"] = mal_data
        context["mal_episode_range"] = range(1, mal_data["num_episodes"] + 1)

    if "nextAiringEpisode" in anime_data:
        context["nextAiringEpisode"] = anime_data["nextAiringEpisode"]

    return render(request, "detail/detail.html", context)
    
    
    # zid support is dropped



    # anime_data, provider, gd = get_anime_data(anime_id)
    # if not anime_data:
    #     return render(request, "detail/detail.html", {"error": "Anime not found"}, status=404)

    # anime_episodes = get_anime_episodes(anime_id)
    # if "message" in anime_episodes:
    #     anime_data, provider, gd = get_anime_data(anime_id, provider="gogo")
    #     anime_episodes, _ = get_anime_episodes_gogo(anime_id)
    
    # if anime_episodes:
    #     attach_episode_metadata(anime_data, anime_episodes)

    # if request.user.mal_access_token and anime_data.get("malId"):
    #     mal_data = get_single_anime_mal(request.user.mal_access_token, anime_data["malId"])
    # else:
    #     mal_data = None

    # context = {
    #     "anime": anime_data,
    #     "episodes": anime_episodes,
    #     "related": anime_data.get("relations", []),
    #     "recommendations": anime_data.get("recommendations", []),
    # }

    # zid = anime_data["episodes"][0]["id"].split("$")[0] if len(anime_data["episodes"]) > 0 else None
    # if zid and provider == "zoro":
    #     seasons = get_seasons_by_zid(zid)
    #     if seasons:
    #         context["seasons"] = seasons

    # if "nextAiringEpisode" in anime_data:
    #     context["nextAiringEpisode"] = anime_data["nextAiringEpisode"]

    # if mal_data:
    #     context["mal_data"] = mal_data
    #     context["mal_episode_range"] = range(1, mal_data["num_episodes"] + 1)

    # return render(request, "detail/detail.html", context)
