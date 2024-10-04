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
        return redirect("detail:detail", anime_id=anime_id)
    
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

    if anime_data and "status" in anime_data and anime_data["status"] == "Not yet aired":
        return redirect("detail:detail", anime_id=anime_id)
    
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
            "anime_cover_image": episode_data["metadata"]["image"] if episode_data and "metadata" in episode_data else episode_data["image"],
            "episode_title": episode_data["metadata"]["title"] if episode_data and "metadata" in episode_data else episode_data["title"],
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
            if not "url" in episode_data:
                episode_data["url"] = "https://hianime.to/watch/" + episode_data["id"].replace("$episode$", "?ep=")
                episode_data["url"] = episode_data["url"].replace("$dub", "").replace("$sub", "")

            streaming_data = get_zoro_episode_streaming_data(episode_data["url"], mode)
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





    # forward_detail = request.GET.get("forward") == "detail"
    # preload_request = request.GET.get("preload") == "true"
    # if not episode and request.user.preferences.default_watch_page == "detail" and not forward_detail:
    #     return redirect("detail:detail", anime_id=anime_id)
    
    # anime_fetched, provider, gogodub = get_anime_data(anime_id)
    # provider = provider.decode() if isinstance(provider, bytes) else provider
    # provider = "gogo" if request.user.preferences.default_provider == "gogoanime" else "zoro"
    # provider = request.GET.get("provider", provider)
    # if not anime_fetched:
    #     provider = "gogo"
    # if anime_fetched and "status" in anime_fetched and anime_fetched["status"] == "Not yet aired":
    #     return redirect("detail:detail", anime_id=anime_id)
    
    # forced_update = request.GET.get("refresh") == "true"

    # if anime_fetched and provider == "zoro":
    #     try:
    #         anime = Anime.objects.get(id=anime_id)
    #         if (anime.needs_update() or forced_update):
    #             anime = update_anime(anime_id, anime_fetched)
    #     except Anime.DoesNotExist:
    #         anime = update_anime(anime_id, anime_fetched)
    # else:
    #     anime = anime_fetched
    #     if anime:
    #         anime["anime_id"] = anime["id"]
    # if provider == "zoro":
    #     history = get_anime_user_history(request.user, anime)
    #     current_watched_time = [h.time_watched for h in history if h.episode.number == episode]
    #     current_watched_time = current_watched_time[0] if current_watched_time else 0

    #     if not episode or episode < 0:
    #         episode = [h.episode.number for h in history if h.last_watched]
    #         episode = episode[0] if episode else 1
    #         return redirect("watch:watch_episode", anime_id=anime_id, episode=episode)

    #     if episode > anime.currentEpisode:
    #         return redirect("watch:watch_episode", anime_id=anime_id, episode=anime.currentEpisode)
    # else:
    #     history = []
    #     current_watched_time = 0

    #     if not episode or episode < 0:
    #         episode = 1
    #         return redirect("watch:watch_episode", anime_id=anime_id, episode=episode)
        
    #     if anime and "totalEpisodes" in anime and episode > anime["totalEpisodes"]:
    #         return redirect("watch:watch_episode", anime_id=anime_id, episode=anime["totalEpisodes"])


    # mode = request.GET.get("mode", request.user.preferences.default_language)
    
    # if provider == "zoro":
    #     episodes = AnimeEpisode.objects.filter(anime=anime).order_by('number')
    #     episode_data = episodes.filter(number=episode).first()

    #     if mode == "dub" and anime.dub < episode:
    #         mode = "sub"

    #     streaming_data = get_episode_streaming_data(episode_data.zEpisodeId, mode) if episode_data else None
    #     if streaming_data and "message" in streaming_data:
    #         server, mode = find_alternate_server(episode_data.zEpisodeId, mode)
    #         streaming_data = get_episode_streaming_data(episode_data.zEpisodeId, mode, server)
            
    #     # if no captions are present and the mode is dub, and ingrain_sub_subtitles_in_dub is true, then fetch the sub track
    #     if streaming_data and "tracks" in streaming_data and not any(t["kind"] == "captions" for t in streaming_data["tracks"]) and mode == "dub" and request.user.preferences.ingrain_sub_subtitles_in_dub:
    #         sub_streaming_data = get_episode_streaming_data(episode_data.zEpisodeId, "sub")
    #         if "tracks" in sub_streaming_data:
    #             captions = [t for t in sub_streaming_data["tracks"] if t["kind"] == "captions"]
    #             if captions:
    #                 streaming_data["tracks"].extend(captions)

    #     if request.user.mal_access_token and anime.malId:
    #         mal_data = get_single_anime_mal(request.user.mal_access_token, anime.malId)
    #         if mal_data:
    #             mal_data["average_episode_duration"] = mal_data["average_episode_duration"] // 60 + 1

    #     if anime and episode_data and not preload_request:
    #         update_anime_user_history(request.user, anime, episode_data, current_watched_time)

    #     seasons = get_seasons_by_zid(anime.z_anime_id)
    #     stream_url = streaming_data["sources"][0]["url"] if streaming_data and "sources" in streaming_data else None
    # else:
    #     gogodub = True if mode == "dub" else False
    #     anime_fetched, provider, gogodub = get_anime_data(anime_id, provider="gogo", gogodub=gogodub)
    #     if anime_fetched and "status" in anime_fetched and anime_fetched["status"] == "Not yet aired":
    #         return redirect("detail:detail", anime_id=anime_id)
    #     episodes, m = get_anime_episodes_gogo(anime_id, mode)
    #     if episodes:
    #         attach_episode_metadata(anime_fetched, episodes)

    #     if not gogodub and mode == "dub":
    #         mode = "sub"

    #     episodes = episodes["episodes"]
    #     episode_data = next((e for e in episodes if e["number"] == int(episode)), None)
    #     seasons = []
    #     streaming_data = get_gogo_streaming_data(episode_data["id"]) if episode_data else None
    #     streaming_data["anilistID"] = anime_id
    #     streaming_data["malID"] = anime_fetched["malId"] if "malId" in anime_fetched else 0
    #     stream_url = streaming_data["sources"][0]["url"] if streaming_data and "sources" in streaming_data else None
    #     episode_data["episodeId"] = episode_data["number"]

    #     if request.user.mal_access_token and anime_fetched["malId"]:
    #         mal_data = get_single_anime_mal(request.user.mal_access_token, anime_fetched["malId"])
    #         if mal_data:
    #             mal_data["average_episode_duration"] = mal_data["average_episode_duration"] // 60 + 1

    # if preload_request:
    #     return JsonResponse({"status": f"Preloaded episode {episode}"})
    
    # should_preload = episode < len(episodes)

    # context = {
    #     "anime": anime,
    #     "animeID": anime_id,
    #     "current_episode_number": episode,
    #     "current_episode": episode_data,
    #     "all_episodes": episodes,
    #     "characters": anime_fetched.get("characters", []),
    #     "recommendations": anime_fetched.get("recommendations", []),
    #     "related": anime_fetched.get("relations", []),
    #     "streaming_data": streaming_data,
    #     "stream_url": stream_url,
    #     "mode": mode,
    #     "watched_episodes": [h.episode.number for h in history],
    #     "current_watched_time": current_watched_time,
    #     "seasons": seasons,
    #     "provider": provider,
    #     "should_preload": should_preload,
    # }

    # mal_id_present = anime_fetched.get("malId")
    # if isinstance(anime, Anime):
    #     if not mal_id_present and anime.malId:
    #         mal_id_present = True

    # if request.user.mal_access_token and mal_id_present:
    #     context["mal_data"] = mal_data
    #     context["mal_episode_range"] = range(1, mal_data["num_episodes"] + 1)

    # if "nextAiringEpisode" in anime_fetched:
    #     context["nextAiringEpisode"] = anime_fetched["nextAiringEpisode"]

    # return render(request, "watch/watch.html", context)




