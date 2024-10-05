from django.http import JsonResponse
from django.urls import reverse
import dotenv
from django.shortcuts import render, redirect
from authentication.utils import get_single_anime_mal
from user_profile.models import UserHistory
from watch.utils import attach_episode_metadata, get_anime_seasons, get_anime_data, get_anime_user_history, get_gogo_episode_streaming_data, get_zoro_episode_streaming_data, update_anime_user_history, get_mal_episode_comments
import json

dotenv.load_dotenv()

def index(request):
    return redirect("home:index")

def watch(request, anime_id, episode=None):
    forward_detail = request.GET.get("forward") == "detail"
    preload_request = request.GET.get("preload") == "true" 

    if not episode and request.user.preferences.default_watch_page == "detail" and not forward_detail:
        return redirect("detail:anime", anime_id=anime_id)
    
    provider = "gogo" if request.user.preferences.default_provider == "gogoanime" else "zoro"
    provider = request.GET.get("provider", provider)

    history = get_anime_user_history(request.user, anime=anime_id)
    current_watched_time = [h.time_watched for h in history if h.episode == episode]
    current_watched_time = current_watched_time[0] if current_watched_time else 0
    
    if not episode or episode < 0:
        episode = [h.episode for h in history if h.last_watched]
        print(episode)
        episode = episode[0] if episode else 1
        return redirect("watch:watch_episode", anime_id=anime_id, episode=episode)
    
    mode = request.GET.get("mode", request.user.preferences.default_language)
    dub = True if mode == "dub" else False
    anime_data = get_anime_data(anime_id, provider=provider, dub=dub)

    if not anime_data:
        return redirect("detail:anime", anime_id=anime_id)

    if anime_data and "status" in anime_data and anime_data["status"] == "Not yet aired":
        return redirect("detail:anime", anime_id=anime_id)
    
    episodes = anime_data["episodes"]
    if len(episodes) == 0:
        if provider == "zoro" and mode == "dub":
            return redirect(reverse("watch:watch_episode", args=[anime_id, 1]) + "?provider=zoro&mode=sub")
        if provider == "zoro" and mode == "sub":
            return redirect(reverse("watch:watch_episode", args=[anime_id, 1]) + "?provider=gogo")
        if provider == "gogo" and mode == "dub":
            return redirect(reverse("watch:watch_episode", args=[anime_id, 1]) + "?provider=gogo&mode=sub")

    episodes = attach_episode_metadata(anime_data, episodes)
    episode_data = next((ep for ep in episodes if ep['number'] == int(episode)), None)
    if not preload_request and episode_data:
        additional_data = {
            "anime_title_english": anime_data["title"]["english"] if "title" in anime_data and "english" in anime_data["title"] else "",
            "anime_title_romaji": anime_data["title"]["romaji"] if "title" in anime_data and "romaji" in anime_data["title"] else "",
            "anime_title_native": anime_data["title"]["native"] if "title" in anime_data and "native" in anime_data["title"] else "",
            "anime_cover_image": episode_data.get("metadata", {}).get("image") if episode_data and episode_data.get("metadata") else anime_data.get("cover", ""),
            "episode_title": episode_data.get("metadata", {}).get("title") if episode_data and episode_data.get("metadata") else episode_data.get("title", ""),
        }

        if not additional_data["episode_title"]:
            additional_data["episode_title"] = f"Episode {episode}"

        update_anime_user_history(request.user, anime_id, episode, current_watched_time, additional_data)

    if "malId" in anime_data and request.user.mal_access_token:
        comments = get_mal_episode_comments(anime_data['malId'], episode, request.user.mal_access_token)
    else:
        comments = []

    if episode_data:
        if provider == "zoro":
            streaming_data = get_zoro_episode_streaming_data(episode_data["id"], mode)
        else:
            streaming_data = get_gogo_episode_streaming_data(episode_data["id"])

        if preload_request:
            return JsonResponse({"status": f"Preloaded episode {episode}"})

        stream_url = streaming_data["sources"][0]["url"] if streaming_data and "sources" in streaming_data else None
    else:
        episode_data = {
            "number": 0,
        }
        streaming_data = None
        stream_url = ""

    seasons = get_anime_seasons(anime_id)

    context = {
        "anime": anime_data,
        "animeID": anime_id,
        "current_episode_number": episode if episode_data else 0,
        "current_episode": episode_data,
        "all_episodes": episodes,
        "characters": anime_data.get("characters", []),
        "recommendations": anime_data.get("recommendations", []),
        "related": anime_data.get("relations", []),
        "streaming_data": streaming_data,
        "stream_url": stream_url,
        "mode": mode,
        "watched_episodes": [h.episode for h in history],
        "current_watched_time": current_watched_time,
        "provider": provider,
        "seasons": seasons,
        "should_preload": episode < len(episodes),
        "discussions": comments,
    }

    if request.user.mal_access_token and "malId" in anime_data:
        mal_data = get_single_anime_mal(request.user.mal_access_token, anime_data["malId"])
        if mal_data:
            mal_data["average_episode_duration"] = mal_data["average_episode_duration"] // 60 + 1
            context["mal_data"] = mal_data
            context["mal_episode_range"] = range(1, mal_data["num_episodes"] + 1)
            

    if "nextAiringEpisode" in anime_data:
        context["nextAiringEpisode"] = anime_data["nextAiringEpisode"]

    return render(request, "watch/watch.html", context)   


def update_episode_watch_time(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request"})

    data = json.loads(request.body)
    anime =data.get("anime")
    episode =data.get("episode")
    time_watched =data.get("time_watched")

    if request.user.is_authenticated:
        anime = int(anime)
        episode = int(episode)
        update_anime_user_history(request.user, anime, episode, time_watched)
        return JsonResponse({"status": "success"})
    else:
        return JsonResponse({"status": "error", "message": "User not authenticated"})

def remove_anime_from_watchlist(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request"})

    data = json.loads(request.body)
    anime_id = data.get("anime_id")

    if request.user.is_authenticated:
        history = UserHistory.objects.filter(user=request.user, anime=anime_id)
        history.delete()
        return JsonResponse({"status": "success"})
    else:
        return JsonResponse({"status": "error", "message": "User not authenticated"})
