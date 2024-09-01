import redis
import os
import dotenv
from user_profile.models import UserHistory

dotenv.load_dotenv()

r = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=6379,
    password=os.getenv("REDIS_PASSWORD"),
    ssl=True,
)

def update_anime_user_history(user, anime_id, episode, time_watched):
    # per episode history
    history, created = UserHistory.objects.get_or_create(user=user, anime_id=anime_id, episode=episode)
    history.time_watched = time_watched

    # last watched
    last_watched = UserHistory.objects.filter(user=user, anime_id=anime_id, last_watched=True)
    if last_watched:
        last_watched = last_watched[0]
        last_watched.last_watched = False
        last_watched.save()

    history.last_watched = True
    history.save()

def get_anime_user_history(user, anime_id):
    history = UserHistory.objects.filter(user=user, anime_id=anime_id).order_by("-episode")
    return history


def store_in_redis_cache(anime_id, data):
    try:
        r.set(anime_id, data, ex=60*60) # 1 hour
    except Exception as e:
        print(e)
        pass

def get_from_redis_cache(anime_id):
    data = r.get(anime_id)
    return data