# def get_anime_by_id(anime_id):
#     cache_key = f"anime_{anime_id}_anime_data"
#     anime_data = get_from_redis_cache(cache_key)
#     provider = get_from_redis_cache(f"anime_{anime_id}_provider")
#     if not provider:
#         provider = "zoro"
#     if not anime_data:
#         base_url = f"{os.getenv('CONSUMET_URL')}/meta/anilist/info/{anime_id}?provider=zoro"
#         try:
#             response = requests.get(base_url, timeout=10)
#             anime_data = response.json()
#             if ("message" not in anime_data or response.status_code == 200) and anime_data["episodes"]:
#                 if anime_data["status"] == "Completed":
#                     store_in_redis_cache(cache_key, json.dumps(anime_data), 3600 * 24 * 30)  # Cache for 30 days
#                 else:
#                     store_in_redis_cache(cache_key, json.dumps(anime_data), 3600 * 12) # Cache for 12 hours
#                 store_in_redis_cache(f"anime_{anime_id}_provider", "zoro")
#             else:
#                 provider = "gogo"
#                 base_url = f"{os.getenv('CONSUMET_URL')}/meta/anilist/info/{anime_id}"
#                 response = requests.get(base_url, timeout=10)
#                 anime_data = response.json()
#                 store_in_redis_cache(cache_key, json.dumps(anime_data), 3600 * 12) # Cache for 12 hours
#                 store_in_redis_cache(f"anime_{anime_id}_provider", "gogo")
#         except requests.RequestException as e:
#             print(f"Error fetching anime data for ID {anime_id}: {e}")
#             return None
#     else:
#         anime_data = json.loads(anime_data)

