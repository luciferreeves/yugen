import json
import os
from django.shortcuts import render
import requests

from watch.utils import get_all_episode_metadata, get_from_redis_cache, store_in_redis_cache

def detail(request, anime_id):
    anime_data = None
    anime_episodes = None
    anime_episodes_metadata = None
    try:
        anime_data = json.loads(get_from_redis_cache(f"anime_{anime_id}_anime_data"))
    except:
        base_url = f"{os.getenv("CONSUMET_URL")}/meta/anilist/info/{anime_id}?provider=zoro"
        response = requests.get(base_url)
        anime_data = response.json()
        store_in_redis_cache(f"anime_{anime_id}_anime_data", json.dumps(anime_data))

    try:
        anime_episodes = json.loads(get_from_redis_cache(f"anime_{anime_id}_anime_episodes"))
    except:
        z_anime_id = anime_data["episodes"][0]["id"].split("$")[0] if len(anime_data["episodes"]) > 0 else None
        if z_anime_id is not None:
            base_url = f"{os.getenv("ZORO_URL")}/anime/episodes/{z_anime_id}"
            response = requests.get(base_url)
            anime_episodes = response.json()
            store_in_redis_cache(f"anime_{anime_id}_anime_episodes", json.dumps(anime_episodes))

    if anime_episodes is not None:
        anime_episodes_metadata = get_all_episode_metadata(anime_data)
        # attach metadata to episodes
        for i, episode in enumerate(anime_episodes["episodes"]):
            episode["metadata"] = anime_episodes_metadata[i]

    context = {
        "anime": anime_data,
        "episodes": anime_episodes,
    }

    return render(request, "detail/detail.html", context)