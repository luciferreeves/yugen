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
def get_anime_data(anime_id, provider="gogo", dub=False):
    if provider == "gogo":
        provider = "gogoanime"

    print(f"Fetching anime data: ID={anime_id}, provider={provider}, initial dub={dub}")

    sub_cache_key = f"anime_{anime_id}_anime_data_{provider}_sub"
    dub_cache_key = f"anime_{anime_id}_anime_data_{provider}_dub"
    sub_dub_cache_key = f"anime_{anime_id}_anime_data_{provider}_sub_dub_count"

    if not dub:
        anime_data = get_from_redis_cache(sub_cache_key)
    else:
        anime_data = get_from_redis_cache(dub_cache_key)

    if not anime_data:
        sub_dub_count = {
            "sub": 0,
            "dub": 0
        }

        base_url = f"{os.getenv('CONSUMET_URL')}/meta/anilist/info/{anime_id}?provider={provider}"
        print(f"Trying URL: {base_url}")
        response = requests.get(base_url, timeout=10)
        sub_data = response.json()

        if "status" in sub_data and sub_data["status"] == "Completed":
            store_in_redis_cache(sub_cache_key, json.dumps(sub_data), 3600 * 24 * 30)
        else:
            store_in_redis_cache(sub_cache_key, json.dumps(sub_data), 3600 * 12)
        sub_dub_count["sub"] = len(sub_data["episodes"])

        base_url = f"{os.getenv('CONSUMET_URL')}/meta/anilist/info/{anime_id}?provider={provider}&dub=true"
        print(f"Trying URL: {base_url}")
        response = requests.get(base_url, timeout=10)
        dub_data = response.json()
        if "status" in dub_data and dub_data["status"] == "Completed":
            store_in_redis_cache(dub_cache_key, json.dumps(dub_data), 3600 * 24 * 30)
        else:
            store_in_redis_cache(dub_cache_key, json.dumps(dub_data), 3600 * 12)
        sub_dub_count["dub"] = len(dub_data["episodes"])

        if not dub:
            anime_data = sub_data
        else:
            anime_data = dub_data

        if anime_data["status"] == "Completed":
            store_in_redis_cache(sub_dub_cache_key, json.dumps(sub_dub_count), 3600 * 24 * 30)
        else:
            store_in_redis_cache(sub_dub_cache_key, json.dumps(sub_dub_count), 3600 * 12)

        anime_data["subDubCount"] = sub_dub_count
    else:   
        anime_data = json.loads(anime_data)
        anime_data["subDubCount"] = json.loads(get_from_redis_cache(sub_dub_cache_key))

    for i, episode in enumerate(anime_data["episodes"], start=1):
        episode["number"] = i

    return anime_data


def find_zoro_server (episode_id, mode):
    base_url = f"{os.getenv('ZORO_URL')}/anime/servers?episodeId={episode_id}"
    print(base_url)
    response = requests.get(base_url)
    response = response.json()

    if "message" in response:
        return None, mode

    if mode == "dub" and "dub" in response and len(response["dub"]) > 0:
        server_id = response["dub"][0]["serverName"]
        mode = "dub"
    elif len(response["sub"]) > 0 and "sub" in response:
        server_id = response["sub"][0]["serverName"]
        mode = "sub"
    elif len(response["raw"]) > 0:
        server_id = response["raw"][0]["serverName"]
        mode = "raw"

    return server_id, mode


@lru_cache(maxsize=100)
def get_zoro_episode_streaming_data(episode_url, dub=False):
    episode_url = episode_url.split("watch/")[1]
    cache_key = f"zoro_episode_streaming_data_{episode_url}_{'dub' if dub else 'sub'}"
    episode_data = get_from_redis_cache(cache_key)
    category = "dub" if dub else "sub"
    server, category = find_zoro_server(episode_url, category)
    if not episode_data:
        base_url = f"{os.getenv('ZORO_URL')}/anime/episode-srcs?id={episode_url}&category={category}&server={server}"
        print(f"Trying URL: {base_url}")
        response = requests.get(base_url, timeout=10)
        episode_data = response.json()

        if "message" not in episode_data:
            store_in_redis_cache(cache_key, json.dumps(episode_data), 3600 * 12)
    else:
        episode_data = json.loads(episode_data)

    return episode_data

