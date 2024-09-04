import datetime
import json
import redis
import os
import dotenv
from user_profile.models import UserHistory
from watch.tmdbmapper import get_anime_episodes, get_tv_episode_group_details

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
            episode_metadata = get_anime_episodes(anime_data)
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
