import datetime
from datetime import datetime as dt
import os
from django.http import Http404, JsonResponse
import dotenv
from django.shortcuts import get_object_or_404, render, redirect
import requests
from authentication.utils import get_single_anime_mal
from watch.utils import get_all_episode_metadata, get_from_redis_cache, store_in_redis_cache, update_anime_user_history, get_anime_user_history
from watch.models import Anime, AnimeEpisode, AnimeTitle, AnimeTrailer, AnimeGenre, AnimeStudio
from django.db import transaction
from django.db.models import Q
from collections import defaultdict
import json

dotenv.load_dotenv()

def get_anime_by_id(anime_id):
    cache_key = f"anime_{anime_id}_anime_data"
    try:
        anime_data = get_from_redis_cache(cache_key)
        anime_data = json.loads(anime_data)
    except:
        base_url = f"{os.getenv('CONSUMET_URL')}/meta/anilist/info/{anime_id}?provider=zoro"
        response = requests.get(base_url)
        anime_data = response.json()

        if anime_data["status"] == "Completed":
            store_in_redis_cache(cache_key, json.dumps(anime_data), 3600 * 24 * 30)  # Cache for 30 days
        else:
            store_in_redis_cache(cache_key, json.dumps(anime_data), 3600 * 12) # Cache for 12 hours

    return anime_data

def get_info_by_zid(zid):
    cache_key = f"anime_{zid}_anime_selected"
    try:
        anime_selected = get_from_redis_cache(cache_key)
        anime_selected = json.loads(anime_selected)
    except:
        base_url = f"{os.getenv('ZORO_URL')}/anime/info?id={zid}"
        response = requests.get(base_url)
        anime_selected = response.json()
        store_in_redis_cache(cache_key, json.dumps(anime_selected), 3600 * 12)

    return anime_selected

def get_episodes_by_zid(anime):
    base_url = f"{os.getenv('ZORO_URL')}/anime/episodes/{anime.z_anime_id}"
    response = requests.get(base_url)
    fetched_episodes = response.json()

    anime_data = {
        "id": anime.id,
        "title": {
            "english": anime.title.english,
            "romaji": anime.title.romaji,
            "native": anime.title.native
        },
        "type": anime.type,
        "startDate": {
            "year": anime.start_date.year,
            "month": anime.start_date.month,
            "day": anime.start_date.day
        },
        "totalEpisodes": anime.totalEpisodes or fetched_episodes["totalEpisodes"],
        "isAdult": False,
        "countryOfOrigin": anime.countryOfOrigin,
        "duration": anime.duration,
    }

    fetched_episodes_metadata = get_all_episode_metadata(anime_data)

    for index, episode in enumerate(fetched_episodes["episodes"]):
        episode["metadata"] = fetched_episodes_metadata[index]

    return fetched_episodes

def get_episode_streaming_data(episode_id, category):
    cache_key = f"episode_{episode_id}_streaming_data_{category}"
    try:
        episode_data = get_from_redis_cache(cache_key)
        episode_data = json.loads(episode_data)
    except:
        base_url = f"{os.getenv('ZORO_URL')}/anime/episode-srcs?id={episode_id}?server&category={category}"
        response = requests.get(base_url)
        episode_data = response.json()

        if "message" in episode_data and episode_data["message"] == "Couldn't find server. Try another server":
            base_url = f"{os.getenv('ZORO_URL')}/anime/episode-srcs?id={episode_id}?server=hd-2&category={category}"
            response = requests.get(base_url)
            episode_data = response.json()
        store_in_redis_cache(cache_key, json.dumps(episode_data), 3600 * 24 * 7)

    return episode_data

