import os
from django.http import JsonResponse
import dotenv
from django.shortcuts import render, redirect
import requests

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

    # search for the current episode name in anime_episodes.episodes where episode.number == episode
    current_episode_name = [e["title"] for e in anime_episodes["episodes"] if e["number"] == episode][0]

    context = {
        "anime_data": anime_data,
        "anime_selected": anime_selected,
        "anime_episodes": anime_episodes,
        "episode_data": episode_data,
        "current_episode": episode,
        "stream_url": episode_data["sources"][0]["url"],
        "anime_id": anime_id,
        "current_episode_name": current_episode_name,
        "mode": mode,
    }

    # print(anime_search_result)
    # print(anime_data)

    return render(request, "watch/watch.html", context)
