import os
from django.http import JsonResponse
import dotenv
from django.shortcuts import render, redirect
from watch.utils import update_anime_user_history, get_anime_user_history, get_from_redis_cache, store_in_redis_cache
import requests
import json

dotenv.load_dotenv()

def watch(request, anime_id, episode=None):
    anime_history = get_anime_user_history(request.user, anime_id)

    watched_episodes = [h.episode for h in anime_history]
    current_watched_time = [h.time_watched for h in anime_history if h.episode == episode]
    current_watched_time = current_watched_time[0] if current_watched_time else 0

    if not episode or episode < 1:
        episode = [h.episode for h in anime_history if h.last_watched]
        episode = episode[0] if episode else 1
        return redirect("watch:watch_episode", anime_id=anime_id, episode=episode)

    mode = request.GET.get("mode", request.user.preferences.default_language)

    anime_data_cached = get_from_redis_cache(f"anime_{anime_id}_anime_data")
    anime_selected_cached = get_from_redis_cache(f"anime_{anime_id}_anime_selected")
    anime_episodes_cached = get_from_redis_cache(f"anime_{anime_id}_anime_episodes")

    if not anime_data_cached:
        base_url = f"{os.getenv("CONSUMET_URL")}/meta/anilist/info/{anime_id}?provider=zoro"
        response = requests.get(base_url)
        anime_data = response.json()
        store_in_redis_cache(f"anime_{anime_id}_anime_data", json.dumps(anime_data))
    else:
        anime_data = json.loads(anime_data_cached)

    if not anime_selected_cached:
        z_anime_id = anime_data["episodes"][0]["id"].split("$")[0]
        base_url = f"{os.getenv("ZORO_URL")}/anime/info?id={z_anime_id}"
        response = requests.get(base_url)
        anime_selected = response.json()
        store_in_redis_cache(f"anime_{anime_id}_anime_selected", json.dumps(anime_selected))
    else:
        anime_selected = json.loads(anime_selected_cached)

    if not anime_episodes_cached:
        base_url = f"{os.getenv("ZORO_URL")}/anime/episodes/{anime_selected["anime"]["info"]["id"]}"
        response = requests.get(base_url)
        anime_episodes = response.json()
        store_in_redis_cache(f"anime_{anime_id}_anime_episodes", json.dumps(anime_episodes))

    if not anime_selected["anime"]["info"]["stats"]["episodes"][mode] or anime_selected["anime"]["info"]["stats"]["episodes"][mode] < episode:
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

    # if no captions are present and the mode is dub, and ingrain_sub_subtitles_in_dub is true, then fetch the sub track
    if not any(t["kind"] == "captions" for t in episode_data["tracks"]) and mode == "dub" and request.user.preferences.ingrain_sub_subtitles_in_dub:
        base_url = f"{os.getenv("ZORO_URL")}/anime/episode-srcs?id={episode_d["episodeId"]}?server&category=sub"
        response = requests.get(base_url).json()
        captions = [t for t in response["tracks"] if t["kind"] == "captions"]
        if captions:
            episode_data["tracks"].extend(captions)

    current_episode_name = [e["title"] for e in anime_episodes["episodes"] if e["number"] == episode][0]
   
    update_anime_user_history(request.user, anime_id, episode, current_watched_time)

    current_episode_data = [e for e in anime_episodes["episodes"] if e["number"] == episode][0]

    context = {
        "anime_data": anime_data,
        "anime_selected": anime_selected,
        "anime_episodes": anime_episodes,
        "episode_data": episode_data,
        "current_episode": episode,
        "current_episode_data": current_episode_data,
        "stream_url": episode_data["sources"][0]["url"],
        "anime_id": anime_id,
        "current_episode_name": current_episode_name,
        "anime_history": anime_history,
        "watched_episodes": watched_episodes,
        "current_watched_time": current_watched_time,
        "mode": mode,
    }

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