def update_anime(anime_id, anime_fetched):
    if "message" in anime_fetched:
        print("Error fetching anime", anime_fetched["message"])
        return None

    with transaction.atomic():
        # Convert start and end dates
        start_date = None
        if anime_fetched.get('startDate'):
            start_date = datetime.date(
                year=anime_fetched['startDate'].get('year'),
                month=anime_fetched['startDate'].get('month') or 1,
                day=anime_fetched['startDate'].get('day') or 1
            )
        
        end_date = None
        if anime_fetched.get('endDate') and anime_fetched['endDate'].get('year') is not None:
            end_date = datetime.date(
                year=anime_fetched['endDate'].get('year'),
                month=anime_fetched['endDate'].get('month') or 1,
                day=anime_fetched['endDate'].get('day') or 1
            )
        
        # First, create or update the Anime object
        anime, created = Anime.objects.update_or_create(
            id=anime_id,
            defaults={
                'malId': anime_fetched['malId'],
                'z_anime_id': anime_fetched["episodes"][0]["id"].split("$")[0] if len(anime_fetched["episodes"]) > 0 else None,
                'description': anime_fetched.get('description'),
                'image': anime_fetched.get('image'),
                'cover': anime_fetched.get('cover'),
                'countryOfOrigin': anime_fetched.get('countryOfOrigin'),
                'popularity': anime_fetched.get('popularity'),
                'color': anime_fetched.get('color'),
                'releaseDate': anime_fetched.get('releaseDate'),
                'totalEpisodes': anime_fetched.get('totalEpisodes'),
                'currentEpisode': anime_fetched.get('currentEpisode'),
                'rating': anime_fetched.get('rating'),
                'duration': anime_fetched.get('duration'),
                'type': anime_fetched.get('type'),
                'season': anime_fetched.get('season'),
                'status': anime_fetched.get('status'),
                'start_date': start_date,
                'end_date': end_date,
                'dub': 0,  # Set a default value
                'sub': 0,  # Set a default value
            }
        )
        
        # Now, create or update the AnimeTitle
        title, _ = AnimeTitle.objects.update_or_create(
            anime=anime,
            defaults={
                'english': anime_fetched['title'].get('english') or None,
                'romaji': anime_fetched['title']['romaji'],
                'native': anime_fetched['title'].get('native') or None
            }
        )
        
        if "trailer" in anime_fetched:
            trailer, _ = AnimeTrailer.objects.update_or_create(
                anime=anime,
                defaults={
                    'id': anime_fetched['trailer']['id'],
                    'site': anime_fetched['trailer']['site'],
                    'thumbnail': anime_fetched['trailer']['thumbnail']
                }
            )
        else:
            AnimeTrailer.objects.filter(anime=anime).delete()

        # Update sub and dub count
        z_anime_info = get_info_by_zid(anime.z_anime_id)
        try:
            anime.sub = z_anime_info["anime"]["info"]["stats"]["episodes"].get("sub", 0)
            anime.dub = z_anime_info["anime"]["info"]["stats"]["episodes"].get("dub", 0)
        except:
            print("Error fetching sub and dub count:", z_anime_info)
            # Set default values if fetching fails
            anime.sub = anime.sub or 0  # Keep existing value or set to 0
            anime.dub = anime.dub or 0  # Keep existing value or set to 0
        
        # Update genres
        anime.genres.set([AnimeGenre.objects.get_or_create(name=genre)[0] for genre in anime_fetched['genres']])
        
        # Update studios
        anime.studios.set([AnimeStudio.objects.get_or_create(name=studio)[0] for studio in anime_fetched['studios']])

        update_anime_episodes(anime)
        
        anime.save()
    
    return anime

def update_anime_episodes(anime):
    fetched_episodes = get_episodes_by_zid(anime)
    
    with transaction.atomic():
        # Update anime's total episodes
        anime.currentEpisode = fetched_episodes["totalEpisodes"]
        anime.dub = anime.dub if anime.dub is not None else 0
        anime.sub = anime.sub if anime.sub is not None else 0
        anime.save()

        # Get existing episodes for this anime
        existing_episodes = {ep.number: ep for ep in AnimeEpisode.objects.filter(anime=anime)}

        episodes_to_create = []
        episodes_to_update = []

        for episode in fetched_episodes["episodes"]:
            metadata = episode['metadata']
            episode_data = {
                'anime': anime,
                'zEpisodeId': episode['episodeId'],
                'title': metadata['title'],
                'number': int(episode['number']),
                'description': metadata.get('description', ''),
                'air_date': dt.strptime(metadata.get('airDate', '1970-01-01'), '%Y-%m-%d').date(),
                'image': metadata.get('image', ''),
                'filler': episode.get('isFiller', False)
            }

            if int(episode['number']) in existing_episodes:
                ep = existing_episodes[int(episode['number'])]
                for key, value in episode_data.items():
                    setattr(ep, key, value)
                episodes_to_update.append(ep)
            else:
                episodes_to_create.append(AnimeEpisode(**episode_data))

        # Bulk create new episodes
        AnimeEpisode.objects.bulk_create(episodes_to_create)

        # Bulk update existing episodes
        AnimeEpisode.objects.bulk_update(episodes_to_update, 
            ['number', 'title', 'number', 'description', 'air_date', 'image', 'filler'])

        # Update anime's current episode count
        anime.currentEpisode = len(fetched_episodes["episodes"])
        anime.save()

    return anime

