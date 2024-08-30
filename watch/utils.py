import redis
import os
import dotenv

dotenv.load_dotenv()

r = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=6379,
    password=os.getenv("REDIS_PASSWORD"),
    ssl=True,
)

def store_in_redis_cache(anime_id, data):
    r.set(anime_id, data, ex=60*60*24*30) # 30 days
    print("data cached", anime_id)

def get_from_redis_cache(anime_id):
    data = r.get(anime_id)
    print("data fetched from cache", anime_id)
    return data