#     if not anime_data:
#         print(f"Anime data not found for ID {anime_id}")
    
#     return anime_data, provider



# def get_episodes_and_metadata(anime):
#     fetched_episodes = get_episodes_by_zid(anime.z_anime_id)
#     anime_data = {
#         "id": anime.id,
#         "title": {
#             "english": anime.title.english,
#             "romaji": anime.title.romaji,
#             "native": anime.title.native
#         },
#         "type": anime.type,
#         "startDate": {
#             "year": anime.start_date.year,
#             "month": anime.start_date.month,
#             "day": anime.start_date.day
#         },
#         "totalEpisodes": anime.totalEpisodes or fetched_episodes["totalEpisodes"],
#         "isAdult": False,
#         "countryOfOrigin": anime.countryOfOrigin,
#         "duration": anime.duration,
#     }

#     fetched_episodes_metadata = get_all_episode_metadata(anime_data)

#     for index, episode in enumerate(fetched_episodes["episodes"]):
#         episode["metadata"] = fetched_episodes_metadata[index] if index < len(fetched_episodes_metadata) else {
#             "title": episode["title"],
#             "description": "",
#             "airDate": "1970-01-01",
#             "image": anime.image
#         }

#     return fetched_episodes

# def get_episode_streaming_data(episode_id, category, server=None):
#     cache_key = f"episode_{episode_id}_streaming_data_{category}"
#     try:
#         episode_data = get_from_redis_cache(cache_key)
#         episode_data = json.loads(episode_data)
#     except:
#         base_url = f"{os.getenv('ZORO_URL')}/anime/episode-srcs?id={episode_id}&category={category}"
#         print(base_url)
#         if server:
#             base_url += f"&server={server}"

#         response = requests.get(base_url)
#         episode_data = response.json()

#         if "message" not in episode_data:
#             store_in_redis_cache(cache_key, json.dumps(episode_data), 3600 * 24 * 7)

#     return episode_data

# def update_anime(anime_id, anime_fetched, zid=None):
#     if "message" in anime_fetched:
#         print("Error fetching anime", anime_fetched["message"])
#         return None

#     with transaction.atomic():
#         # Convert start and end dates
#         start_date = None
#         if anime_fetched.get('startDate'):
#             start_date = datetime.date(
#                 year=anime_fetched['startDate'].get('year') or 1970,
#                 month=anime_fetched['startDate'].get('month') or 1,
#                 day=anime_fetched['startDate'].get('day') or 1
#             )
        
#         end_date = None
#         if anime_fetched.get('endDate') and anime_fetched['endDate'].get('year') is not None:
#             end_date = datetime.date(
#                 year=anime_fetched['endDate'].get('year'),
#                 month=anime_fetched['endDate'].get('month') or 1,
#                 day=anime_fetched['endDate'].get('day') or 1
#             )
        
