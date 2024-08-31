import os
from django.http import JsonResponse
import dotenv
from django.shortcuts import render, redirect
from watch.utils import update_anime_user_history, get_anime_user_history
import requests
import json

dotenv.load_dotenv()

def watch(request, anime_id, episode=None):
    if not episode or episode < 1:
        return redirect("watch:watch_episode", anime_id=anime_id, episode=1)

    mode = request.GET.get("mode", request.user.preferences.default_language)

    base_url = f"{os.getenv("CONSUMET_URL")}/meta/anilist/data/{anime_id}?provider=zoro"
    response = requests.get(base_url)
    anime_data = response.json()

    base_url = f"{os.getenv("ZORO_URL")}/anime/search?q={anime_data["title"]["english"]}&page=1"
    response = requests.get(base_url)
    anime_search_result = response.json()
    anime_selected = [a for a in anime_search_result["animes"] if a["name"].lower() == anime_data["title"]["english"].lower()]

    if not anime_selected:
        anime_selected = anime_search_result["animes"][0]
    else:
        anime_selected = anime_selected[0]

    base_url = f"{os.getenv("ZORO_URL")}/anime/episodes/{anime_selected["id"]}"
    response = requests.get(base_url)
    anime_episodes = response.json()

    if mode == "dub" and not anime_selected["episodes"]["dub"]:
        mode = "sub"

    if not anime_selected["episodes"][mode] or anime_selected["episodes"][mode] < episode:
        mode = "sub"

    if episode > anime_episodes["totalEpisodes"]:
            return redirect("watch:watch_episode", anime_id=anime_id, episode=anime_episodes["totalEpisodes"])
        
    episode_d = [e for e in anime_episodes["episodes"] if e["number"] == episode][0]

    base_url = f"{os.getenv("ZORO_URL")}/anime/episode-srcs?id={episode_d["episodeId"]}?server&category={mode}"
    response = requests.get(base_url)
    episode_data = response.json()

    if "message" in episode_data and episode_data["message"] == "Couldn't find server. Try another server":
        base_url = f"{os.getenv("ZORO_URL")}/anime/episode-srcs?id={episode_d["episodeId"]}?server=hd-2&category={mode}"
        response = requests.get(base_url)
        episode_data = response.json()

    current_episode_name = [e["title"] for e in anime_episodes["episodes"] if e["number"] == episode][0]

    # store anime history
    if request.user.is_authenticated:
        anime_history = get_anime_user_history(request.user, anime_id)

        # if current episode is not in history, add it
        if not any(h.episode == episode for h in anime_history):
            update_anime_user_history(request.user, anime_id, episode, 0)

        watched_episodes = [h.episode for h in anime_history]
        current_watched_time = [h.time_watched for h in anime_history if h.episode == episode][0]
    else:
        anime_history = None
        watched_episodes = []
        current_watched_time = 0

    context = {
        "anime_data": anime_data,
        "anime_selected": anime_selected,
        "anime_episodes": anime_episodes,
        "episode_data": episode_data,
        "current_episode": episode,
        "stream_url": episode_data["sources"][0]["url"],
        "anime_id": anime_id,
        "current_episode_name": current_episode_name,
        "anime_history": anime_history,
        "watched_episodes": watched_episodes,
        "current_watched_time": current_watched_time,
        "mode": mode,
    }

    print(context)

    return render(request, "watch/watch.html", context)

def update_episode_watch_time(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request"})

    data = json.loads(request.body)
    anime_id =data.get("anime_id")
    episode =data.get("episode")
    time_watched =data.get("time_watched")

    if request.user.is_authenticated:
        update_anime_user_history(request.user, anime_id, episode, time_watched)
        return JsonResponse({"status": "success"})
    else:
        return JsonResponse({"status": "error", "message": "User not authenticated"})
