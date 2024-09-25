import datetime
from functools import lru_cache
import json
import redis
import os
import dotenv
import requests
from user_profile.models import UserHistory
from watch.tmdbmapper import get_anime_episodes as gae, get_tv_episode_group_details

dotenv.load_dotenv()

r = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=os.getenv("REDIS_PORT"),
    password=os.getenv("REDIS_PASSWORD"),
)

# r.flushall()
# print("Redis cache flushed")

def get_episode_metadata(anime_data, episode):
    episode_metadata = get_all_episode_metadata(anime_data)
    current_episode_metadata = episode_metadata[episode - 1] if len(episode_metadata) >= episode else None
    return current_episode_metadata

@lru_cache(maxsize=100)
def get_anime_data(anime_id, provider="zoro", gogodub=False):
    cache_key = f"anime_{anime_id}_anime_data_{provider}"
    anime_data = get_from_redis_cache(cache_key)
    original_provider = provider

    if provider == "gogo":
        provider = "gogoanime"
    
    print(f"Fetching anime data: ID={anime_id}, provider={provider}, initial gogodub={gogodub}")
    
    if not anime_data:
        base_url = f"{os.getenv('CONSUMET_URL')}/meta/anilist/info/{anime_id}?provider={provider}"
        
        def fetch_data(dub):
            url = base_url + ("&dub=true" if dub else "")
            print(f"Trying URL: {url}")
            response = requests.get(url, timeout=10)
            data = response.json()
            return data if "message" not in data and response.status_code == 200 else None

        # Try to fetch the requested version (dub or sub)
        anime_data = fetch_data(gogodub)
        
        # If dub was requested but not found, try sub
        if gogodub and not anime_data:
            print(f"No dub episodes found for ID {anime_id}, trying sub")
            anime_data = fetch_data(False)
            if anime_data:
                gogodub = False  # We found sub episodes, so set gogodub to False

        # If we still don't have data, try switching providers
        if not anime_data:
            if original_provider != "gogo":
                print(f"No episodes found for ID {anime_id} with {provider}, switching to gogo")
                return get_anime_data(anime_id, "gogo", gogodub)
            else:
                print(f"No episodes found for ID {anime_id} with any provider or mode")
                return anime_data, provider, gogodub

        # We have valid data at this point
        episode_count = len(anime_data["episodes"])
        print(f"Found {episode_count} episodes for ID {anime_id}, gogodub={gogodub}")

        # Cache the data
        cache_key = f"anime_{anime_id}_anime_data_{provider}_{'dub' if gogodub else 'sub'}"
        if anime_data["status"] == "Completed":
            store_in_redis_cache(cache_key, json.dumps(anime_data), 3600 * 24 * 30)
        else:
            store_in_redis_cache(cache_key, json.dumps(anime_data), 3600 * 12)
        
        print(f"Anime data found: ID={anime_id}, provider={provider}, final gogodub={gogodub}, episodes={episode_count}")
    else:
        anime_data = json.loads(anime_data)
        episode_count = len(anime_data.get("episodes", []))
        print(f"Loaded cached anime data: ID={anime_id}, provider={provider}, gogodub={gogodub}, episodes={episode_count}")

    if provider == "gogoanime":
        provider = "gogo"

    print(f"Returning: provider={provider}, gogodub={gogodub}")
    return anime_data, provider, gogodub

@lru_cache(maxsize=100)
def get_anime_episodes(anime_id): #only returns episodes from zoro
    cache_key = f"anime_{anime_id}_anime_episodes_zoro"
    anime_episodes = get_from_redis_cache(cache_key)
    
    if not anime_episodes:
        anime_data, provider, gd = get_anime_data(anime_id, "zoro")
        if not anime_data or not anime_data.get("episodes"):
            return []

        z_anime_id = anime_data["episodes"][0]["id"].split("$")[0]

        print(f"Fetching episodes for ID {anime_id} with Zoro ID {z_anime_id}")

        base_url = f"{os.getenv('CONSUMET_URL')}/meta/zoro/anime/episodes/{z_anime_id}"
        try:
            response = requests.get(base_url, timeout=10)
            anime_episodes = response.json()
            store_in_redis_cache(cache_key, json.dumps(anime_episodes), 86400)  # Cache for 24 hours
        except requests.RequestException as e:
            print(f"Error fetching anime episodes for ID {anime_id}: {e}")
            return []
    else:
        anime_episodes = json.loads(anime_episodes)

    return anime_episodes

@lru_cache(maxsize=100)
def get_anime_episodes_gogo(anime_id, mode="sub"):
    cache_key = f"anime_{anime_id}_anime_episodes_gogo_{mode}"
    anime_episodes = get_from_redis_cache(cache_key)
    
    if not anime_episodes:
        gogodub = True if mode == "dub" else False
        print(f"Fetching episodes for ID {anime_id} with mode {mode} and dub=>{gogodub}")
        anime_data, provider, gd = get_anime_data(anime_id, "gogo", gogodub)
        if anime_data and "episodes" in anime_data:
            anime_episodes = anime_data["episodes"]
            store_in_redis_cache(cache_key, json.dumps(anime_episodes), 86400)
        else:
            anime_episodes = []
    else:
        anime_episodes = json.loads(anime_episodes)

    # Convert everything to 1-based index
    for i, episode in enumerate(anime_episodes, start=1):
        episode["number"] = i

    anime_episode_data = {
        "episodes": anime_episodes,
        "totalEpisodes": len(anime_episodes)
    }

    print(f"Returning {len(anime_episodes)} episodes for ID {anime_id} with mode {mode}")

    return anime_episode_data, mode