#         # First, create or update the Anime object
#         anime, created = Anime.objects.update_or_create(
#             id=anime_id,
#             defaults={
#                 'malId': anime_fetched['malId'] if "malId" in anime_fetched else None,
#                 'description': anime_fetched.get('description'),
#                 'image': anime_fetched.get('image'),
#                 'cover': anime_fetched.get('cover'),
#                 'countryOfOrigin': anime_fetched.get('countryOfOrigin'),
#                 'popularity': anime_fetched.get('popularity'),
#                 'color': anime_fetched.get('color'),
#                 'releaseDate': anime_fetched.get('releaseDate'),
#                 'totalEpisodes': anime_fetched.get('totalEpisodes'),
#                 'currentEpisode': anime_fetched.get('currentEpisode'),
#                 'rating': anime_fetched.get('rating'),
#                 'duration': anime_fetched.get('duration'),
#                 'type': anime_fetched.get('type'),
#                 'season': anime_fetched.get('season'),
#                 'status': anime_fetched.get('status'),
#                 'start_date': start_date,
#                 'end_date': end_date,
#                 'dub': 0,  # Set a default value
#                 'sub': 0,  # Set a default value
#             }
#         )

#         # separately update zid:
#         if not anime.z_anime_id:
#             if zid:
#                 anime.z_anime_id = zid
#             else:
#                 anime.z_anime_id = anime_fetched["episodes"][0]["id"].split("$")[0] if len(anime_fetched["episodes"]) > 0 else zid
#             anime.save()
        
#         # Now, create or update the AnimeTitle
#         title, _ = AnimeTitle.objects.update_or_create(
#             anime=anime,
#             defaults={
#                 'english': anime_fetched['title'].get('english') or None,
#                 'romaji': anime_fetched['title']['romaji'],
#                 'native': anime_fetched['title'].get('native') or None
#             }
#         )
        
#         if "trailer" in anime_fetched:
#             trailer, _ = AnimeTrailer.objects.update_or_create(
#                 anime=anime,
#                 defaults={
#                     'id': anime_fetched['trailer']['id'],
#                     'site': anime_fetched['trailer']['site'],
#                     'thumbnail': anime_fetched['trailer']['thumbnail']
#                 }
#             )
#         else:
#             AnimeTrailer.objects.filter(anime=anime).delete()

#         # Update sub and dub count
#         z_anime_info = get_info_by_zid(anime.z_anime_id)
#         try:
#             anime.sub = z_anime_info["anime"]["info"]["stats"]["episodes"].get("sub", 0)
#             anime.dub = z_anime_info["anime"]["info"]["stats"]["episodes"].get("dub", 0)
#         except:
#             print("Error fetching sub and dub count:", z_anime_info)
#             # Set default values if fetching fails
#             anime.sub = anime.sub or 0  # Keep existing value or set to 0
#             anime.dub = anime.dub or 0  # Keep existing value or set to 0

#         if anime.currentEpisode < anime.sub:
#             anime.currentEpisode = anime.sub

#         if anime.totalEpisodes < anime.sub:
#             anime.totalEpisodes = anime.sub
        
#         # Update genres
#         anime.genres.set([AnimeGenre.objects.get_or_create(name=genre)[0] for genre in anime_fetched['genres']])
        
#         # Update studios
#         anime.studios.set([AnimeStudio.objects.get_or_create(name=studio)[0] for studio in anime_fetched['studios']])

#         update_anime_episodes(anime)
        
#         anime.save()
    
#     return anime

# def update_anime_episodes(anime):
#     if not anime.z_anime_id:
#         return anime

#     fetched_episodes = get_episodes_and_metadata(anime)
    
#     with transaction.atomic():
#         # Update anime's total episodes
#         anime.currentEpisode = fetched_episodes["episodes"][-1]["number"]
#         anime.dub = anime.dub if anime.dub is not None else 0
#         anime.sub = anime.sub if anime.sub is not None else 0
#         anime.save()