def watch(request, anime_id, episode=None):
    forward_detail = request.GET.get("forward") == "detail"
    if not episode and request.user.preferences.default_watch_page == "detail" and not forward_detail:
        return redirect("detail:detail", anime_id=anime_id)
    
    anime_fetched = get_anime_by_id(anime_id)
    try:
        anime = Anime.objects.get(id=anime_id)
        if anime.needs_update():
            anime = update_anime(anime_id, anime_fetched)
    except Anime.DoesNotExist:
        anime = update_anime(anime_id, anime_fetched)

    history = get_anime_user_history(request.user, anime)
    current_watched_time = [h.time_watched for h in history if h.episode.number == episode]
    current_watched_time = current_watched_time[0] if current_watched_time else 0

    if not episode or episode < 1:
        episode = [h.episode.number for h in history if h.last_watched]
        episode = episode[0] if episode else 1
        return redirect("watch:watch_episode", anime_id=anime_id, episode=episode)

    if episode > anime.currentEpisode:
        return redirect("watch:watch_episode", anime_id=anime_id, episode=anime.currentEpisode)

    mode = request.GET.get("mode", request.user.preferences.default_language)
    episodes = AnimeEpisode.objects.filter(anime=anime).order_by('number')
    episode_data = episodes.filter(number=episode).first()

    if mode == "dub" and anime.dub < episode:
        mode = "sub"

    streaming_data = get_episode_streaming_data(episode_data.zEpisodeId, mode)

    # if no captions are present and the mode is dub, and ingrain_sub_subtitles_in_dub is true, then fetch the sub track
    if "tracks" in streaming_data and not any(t["kind"] == "captions" for t in streaming_data["tracks"]) and mode == "dub" and request.user.preferences.ingrain_sub_subtitles_in_dub:
        sub_streaming_data = get_episode_streaming_data(episode_data.zEpisodeId, "sub")
        captions = [t for t in sub_streaming_data["tracks"] if t["kind"] == "captions"]
        if captions:
            streaming_data["tracks"].extend(captions)

    if request.user.mal_access_token and anime.malId:
        mal_data = get_single_anime_mal(request.user.mal_access_token, anime.malId)
        if mal_data:
            mal_data["average_episode_duration"] = mal_data["average_episode_duration"] // 60 + 1

    context = {
        "anime": anime,
        "current_episode_number": episode,
        "current_episode": episode_data,
        "all_episodes": episodes,
        "characters": anime_fetched.get("characters", []),
        "recommendations": anime_fetched.get("recommendations", []),
        "related": anime_fetched.get("relations", []),
        "streaming_data": streaming_data,
        "stream_url": streaming_data["sources"][0]["url"] if streaming_data and "sources" in streaming_data else None,
        "mode": mode,
        "watched_episodes": [h.episode.number for h in history],
        "current_watched_time": current_watched_time,
        "mal_data": mal_data,
        "mal_episode_range": range(1, mal_data["num_episodes"] + 1) if mal_data else None,
    }

    update_anime_user_history(request.user, anime, episode_data, 0)

    return render(request, "watch/watch.html", context)

def update_episode_watch_time(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request"})

    data = json.loads(request.body)
    anime =data.get("anime")
    episode =data.get("episode")
    time_watched =data.get("time_watched")

    if request.user.is_authenticated:
        anime = Anime.objects.get(anime_id=anime)
        episode = AnimeEpisode.objects.get(episode_id=episode)
        update_anime_user_history(request.user, anime, episode, time_watched)
        return JsonResponse({"status": "success"})
    else:
        return JsonResponse({"status": "error", "message": "User not authenticated"})
