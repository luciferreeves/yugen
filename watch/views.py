import os
from django.http import JsonResponse
import dotenv
from django.shortcuts import render, redirect
from authentication.utils import get_single_anime_mal
from watch.utils import get_episode_metadata, update_anime_user_history, get_anime_user_history, get_from_redis_cache, store_in_redis_cache
import requests
import json
from functools import lru_cache

dotenv.load_dotenv()

def watch(request, anime_id, episode=None):
    user = request.user
    preferences = user.preferences
    
    if not episode and preferences.default_watch_page == "detail" and request.GET.get("forward") != "detail":
        return redirect("detail:detail", anime_id=anime_id)

    anime_history = get_anime_user_history(user, anime_id)
    watched_episodes = [h.episode for h in anime_history]
    
    if not episode or episode < 1:
        episode = next((h.episode for h in anime_history if h.last_watched), 1)
        return redirect("watch:watch_episode", anime_id=anime_id, episode=episode)

    mode = request.GET.get("mode", preferences.default_language)
    
    anime_data, anime_selected, anime_episodes = get_anime_combined_data(anime_id)

    if not anime_data or anime_data.get("status") == "Not yet aired" or not anime_selected or not anime_episodes:
        return redirect("detail:detail", anime_id=anime_id)

    mode = process_mode(mode, anime_selected, episode)
    episode_data, current_episode_data = process_episode_data(anime_episodes, episode, mode, preferences)
    
    if not episode_data:
        return redirect("watch:watch_episode", anime_id=anime_id, episode=anime_episodes["totalEpisodes"])

    current_watched_time = next((h.time_watched for h in anime_history if h.episode == episode), 0)
    update_anime_user_history(user, anime_id, episode, current_watched_time)

    context = build_context(anime_data, anime_selected, anime_episodes, episode_data, current_episode_data, 
                            episode, anime_id, anime_history, watched_episodes, mode)

    if user.mal_access_token and "malId" in anime_data:
        context["mal_data"] = get_mal_data(user.mal_access_token, anime_data["malId"])

    return render(request, "watch/watch.html", context)

@lru_cache(maxsize=100)
def get_anime_combined_data(anime_id):
    cache_keys = [
        f"anime_{anime_id}_combined_data",
        f"anime_{anime_id}_data",
        f"anime_{anime_id}_selected",
        f"anime_{anime_id}_episodes"
    ]
    
    cached_data = get_multiple_from_cache(cache_keys)
    
    if cached_data.get(cache_keys[0]):
        return json.loads(cached_data[cache_keys[0]])
    
    anime_data = cached_data.get(cache_keys[1]) or fetch_anime_data(anime_id)
    if not anime_data:
        return None, None, None
    
    anime_selected = cached_data.get(cache_keys[2]) or fetch_anime_selected(anime_data)
    anime_episodes = cached_data.get(cache_keys[3]) or fetch_anime_episodes(anime_selected) if anime_selected else None
    
    combined_data = [anime_data, anime_selected, anime_episodes]
    store_in_redis_cache(cache_keys[0], json.dumps(combined_data), 3600)  # Cache for 1 hour
    
    return combined_data

def get_multiple_from_cache(keys):
    return {key: json.loads(value) if value else None 
            for key, value in zip(keys, map(get_from_redis_cache, keys))}

def fetch_anime_data(anime_id):
    url = f"{os.getenv('CONSUMET_URL')}/meta/anilist/info/{anime_id}?provider=zoro"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        store_in_redis_cache(f"anime_{anime_id}_data", json.dumps(data), 86400)  # Cache for 24 hours
        return data
    except requests.RequestException as e:
        print(f"Error fetching anime data for ID {anime_id}: {e}")
        return None

def fetch_anime_selected(anime_data):
    if anime_data and anime_data.get("episodes"):
        z_anime_id = anime_data["episodes"][0]["id"].split("$")[0]
        url = f"{os.getenv('ZORO_URL')}/anime/info?id={z_anime_id}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            store_in_redis_cache(f"anime_{anime_data['id']}_selected", json.dumps(data), 86400)  # Cache for 24 hours
            return data
        except requests.RequestException as e:
            print(f"Error fetching anime selected data: {e}")
    return None