#         # Get existing episodes for this anime
#         existing_episodes = {ep.number: ep for ep in AnimeEpisode.objects.filter(anime=anime)}

#         episodes_to_create = []
#         episodes_to_update = []

#         for episode in fetched_episodes["episodes"]:
#             metadata = episode['metadata']
#             episode_data = {
#                 'anime': anime,
#                 'zEpisodeId': episode['episodeId'],
#                 'title': episode['title'],
#                 'number': int(episode['number']),
#                 'description': metadata.get('description', 'No description available.'),
#                 'air_date': dt.strptime(metadata.get('airDate', '1970-01-01'), '%Y-%m-%d').date(),
#                 'image': metadata.get('image', anime.image),
#                 'filler': episode.get('isFiller', False)
#             }

#             # if image is null, set it to anime image
#             if not episode_data['image']:
#                 episode_data['image'] = anime.image

#             if int(episode['number']) in existing_episodes:
#                 ep = existing_episodes[int(episode['number'])]
#                 for key, value in episode_data.items():
#                     setattr(ep, key, value)
#                 episodes_to_update.append(ep)
#             else:
#                 episodes_to_create.append(AnimeEpisode(**episode_data))

#         # Bulk create new episodes
#         AnimeEpisode.objects.bulk_create(episodes_to_create)

#         # Bulk update existing episodes
#         AnimeEpisode.objects.bulk_update(episodes_to_update, 
#             ['number', 'title', 'number', 'description', 'air_date', 'image', 'filler'])

#         anime.save()

#     return anime

# def find_alternate_server(episode_id, mode):
#     base_url = f"{os.getenv('ZORO_URL')}/anime/servers?episodeId={episode_id}"
#     print(base_url)
#     response = requests.get(base_url)
#     response = response.json()

#     if "message" in response:
#         return None, mode

#     if mode == "dub" and "dub" in response and len(response["dub"]) > 0:
#         server_id = response["dub"][0]["serverName"]
#         mode = "dub"
#     elif len(response["sub"]) > 0 and "sub" in response:
#         server_id = response["sub"][0]["serverName"]
#         mode = "sub"
#     elif len(response["raw"]) > 0:
#         server_id = response["raw"][0]["serverName"]
#         mode = "raw"

#     return server_id, mode

# def convert_gogo_stream_data(input_data):
#     # Create the new structure
#     new_data = {
#         'tracks': [],
#         'intro': {'start': 0, 'end': 0},
#         'outro': {'start': 0, 'end': 0},
#         'sources': [],
#         'anilistID': 0,
#         'malID': 0
#     }
    
#     # Add the default stream to sources
#     default_source = next((s for s in input_data['sources'] if s['quality'] == 'default'), None)
#     if default_source:
#         new_data['sources'].append({
#             'url': default_source['url'],
#             'type': 'hls'
#         })
    
#     return new_data

# def get_gogo_streaming_data(episode_id):
#     cache_key = f"episode_{episode_id}_streaming_data"
#     try:
#         episode_data = get_from_redis_cache(cache_key)
#         episode_data = json.loads(episode_data)
#     except:
#         base_url = f"{os.getenv('CONSUMET_URL')}/meta/anilist/watch/{episode_id}"
#         response = requests.get(base_url)
#         episode_data = response.json()
#         store_in_redis_cache(cache_key, json.dumps(episode_data), 3600 * 24 * 7)

#     return convert_gogo_stream_data(episode_data)



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

# def watch_via_zid(request, zid):
#     # See if anilist id is present in the info from zoro
#     anime_selected = get_info_by_zid(zid)
#     anilist_id = anime_selected["anime"]["info"]["anilistId"]
#     mal_id = anime_selected["anime"]["info"]["malId"]

#     # If not see if we can find the anilist id from the mal id using anilist graphql
#     # this will almost always work and we wont need to search for the anime by name
#     if not anilist_id:
#         print("Searching using graphql. Mal id:", mal_id)
#         anilist_graphql_url = "https://graphql.anilist.co"
#         query = """
#         query {{
#             Media(idMal: {mal_id}, type: ANIME) {{
#                 id
#             }}
#         }}
#         """.format(mal_id=mal_id)

