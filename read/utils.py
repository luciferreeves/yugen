import json
import os

import requests
from watch.utils import get_from_redis_cache, store_in_redis_cache


def get_manga_data(manga_id):
    print(f"Fetching manga data: ID={manga_id}")

    cache_key = f"manga_{manga_id}_manga_data"
    manga_data = get_from_redis_cache(cache_key)

    if not manga_data:
        base_url = f"{os.getenv('CONSUMET_URL')}/meta/anilist-manga/info/{manga_id}"
        print(f"Trying URL: {base_url}")
        response = requests.get(base_url, timeout=10)
        manga_data = response.json()

        if "message" in manga_data:
            return None
        
        if "status" in manga_data and manga_data["status"] == "Completed":
            store_in_redis_cache(cache_key, json.dumps(manga_data), 3600 * 24 * 30)
        else:
            store_in_redis_cache(cache_key, json.dumps(manga_data), 3600 * 24)
    else:
        manga_data = json.loads(manga_data)

    return manga_data
