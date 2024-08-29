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

    base_url = f"{os.getenv("ZORO_URL")}/anime/search?q={anime_data["title"]["english"]}&page=1"
    response = requests.get(base_url)
    anime_search_result = response.json()["animes"][0]

    base_url = f"{os.getenv("ZORO_URL")}/anime/episodes/{anime_search_result["id"]}"
    response = requests.get(base_url)
    anime_episodes = response.json()

    if episode > anime_episodes["totalEpisodes"]:
        return redirect("watch:watch_episode", anime_id=anime_id, episode=anime_episodes["totalEpisodes"])
    
    episode_d = [e for e in anime_episodes["episodes"] if e["number"] == episode][0]

    base_url = f"{os.getenv("ZORO_URL")}/anime/episode-srcs?id={episode_d["episodeId"]}?server&category={mode}"
    response = requests.get(base_url)
    episode_data = response.json()

    print(episode_data)

    return render(request, "watch/watch.html", {
        "anime_data": anime_data,
        "anime_search_result": anime_search_result,
        "anime_episodes": anime_episodes,
        "episode_data": episode_data,
        "current_episode": episode,
        "stream_url": episode_data["sources"][0]["url"],
        "mode": mode,
    })