#         response = requests.post(anilist_graphql_url, json={"query": query})
#         response = response.json()

#         if not "errors" in response:
#             anilist_id = response["data"]["Media"]["id"]

#     if not anilist_id:
#         anime_name = anime_selected['anime']['info']['name']
#         anime_name = parse_title_and_season(anime_name)["show_name"]
#         consumet_search_url = f"{os.getenv('CONSUMET_URL')}/meta/anilist/advanced-search?query={anime_name}&provider=zoro"
#         response = requests.get(consumet_search_url)
#         anime_search_results = response.json()

#         # compare where mal id is same and return the anilist id
#         for result in anime_search_results["results"]:
#             if result["malId"] == mal_id:
#                 anilist_id = result["id"]
#                 break
    
#     if anilist_id:
#         anime_fetched, provider = get_anime_by_id(anilist_id)
#         if "message" not in anime_fetched:
#             print("Updating anime with zid:", zid)
#             update_anime(anilist_id, anime_fetched, zid)
#             return redirect("watch:watch", anime_id=anilist_id)
    
#     return redirect("watch:watch_via_zid_mal_id", mal_id=mal_id, zid=zid)

# # same thing as watch, but with mal id and zid since anilist id is not available
# # context remains the same but data is not saved in database
# def watch_via_zid_mal_id(request, mal_id, zid):
#     anime_info = get_info_by_zid(zid)

#     mal_access_token = request.user.mal_access_token
#     if not mal_access_token:
#         u = User.objects.filter(mal_access_token__isnull=False).first()
#         mal_access_token = u.mal_access_token

#     anime_mal_info = get_single_anime_mal(mal_access_token, mal_id)
#     anime_episodes = get_episodes_by_zid(zid)
#     for index, episode in enumerate(anime_episodes["episodes"]):
#         episode_identifier = episode["episodeId"].split("?ep=")[1]
#         anime_episodes["episodes"][index]["episode"] = {
#             "identifier": episode_identifier,
#             "number": index + 1,
#         }

#     current_episode_number = 1
#     ep = request.GET.get("ep", None)

#     if ep:
#         current_episode_number = next((i + 1 for i, item in enumerate(anime_episodes["episodes"]) if item["episode"]["identifier"] == ep), 1)
#     else:
#         ep = anime_episodes["episodes"][0]["episode"]["identifier"]
#         return redirect(reverse("watch:watch_via_zid_mal_id", args=[mal_id, zid]) + f"?ep={ep}")

#     current_episode = anime_episodes["episodes"][int(current_episode_number) - 1]

#     mode = request.GET.get("mode", request.user.preferences.default_language)
#     if mode == "dub" and (not anime_info["anime"]["info"]["stats"]["episodes"]["dub"] or anime_info["anime"]["info"]["stats"]["episodes"]["dub"] < current_episode_number):
#         mode = "sub"

#     streaming_data = get_episode_streaming_data(current_episode["episodeId"], mode)
#     if "message" in streaming_data:
#         server, mode = find_alternate_server(current_episode["episodeId"], mode)
#         streaming_data = get_episode_streaming_data(current_episode["episodeId"], mode, server)

#     if streaming_data and "tracks" in streaming_data and not any(t["kind"] == "captions" for t in streaming_data["tracks"]) and mode == "dub" and request.user.preferences.ingrain_sub_subtitles_in_dub:
#         sub_streaming_data = get_episode_streaming_data(current_episode["episodeId"], "sub")
#         if "tracks" in sub_streaming_data:
#             captions = [t for t in sub_streaming_data["tracks"] if t["kind"] == "captions"]
#             if captions:
#                 streaming_data["tracks"].extend(captions)