@lru_cache(maxsize=100)
def get_gogo_episode_streaming_data(episode_id):
    cache_key = f"gogo_episode_streaming_data_{episode_id}"
    episode_data = get_from_redis_cache(cache_key)
    if not episode_data:
        base_url = f"{os.getenv('CONSUMET_URL')}/meta/anilist/watch/{episode_id}"
        print(f"Trying URL: {base_url}")
        response = requests.get(base_url, timeout=10)
        episode_data = response.json()
        store_in_redis_cache(cache_key, json.dumps(episode_data), 3600 * 12)
    else:
        episode_data = json.loads(episode_data)

    return convert_gogo_stream_data(episode_data)

def convert_gogo_stream_data(input_data):
    # Create the new structure
    new_data = {
        'tracks': [],
        'intro': {'start': 0, 'end': 0},
        'outro': {'start': 0, 'end': 0},
        'sources': [],
        'anilistID': 0,
        'malID': 0
    }
    
    # Add the default stream to sources
    default_source = next((s for s in input_data['sources'] if s['quality'] == 'default'), None)
    if default_source:
        new_data['sources'].append({
            'url': default_source['url'],
            'type': 'hls'
        })
    
    return new_data

def fetch_anime_seasons(anime_id):
    url = 'https://graphql.anilist.co'
    query = '''
    query ($id: Int) {
        Media(id: $id, type: ANIME) {
            id
            title {
                romaji
                english
                native
                userPreferred
            }
            format
            episodes
            startDate {
                year
            }
            coverImage {
                large
                medium
            }
            bannerImage
            relations {
                edges {
                    relationType(version: 2)
                    node {
                        ... on Media {
                            id
                            title {
                                romaji
                                english
                                native
                                userPreferred
                            }
                            format
                            episodes
                            startDate {
                                year
                            }
                            coverImage {
                                large
                                medium
                            }
                            bannerImage
                            relations {
                                edges {
                                    relationType(version: 2)
                                    node {
                                        ... on Media {
                                            id
                                            title {
                                                romaji
                                                english
                                                native
                                                userPreferred
                                            }
                                            format
                                            episodes
                                            startDate {
                                                year
                                            }
                                            coverImage {
                                                large
                                                medium
                            }
                                            bannerImage
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    '''
    variables = {'id': anime_id}
    response = requests.post(url, json={'query': query, 'variables': variables})
    return response.json()

def extract_seasons(data):
    seasons = {}
    main_title = data['data']['Media']['title']['english'] or data['data']['Media']['title']['romaji']
    main_title_words = set(main_title.lower().split())

    def is_related_content(title):
        title_words = set(title.lower().split())
        return len(main_title_words.intersection(title_words)) >= 2 or 'season' in title.lower()

    def add_content(media):
        if media['format'] in ['TV', 'SPECIAL', 'MOVIE', 'OVA', 'ONA']:
            english_title = media['title']['english'] or ''
            romaji_title = media['title']['romaji'] or ''
            
            if is_related_content(english_title) or is_related_content(romaji_title):
                seasons[media['id']] = {
                    'id': media['id'],
                    'title': media['title'],
                    'format': media['format'],
                    'episodes': media['episodes'],
                    'startYear': media['startDate']['year'] if media['startDate']['year'] else 9999,
                    'coverImage': media['coverImage']['large'] if media['coverImage'] else None,
                    'bannerImage': media['bannerImage']
                }

    def process_relations(relations):
        for edge in relations['edges']:
            if edge['relationType'] in ['SEQUEL', 'PREQUEL', 'ALTERNATIVE', 'SPIN_OFF', 'SIDE_STORY', 'PARENT', 'SUMMARY']:
                node = edge['node']
                add_content(node)
                if 'relations' in node:
                    process_relations(node['relations'])

    main_media = data['data']['Media']
    add_content(main_media)
    process_relations(main_media['relations'])

    return sorted(seasons.values(), key=lambda x: (x['startYear'], x['id']))