def fetch_anime_episodes(anime_selected):
    if anime_selected and anime_selected.get("anime", {}).get("info", {}).get("id"):
        url = f"{os.getenv('ZORO_URL')}/anime/episodes/{anime_selected['anime']['info']['id']}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            store_in_redis_cache(f"anime_{anime_selected['anime']['info']['id']}_episodes", json.dumps(data), 86400)  # Cache for 24 hours
            return data
        except requests.RequestException as e:
            print(f"Error fetching anime episodes: {e}")
    return None

def process_mode(mode, anime_selected, episode):
    if not anime_selected.get("anime", {}).get("info", {}).get("stats", {}).get("episodes", {}).get(mode) or \
       anime_selected["anime"]["info"]["stats"]["episodes"].get(mode, 0) < episode:
        return "sub"
    return mode

def process_episode_data(anime_episodes, episode, mode, preferences):
    if not anime_episodes or episode > anime_episodes.get("totalEpisodes", 0):
        return None, None

    episode_d = next((e for e in anime_episodes.get("episodes", []) if e["number"] == episode), None)
    if not episode_d:
        return None, None

    cache_key = f"episode_data_{episode_d['episodeId']}_{mode}"
    episode_data = get_from_redis_cache(cache_key)

    if not episode_data:
        episode_data = fetch_episode_data(episode_d["episodeId"], mode)
        if episode_data:
            store_in_redis_cache(cache_key, json.dumps(episode_data), 3600)  # Cache for 1 hour
    else:
        episode_data = json.loads(episode_data)
    
    if preferences.ingrain_sub_subtitles_in_dub and mode == "dub" and \
       not any(t.get("kind") == "captions" for t in episode_data.get("tracks", [])):
        sub_data = fetch_episode_data(episode_d["episodeId"], "sub")
        if sub_data:
            episode_data.setdefault("tracks", []).extend([t for t in sub_data.get("tracks", []) if t.get("kind") == "captions"])

    current_episode_data = {
        "title": episode_d.get("title", ""),
        "number": episode_d.get("number", 0),
    }

    return episode_data, current_episode_data

def fetch_episode_data(episode_id, mode):
    url = f"{os.getenv('ZORO_URL')}/anime/episode-srcs?id={episode_id}?server&category={mode}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("message") == "Couldn't find server. Try another server":
            url = f"{os.getenv('ZORO_URL')}/anime/episode-srcs?id={episode_id}?server=hd-2&category={mode}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
        
        return data
    except requests.RequestException as e:
        print(f"Error fetching episode data for ID {episode_id}: {e}")
        return None

def build_context(anime_data, anime_selected, anime_episodes, episode_data, current_episode_data, 
                  episode, anime_id, anime_history, watched_episodes, mode):
    return {
        "anime_data": anime_data,
        "anime_selected": anime_selected,
        "anime_episodes": anime_episodes,
        "episode_data": episode_data,
        "current_episode": episode,
        "current_episode_data": current_episode_data,
        "stream_url": episode_data.get("sources", [{}])[0].get("url") if episode_data else None,
        "anime_id": anime_id,
        "current_episode_name": current_episode_data.get("title") if current_episode_data else None,
        "anime_history": anime_history,
        "watched_episodes": watched_episodes,
        "current_watched_time": next((h.time_watched for h in anime_history if h.episode == episode), 0),
        "current_episode_metadata": get_episode_metadata(anime_data, episode),
        "mode": mode,
    }

@lru_cache(maxsize=100)
def get_mal_data(mal_access_token, mal_id):
    cache_key = f"mal_data_{mal_id}"
    mal_data = get_from_redis_cache(cache_key)
    
    if not mal_data:
        mal_data = get_single_anime_mal(mal_access_token, mal_id)
        if mal_data:
            mal_data["average_episode_duration"] = mal_data.get("average_episode_duration", 0) // 60 + 1
            mal_data["episode_range"] = list(range(1, mal_data.get("num_episodes", 1) + 1))
            store_in_redis_cache(cache_key, json.dumps(mal_data), 86400)  # Cache for 24 hours
    else:
        mal_data = json.loads(mal_data)
    
    return mal_data

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
