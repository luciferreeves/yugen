import os
from django.http import JsonResponse
import dotenv
from django.shortcuts import render, redirect
from watch.utils import update_anime_user_history, get_anime_user_history, get_from_redis_cache, store_in_redis_cache
import requests
import json

dotenv.load_dotenv()

def watch(request, anime_id, episode=None):
    # store anime history
    anime_history = get_anime_user_history(request.user, anime_id)

    watched_episodes = [h.episode for h in anime_history]
    current_watched_time = [h.time_watched for h in anime_history if h.episode == episode]
    current_watched_time = current_watched_time[0] if current_watched_time else 0

    if not episode or episode < 1:
        episode = [h.episode for h in anime_history if h.last_watched]
        episode = episode[0] if episode else 1
        return redirect("watch:watch_episode", anime_id=anime_id, episode=episode)

    mode = request.GET.get("mode", request.user.preferences.default_language)

    anime_data_cached = get_from_redis_cache(anime_id)

    if not anime_data_cached:
        print("fetching data from api")
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

        anime_data_to_cache = {
            "anime_data": anime_data,
            "anime_selected": anime_selected,
            "anime_episodes": anime_episodes,
        }

        store_in_redis_cache(anime_id, json.dumps(anime_data_to_cache))
    else:
        print("fetching data from cache")
        anime_data_cached = json.loads(anime_data_cached)
        anime_data = anime_data_cached["anime_data"]
        anime_selected = anime_data_cached["anime_selected"]
        anime_episodes = anime_data_cached["anime_episodes"]

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

    # if no captions are present and the mode is dub, and ingrain_sub_subtitles_in_dub is true, then fetch the sub track
    if not any(t["kind"] == "captions" for t in episode_data["tracks"]) and mode == "dub" and request.user.preferences.ingrain_sub_subtitles_in_dub:
        base_url = f"{os.getenv("ZORO_URL")}/anime/episode-srcs?id={episode_d["episodeId"]}?server&category=sub"
        response = requests.get(base_url).json()
        # attach the sub captions to the dub episode data, append - do not replace
        captions = [t for t in response["tracks"] if t["kind"] == "captions"]
        if captions:
            episode_data["tracks"].extend(captions)

    current_episode_name = [e["title"] for e in anime_episodes["episodes"] if e["number"] == episode][0]
   
    update_anime_user_history(request.user, anime_id, episode, current_watched_time)

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