# @lru_cache(maxsize=100)
# def get_anime_episodes(anime_id, provider="zoro"):
#     cache_key = f"anime_{anime_id}_anime_episodes_{provider}"
#     anime_episodes = get_from_redis_cache(cache_key)

#     if not anime_episodes:
#         anime_data, provider = get_anime_data(anime_id, provider)
#         if not anime_data or not anime_data.get("episodes"):
#             return None
        
#         if provider == "zoro":
#             if "mappings" in anime_data:
#                 z_anime_id = next((m["id"] for m in anime_data["mappings"] if m["providerId"] == "zoro"), None)
#                 z_anime_id = z_anime_id.split("/")[-1] if z_anime_id else None
#             else:
#                 z_anime_id = anime_data["episodes"][0]["id"].split("$")[0]

#             print(f"Fetching episodes for ID {anime_id} with Zoro ID {z_anime_id}")

#             base_url = f"{os.getenv('ZORO_URL')}/anime/episodes/{z_anime_id}"
#             try:
#                 response = requests.get(base_url, timeout=10)
#                 anime_episodes = response.json()
#                 store_in_redis_cache(cache_key, json.dumps(anime_episodes), 86400)  # Cache for 24 hours
#             except requests.RequestException as e:
#                 print(f"Error fetching anime episodes for ID {anime_id}: {e}")
#                 return None
#         else:
#             return {"episodes": anime_data["episodes"], "totalEpisodes": len(anime_data["episodes"])}
#     else:
#         anime_episodes = json.loads(anime_episodes)
    
#     return anime_episodes

def attach_episode_metadata(anime_data, anime_episodes):
    anime_episodes_metadata = get_all_episode_metadata(anime_data)
    if anime_episodes_metadata:
        for i, episode in enumerate(anime_episodes.get("episodes", [])):
            if i < len(anime_episodes_metadata):
                episode["metadata"] = anime_episodes_metadata[i]

def get_info_by_zid(zid):
    cache_key = f"anime_{zid}_anime_selected"
    print(cache_key)
    try:
        anime_selected = get_from_redis_cache(cache_key)
        anime_selected = json.loads(anime_selected)
    except:
        base_url = f"{os.getenv('ZORO_URL')}/anime/info?id={zid}"
        response = requests.get(base_url)
        anime_selected = response.json()

        if "message" not in anime_selected:
            store_in_redis_cache(cache_key, json.dumps(anime_selected), 3600 * 12)

    return anime_selected

def get_seasons_by_zid(zid):
    if not zid:
        return []

    fetched_info = get_info_by_zid(zid)
    seasons = fetched_info["seasons"] if "seasons" in fetched_info else []

    for season in seasons:
        season["poster"] = season["poster"].replace("100x200/100", "400x800/100")

    return seasons

def get_episodes_by_zid(z_anime_id):
    cache_key = f"anime_{z_anime_id}_episodes"
    try:
        fetched_episodes = get_from_redis_cache(cache_key)
        fetched_episodes = json.loads(fetched_episodes)
    except:
        base_url = f"{os.getenv('ZORO_URL')}/anime/episodes/{z_anime_id}"
        response = requests.get(base_url)
        fetched_episodes = response.json()
        store_in_redis_cache(cache_key, json.dumps(fetched_episodes), 3600 * 12)

    return fetched_episodes

def get_all_episode_metadata(anime_data):
    special_case = False

    special_cases = {
        "Clannad": "5de8c6127646fd00139b883d",
        "Clannad: After Story": "5de8c6bda313b80012935f55"
    }

    if anime_data["title"]["english"] in special_cases:
        special_case = True

    episode_metadata = get_from_redis_cache(f"anime_{anime_data['id']}_episode_metadata")
    if episode_metadata:
        episode_metadata = json.loads(episode_metadata)
    else:
        if not special_case:
            episode_metadata = gae(anime_data)
        else:
            group_id = special_cases[anime_data["title"]["english"]]
            episode_metadata = get_tv_episode_group_details(group_id)

        store_in_redis_cache(f"anime_{anime_data['id']}_episode_metadata", json.dumps(episode_metadata))

    # Special cases
    if anime_data["title"]["english"] == "Attack on Titan Final Season THE FINAL CHAPTERS Special 1":
        episode_metadata.insert(0, episode_metadata[0])

    return episode_metadata


def update_anime_user_history(user, anime, episode, time_watched):
    # per episode history
    history, created = UserHistory.objects.get_or_create(user=user, anime=anime, episode=episode)
    history.time_watched = time_watched

    # last watched
    last_watched = UserHistory.objects.filter(user=user, anime=anime, last_watched=True)
    if last_watched:
        last_watched = last_watched[0]
        last_watched.last_watched = False
        last_watched.save()

    history.last_watched = True
    history.last_updated = datetime.datetime.now()
    history.save()

def get_anime_user_history(user, anime):
    history = UserHistory.objects.filter(user=user, anime=anime)
    return history


def store_in_redis_cache(anime_id, data, cache_time=60*60*12):
    try:
        print("Storing in cache=>", anime_id)
        r.set(anime_id, data, ex=cache_time) # 1 hour
    except Exception as e:
        print(e)
        pass

def get_from_redis_cache(anime_id):
    data = r.get(anime_id)
    return data if data else None
