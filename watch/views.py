import os
import dotenv
from django.shortcuts import render, redirect
import requests

dotenv.load_dotenv()

def watch(request, anime_id, episode=None):
    if not episode or episode < 1:
        return redirect("watch:watch_episode", anime_id=anime_id, episode=1)
    
    mode = request.GET.get("mode", "sub")

    base_url = f"{os.getenv("CONSUMET_URL")}/meta/anilist/data/{anime_id}?provider=zoro"
    response = requests.get(base_url)
    anime_data = response.json()

    base_url = f"{os.getenv("CONSUMET_URL")}/anime/zoro/{anime_data["title"]["english"]}?page=1"
    response = requests.get(base_url)
    anime_search_result = response.json()["results"][0]
    anime_fetch_id = anime_search_result["id"]

    base_url = f"{os.getenv("CONSUMET_URL")}/anime/zoro/info?id={anime_fetch_id}"
    response = requests.get(base_url)
    anime_info = response.json()
    episodes = anime_info["episodes"]

    if episode > anime_info["totalEpisodes"]:
        return redirect("watch:watch_episode", anime_id=anime_id, episode=episodes)
    
    # episode_d = [episode for episode in episodes if episode["number"] == episode]

    ed = None
    for e in episodes:
        if e["number"] == episode:
            ed = e
            break

    base_url = f"{os.getenv("CONSUMET_URL")}/anime/zoro/watch?episodeId={ed['id'].replace("sub", "").replace("dub", "").replace("both", "")}{mode}"
    response = requests.get(base_url)
    episode_data = response.json()

    print(episode_data)

    return render(request, "watch/watch.html", { "anime": anime_data, "episode": episode_data, "episodes": episodes, "current_episode": episode, "stream_url": episode_data["sources"][0]["url"] })