def get_anime_seasons(anime_id):
    cache_key = f"anime_{anime_id}_seasons"
    fetched_data = get_from_redis_cache(cache_key)
    if not fetched_data:
        fetched_data = fetch_anime_seasons(anime_id)
        seasons = extract_seasons(fetched_data)
        store_in_redis_cache(cache_key, json.dumps(seasons), 3600 * 12)
    else:
        seasons = json.loads(fetched_data)

    return seasons





    # if not anime_data:
    #     subDubCount = {
    #         "sub": 0,
    #         "dub": 0
    #     }
        
    #     base_url = f"{os.getenv('CONSUMET_URL')}/meta/zoro/anime/info/{anime_id}?provider={provider}?dub=false"

    #     print(f"Trying URL: {base_url}")
    #     response = requests.get(base_url, timeout=10)
    #     data = response.json()

    #     store_in_redis_cache(f"{cache_key}_sub", json.dumps(data), 3600 * 24 * 30)
    #     subDubCount["sub"] = len(data["episodes"])

    #     base_url = f"{os.getenv('CONSUMET_URL')}/meta/zoro/anime/info/{anime_id}?provider={provider}?dub=true"

    #     print(f"Trying URL: {base_url}")
    #     response = requests.get(base_url, timeout=10)
    #     data = response.json()

    #     store_in_redis_cache(f"{cache_key}_dub", json.dumps(data), 3600 * 24 * 30)
    #     subDubCount["dub"] = len(data["episodes"])

    #     anime_data = {
    #         "subDubCount": subDubCount
    #     }

        




# @lru_cache(maxsize=100)
# def get_anime_data(anime_id, provider="zoro", gogodub=False):
#     cache_key = f"anime_{anime_id}_anime_data_{provider}"
#     anime_data = get_from_redis_cache(cache_key)
#     original_provider = provider

#     if provider == "gogo":
#         provider = "gogoanime"
    
#     print(f"Fetching anime data: ID={anime_id}, provider={provider}, initial gogodub={gogodub}")
    
#     if not anime_data:
#         base_url = f"{os.getenv('CONSUMET_URL')}/meta/anilist/info/{anime_id}?provider={provider}"
        
#         def fetch_data(dub):
#             url = base_url + ("&dub=true" if dub else "")
#             print(f"Trying URL: {url}")
#             response = requests.get(url, timeout=10)
#             data = response.json()
#             return data if "message" not in data and response.status_code == 200 else None

#         # Try to fetch the requested version (dub or sub)
#         anime_data = fetch_data(gogodub)
        
#         # If dub was requested but not found, try sub
#         if gogodub and not anime_data:
#             print(f"No dub episodes found for ID {anime_id}, trying sub")
#             anime_data = fetch_data(False)
#             if anime_data:
#                 gogodub = False  # We found sub episodes, so set gogodub to False

#         # If we still don't have data, try switching providers
#         if not anime_data:
#             if original_provider != "gogo":
#                 print(f"No episodes found for ID {anime_id} with {provider}, switching to gogo")
#                 return get_anime_data(anime_id, "gogo", gogodub)
#             else:
#                 print(f"No episodes found for ID {anime_id} with any provider or mode")
#                 return anime_data, provider, gogodub

#         # We have valid data at this point
#         episode_count = len(anime_data["episodes"])
#         print(f"Found {episode_count} episodes for ID {anime_id}, gogodub={gogodub}")

#         # Cache the data
#         cache_key = f"anime_{anime_id}_anime_data_{provider}_{'dub' if gogodub else 'sub'}"
#         if anime_data["status"] == "Completed":
#             store_in_redis_cache(cache_key, json.dumps(anime_data), 3600 * 24 * 30)
#         else:
#             store_in_redis_cache(cache_key, json.dumps(anime_data), 3600 * 12)
        
