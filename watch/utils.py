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

r.flushall()
print("Redis cache flushed")

def get_episode_metadata(anime_data, episode):
    episode_metadata = get_all_episode_metadata(anime_data)
    current_episode_metadata = episode_metadata[episode - 1] if len(episode_metadata) >= episode else None
    return current_episode_metadata

@lru_cache(maxsize=100)
def get_anime_data(anime_id):
    cache_key = f"anime_{anime_id}_anime_data"
    anime_data = get_from_redis_cache(cache_key)
    provider = get_from_redis_cache(f"anime_{anime_id}_provider")
    if not provider:
        provider = "zoro"
    if not anime_data:
        base_url = f"{os.getenv('CONSUMET_URL')}/meta/anilist/info/{anime_id}?provider=zoro"
        try:
            response = requests.get(base_url, timeout=10)
            anime_data = response.json()
            if ("message" not in anime_data or response.status_code == 200) and anime_data["episodes"]:
                if anime_data["status"] == "Completed":
                    store_in_redis_cache(cache_key, json.dumps(anime_data), 3600 * 24 * 30)  # Cache for 30 days
                else:
                    store_in_redis_cache(cache_key, json.dumps(anime_data), 3600 * 12) # Cache for 12 hours
                store_in_redis_cache(f"anime_{anime_id}_provider", "zoro")
            else:
                provider = "gogo"
                base_url = f"{os.getenv('CONSUMET_URL')}/meta/anilist/info/{anime_id}"
                response = requests.get(base_url, timeout=10)
                anime_data = response.json()
                store_in_redis_cache(cache_key, json.dumps(anime_data), 3600 * 12) # Cache for 12 hours
                store_in_redis_cache(f"anime_{anime_id}_provider", "gogo")
        except requests.RequestException as e:
            print(f"Error fetching anime data for ID {anime_id}: {e}")
            return None
    else:
        anime_data = json.loads(anime_data)

    if not anime_data:
        print(f"Anime data not found for ID {anime_id}")
    
    return anime_data, provider

@lru_cache(maxsize=100)
def get_anime_episodes(anime_id):
    cache_key = f"anime_{anime_id}_anime_episodes"
    anime_episodes = get_from_redis_cache(cache_key)

    if not anime_episodes:
        anime_data, provider = get_anime_data(anime_id)
        if not anime_data or not anime_data.get("episodes"):
            return None
        
        if provider == "zoro":
            if "mappings" in anime_data:
                z_anime_id = next((m["id"] for m in anime_data["mappings"] if m["providerId"] == "zoro"), None)
                z_anime_id = z_anime_id.split("/")[-1] if z_anime_id else None
            else:
                z_anime_id = anime_data["episodes"][0]["id"].split("$")[0]

            print(f"Fetching episodes for ID {anime_id} with Zoro ID {z_anime_id}")

            base_url = f"{os.getenv('ZORO_URL')}/anime/episodes/{z_anime_id}"
            try:
                response = requests.get(base_url, timeout=10)
                anime_episodes = response.json()
                store_in_redis_cache(cache_key, json.dumps(anime_episodes), 86400)  # Cache for 24 hours
            except requests.RequestException as e:
                print(f"Error fetching anime episodes for ID {anime_id}: {e}")
                return None
        else:
            return {"episodes": anime_data["episodes"], "totalEpisodes": len(anime_data["episodes"])}
    else:
        anime_episodes = json.loads(anime_episodes)
    
    return anime_episodes

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