#     anime = {
#         "id": mal_id,
#         "malId": mal_id,
#         "z_anime_id": zid,
#         "description": anime_info["anime"]["info"]["description"],
#         "image": anime_info["anime"]["info"]["poster"].replace("300x400/100", "600x800/100"),
#         "countryOfOrigin": "JP",
#         "titles": {
#             "english": anime_mal_info["alternative_titles"]["en"] if mal_id else anime_info["anime"]["info"]["name"],
#             "romaji": anime_mal_info["title"] if mal_id else anime_info["anime"]["info"]["name"],
#             "native": anime_mal_info["alternative_titles"]["ja"] if mal_id else anime_info["anime"]["moreInfo"]["japanese"],
#         },
#         "type": anime_mal_info["media_type"].replace("_", " ").title() if mal_id else anime_info["anime"]["info"]["stats"]["type"],
#         "popularity": anime_mal_info["popularity"] if mal_id else 0,
#         "releaseDate": anime_mal_info["start_date"].split("-")[0] if mal_id else anime_info["anime"]["moreInfo"]["aired"],
#         "totalEpisodes": anime_mal_info["num_episodes"] if mal_id else len(anime_episodes["episodes"]),
#         "currentEpisode": len(anime_episodes["episodes"]),
#         "rating": anime_mal_info["mean"] if mal_id else 0,
#         "duration": anime_mal_info["average_episode_duration"] // 60 + 1 if mal_id else anime_info["anime"]["moreInfo"]["duration"],
#         "genres": {
#             "all": anime_mal_info["genres"] if mal_id else [{"name": g} for g in anime_info["anime"]["moreInfo"]["genres"]],
#         },
#         "status": anime_mal_info["status"].replace("_", " ").title() if mal_id else anime_info["anime"]["moreInfo"]["status"],
#         "season": anime_mal_info["start_season"]["season"].title() if mal_id else None,
#         "studios": {
#             "all": anime_mal_info["studios"] if mal_id else [{"name": anime_info["anime"]["moreInfo"]["studios"]}],
#         },
#         "sub": anime_info["anime"]["info"]["stats"]["episodes"].get("sub", 0),
#         "dub": anime_info["anime"]["info"]["stats"]["episodes"].get("dub", 0),
#     }

#     related = []
#     for r in anime_info["relatedAnimes"]:
#         rd = {
#             "zid": r["id"],
#             "image": r["poster"].replace("300x400/100", "600x800/100"),
#             "title": {
#                 "english": r["name"],
#                 "romaji": r["jname"]
#             },
#             "episodes": r["episodes"]["sub"],
#             "type": r["type"],
#         }

#         related.append(rd)

#     recommended = []
#     for r in anime_info["recommendedAnimes"]:
#         rd = {
#             "zid": r["id"],
#             "image": r["poster"].replace("300x400/100", "600x800/100"),
#             "title": {
#                 "english": r["name"],
#                 "romaji": r["jname"]
#             },
#             "episodes": r["episodes"]["sub"],
#             "type": r["type"],
#         }

#     characters = []
#     for c in anime_info["anime"]["info"]["charactersVoiceActors"]:
#         cd = {
#             "name": {
#                 "full": c["character"]["name"],
#                 "natve": c["character"]["name"],
#             },
#             "image": c["character"]["poster"].replace("100x100/100", "200x200/100"),
#             "role": c["character"]["cast"],
#             "voiceActors": [
#                {
#                      "name": {
#                           "full": c["voiceActor"]["name"],
#                           "native": c["voiceActor"]["name"],
#                      },
#                      "image": c["voiceActor"]["poster"].replace("100x100/100", "200x200/100"),
#                      "language": "Japanese",
#                }
#             ],
#         }

#         characters.append(cd)

#     context = {
#         "anime": anime,
#         "current_episode_number": current_episode_number,
#         "current_episode": current_episode,
#         "all_episodes": anime_episodes["episodes"],
#         "streaming_data": streaming_data,
#         "stream_url": streaming_data["sources"][0]["url"] if streaming_data and "sources" in streaming_data else None,
#         "watched_episodes": [],
#         "current_watched_time": 0,
#         "mode": mode,
#         "seasons": get_seasons_by_zid(zid),
#         "viaMal": True,
#         "related": related,
#         "recommendations": recommended,
#         "characters": characters,
#     }

#     if request.user.mal_access_token and mal_id:
#         context["mal_data"] = anime_mal_info
#         context["mal_episode_range"] = range(1, anime_mal_info["num_episodes"] + 1)

#     return render(request, "watch/watch.html", context)

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