#         print(f"Anime data found: ID={anime_id}, provider={provider}, final gogodub={gogodub}, episodes={episode_count}")
#     else:
#         anime_data = json.loads(anime_data)
#         episode_count = len(anime_data.get("episodes", []))
#         print(f"Loaded cached anime data: ID={anime_id}, provider={provider}, gogodub={gogodub}, episodes={episode_count}")

#     if provider == "gogoanime":
#         provider = "gogo"

#     print(f"Returning: provider={provider}, gogodub={gogodub}")
#     return anime_data, provider, gogodub


# @lru_cache(maxsize=100)
# def get_anime_episodes(anime_id): #only returns episodes from zoro
#     cache_key = f"anime_{anime_id}_anime_episodes_zoro"
#     anime_episodes = get_from_redis_cache(cache_key)
    
#     if not anime_episodes:
#         anime_data, provider, gd = get_anime_data(anime_id, "zoro")
#         if not anime_data or not anime_data.get("episodes"):
#             return []

#         z_anime_id = anime_data["episodes"][0]["id"].split("$")[0]

#         print(f"Fetching episodes for ID {anime_id} with Zoro ID {z_anime_id}")

#         base_url = f"{os.getenv('CONSUMET_URL')}/meta/zoro/anime/episodes/{z_anime_id}"
#         try:
#             response = requests.get(base_url, timeout=10)
#             anime_episodes = response.json()
#             store_in_redis_cache(cache_key, json.dumps(anime_episodes), 86400)  # Cache for 24 hours
#         except requests.RequestException as e:
#             print(f"Error fetching anime episodes for ID {anime_id}: {e}")
#             return []
#     else:
#         anime_episodes = json.loads(anime_episodes)

#     return anime_episodes

# @lru_cache(maxsize=100)
# def get_anime_episodes_gogo(anime_id, mode="sub"):
#     cache_key = f"anime_{anime_id}_anime_episodes_gogo_{mode}"
#     anime_episodes = get_from_redis_cache(cache_key)
    
#     if not anime_episodes:
#         gogodub = True if mode == "dub" else False
#         print(f"Fetching episodes for ID {anime_id} with mode {mode} and dub=>{gogodub}")
#         anime_data, provider, gd = get_anime_data(anime_id, "gogo", gogodub)
#         if anime_data and "episodes" in anime_data:
#             anime_episodes = anime_data["episodes"]
#             store_in_redis_cache(cache_key, json.dumps(anime_episodes), 86400)
#         else:
#             anime_episodes = []
#     else:
#         anime_episodes = json.loads(anime_episodes)

#     # Convert everything to 1-based index
#     for i, episode in enumerate(anime_episodes, start=1):
#         episode["number"] = i

#     anime_episode_data = {
#         "episodes": anime_episodes,
#         "totalEpisodes": len(anime_episodes)
#     }

#     print(f"Returning {len(anime_episodes)} episodes for ID {anime_id} with mode {mode}")

#     return anime_episode_data, mode


def attach_episode_metadata(anime_data, anime_episodes):
    anime_episodes_metadata = get_all_episode_metadata(anime_data)
    if anime_episodes_metadata:
        for i, episode in enumerate(anime_episodes):
            if i < len(anime_episodes_metadata):
                episode["metadata"] = anime_episodes_metadata[i]
            else:
                episode["metadata"] = None

    return anime_episodes

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


def update_anime_user_history(user, anime, episode, time_watched, additional_data=None):
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

    if additional_data:
        if "anime_title_english" in additional_data:
            history.anime_title_english = additional_data["anime_title_english"]
        else:
            history.anime_title_english = ""
        if "anime_title_romaji" in additional_data:
            history.anime_title_romaji = additional_data["anime_title_romaji"]
        else:
            history.anime_title_romaji = ""
        if "anime_title_native" in additional_data:
            history.anime_title_native = additional_data["anime_title_native"]
        else:
            history.anime_title_native = ""
        if "anime_cover_image" in additional_data:
            history.anime_cover_image = additional_data["anime_cover_image"]
        else:
            history.anime_cover_image = ""
        if "episode_title" in additional_data:
            history.episode_title = additional_data["episode_title"]
        else:
            history.episode_title = ""

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
