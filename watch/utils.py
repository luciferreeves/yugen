from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
from difflib import SequenceMatcher
from functools import lru_cache
import html
import json
import math
import random
import re
import redis
import bbcode
from bs4 import BeautifulSoup
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

        if "message" in sub_data:
            return None

        if "status" in sub_data and sub_data["status"] == "Completed":
            store_in_redis_cache(sub_cache_key, json.dumps(sub_data), 3600 * 24 * 30)
        else:
            store_in_redis_cache(sub_cache_key, json.dumps(sub_data), 3600 * 12)
        sub_dub_count["sub"] = len(sub_data["episodes"]) if "episodes" in sub_data else 0

        base_url = f"{os.getenv('CONSUMET_URL')}/meta/anilist/info/{anime_id}?provider={provider}&dub=true"
        print(f"Trying URL: {base_url}")
        response = requests.get(base_url, timeout=10)
        dub_data = response.json()
        if "status" in dub_data and dub_data["status"] == "Completed":
            store_in_redis_cache(dub_cache_key, json.dumps(dub_data), 3600 * 24 * 30)
        else:
            store_in_redis_cache(dub_cache_key, json.dumps(dub_data), 3600 * 12)
        sub_dub_count["dub"] = len(dub_data["episodes"]) if "episodes" in dub_data else 0

        if not dub:
            anime_data = sub_data
        else:
            anime_data = dub_data

        if "status" in anime_data and anime_data["status"] == "Completed":
            store_in_redis_cache(sub_dub_cache_key, json.dumps(sub_dub_count), 3600 * 24 * 30)
        else:
            store_in_redis_cache(sub_dub_cache_key, json.dumps(sub_dub_count), 3600 * 12)

        anime_data["subDubCount"] = sub_dub_count
    else:   
        anime_data = json.loads(anime_data)
        anime_data["subDubCount"] = json.loads(get_from_redis_cache(sub_dub_cache_key))

    episodes = anime_data["episodes"] if "episodes" in anime_data else []
    for i, episode in enumerate(episodes, start=1):
        episode["number"] = i
    anime_data["episodes"] = episodes

    return anime_data


def find_zoro_server (episode_id, mode):
    cache_key = f"zoro_server_{episode_id}_{mode}"
    server_id = get_from_redis_cache(cache_key)

    if server_id:
        return server_id, mode

    base_url = f"{os.getenv('ZORO_URL')}/api/v2/hianime/episode/servers?animeEpisodeId={episode_id}"
    print(base_url)
    response = requests.get(base_url)
    response = response.json()

    if "message" in response:
        return None, mode
    
    response = response["data"]

    if mode == "dub" and "dub" in response and len(response["dub"]) > 0:
        server_id = response["dub"][0]["serverName"]
        mode = "dub"
    elif len(response["sub"]) > 0 and "sub" in response:
        server_id = response["sub"][0]["serverName"]
        mode = "sub"
    elif len(response["raw"]) > 0:
        server_id = response["raw"][0]["serverName"]
        mode = "raw"

    store_in_redis_cache(cache_key, server_id)

    return server_id, mode


@lru_cache(maxsize=100)
def get_zoro_episode_streaming_data(episode_url, mode="sub"):
    dub = mode == "dub"
    episode_url = episode_url.replace("$episode$", "?ep=").replace("$dub", "").replace("$sub", "")
    cache_key = f"zoro_episode_streaming_data_{episode_url}_{'dub' if dub else 'sub'}"
    episode_data = get_from_redis_cache(cache_key)
    category = "dub" if dub else "sub"
    server, category = find_zoro_server(episode_url, category)
    if not episode_data:
        base_url = f"{os.getenv('ZORO_URL')}/api/v2/hianime/episode/sources?animeEpisodeId={episode_url}&category={category}&server={server}"
        print(f"Trying URL: {base_url}")
        response = requests.get(base_url, timeout=10)
        episode_data = response.json()

        if "message" not in episode_data:
            episode_data = episode_data["data"]
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
    main_media = data['data']['Media']
    main_title = main_media['title']['english'] or main_media['title']['romaji']

    def similarity(a, b):
        return SequenceMatcher(None, a, b).ratio()

    def clean_title(title):
        return re.sub(r'[^\w\s]', '', title.lower())

    def is_related_content(title, main_title):
        clean_main = clean_title(main_title)
        clean_title_check = clean_title(title)
        return (similarity(clean_main, clean_title_check) > 0.6 or
                clean_main in clean_title_check or
                'season' in clean_title_check)

    def add_content(media, depth=0):
        if media['id'] in seasons:
            return

        english_title = media['title']['english'] or ''
        romaji_title = media['title']['romaji'] or ''
        
        if depth == 0 or is_related_content(english_title, main_title) or is_related_content(romaji_title, main_title):
            seasons[media['id']] = {
                'id': media['id'],
                'title': media['title'],
                'format': media['format'],
                'episodes': media['episodes'],
                'startYear': media['startDate']['year'] if media['startDate']['year'] else 9999,
                'coverImage': media['coverImage']['large'] if media['coverImage'] else None,
                'bannerImage': media['bannerImage']
            }

            if 'relations' in media:
                process_relations(media['relations'], depth + 1)

    def process_relations(relations, depth):
        for edge in relations['edges']:
            if edge['relationType'] in ['SEQUEL', 'PREQUEL', 'ALTERNATIVE', 'PARENT', 'SIDE_STORY'] and edge['node']['format'] in ['TV', 'TV_SHORT', 'MOVIE', 'SPECIAL', 'OVA']:
                add_content(edge['node'], depth)

    # Start with the main media
    add_content(main_media)

    # Sort the seasons
    sorted_seasons = sorted(seasons.values(), key=lambda x: (x['startYear'], x['id']))

    return sorted_seasons

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
        base_url = f"{os.getenv('ZORO_URL')}/api/v2/hianime/anime/{zid}"
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
        base_url = f"{os.getenv('ZORO_URL')}/api/v2/hianime/anime/{z_anime_id}/episodes"
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
            history.episode_title = f"Episode {episode}"

    history.save()

    return history

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

def get_mal_episode_discussion_data(mal_id, episode_number):
    base_url = f"https://api.jikan.moe/v4/anime/{mal_id}/episodes"
    
    # Calculate the page number and offset
    page = math.ceil(episode_number / 100)
    offset = (episode_number - 1) % 100
    
    params = {
        'page': page
    }

    cache_key = f"anime:{mal_id}:episodes:{page}"
    cached_data = get_from_redis_cache(cache_key)

    if cached_data:
        data = json.loads(cached_data)
    else:
        response = requests.get(base_url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            # Cache the entire page of episode data
            store_in_redis_cache(cache_key, json.dumps(data), cache_time=86400)  # Cache for 24 hours
        elif response.status_code == 429:
            # Handle rate limiting
            print("Rate limit reached. Waiting before retrying...")
            return get_mal_episode_discussion_data(mal_id, episode_number)  # Retry the request
        else:
            print(f"Error fetching data: {response.status_code}")
            return None

    if 'data' in data and offset < len(data['data']):
        episode_data = data['data'][offset]
        return episode_data
    else:
        print(f"Episode {episode_number} not found for anime {mal_id}")
        return None

def get_mal_episode_comments(mal_id, episode_number, mal_access_token):
    cache_key = f"anime:{mal_id}:episode:{episode_number}:comments"
    cached_data = get_from_redis_cache(cache_key)

    if cached_data:
        return json.loads(cached_data)

    discussion_data = get_mal_episode_discussion_data(mal_id, episode_number)

    if not discussion_data:
        return None
    
    topic_id_match = re.search(r'topicid=(\d+)', discussion_data['forum_url'])
    if not topic_id_match:
        print(f"Could not extract topic ID from forum URL: {discussion_data['forum_url']}")
        return None
    
    topic_id = topic_id_match.group(1)
    api_url = f"https://api.myanimelist.net/v2/forum/topic/{topic_id}?limit=100"
    headers = {"Authorization": f"Bearer {mal_access_token}"}

    all_comments = []
    next_url = api_url

    def fetch_comments(url):
        retries = 3
        while retries > 0:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                print(f"Rate limit reached. Waiting before retrying... Retries left: {retries}")
                retries -= 1
            else:
                print(f"Error fetching posts: {response.status_code}")
                return None
        return None

    while next_url:
        data = fetch_comments(next_url)
        if data:
            all_comments.extend(data["data"]["posts"])
            next_url = data.get("paging", {}).get("next")
        else:
            break  # Stop if we encounter an error

    if not all_comments:
        return None

    all_comments = sorted(
        all_comments,
        key=lambda x: datetime.datetime.fromisoformat(x["created_at"].replace("Z", "+00:00")),
        reverse=True
    )

    for post in all_comments:
        decoded_text = html.unescape(post['body'])
        post['body_html'] = parse_mixed_content(decoded_text)

    discussion_data["total"] = len(all_comments)

    result = {
        "metadata": discussion_data,
        "comments": all_comments
    }

    store_in_redis_cache(cache_key, json.dumps(result), cache_time=3600)  # Cache for 1 hour

    return result

def parse_mixed_content(content):
    # Remove HTML comments
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    
    # Parse quotes
    content = parse_quotes(content)
    
    # Parse BBCode
    content = parse_bbcode(content)
    
    # Clean up remaining HTML
    soup = BeautifulSoup(content, 'html.parser')
    for br in soup.find_all("br"):
        br.replace_with("\n")
    content = soup.get_text()
    
    # Convert newlines to <p> tags
    paragraphs = content.split('\n')
    paragraphs = [f'<p>{p.strip()}</p>' for p in paragraphs if p.strip()]
    
    return ''.join(paragraphs)

def parse_quotes(content):
    quote_pattern = r'<!–quote–><div class="quotetext"><strong>(.*?)said:</strong><!–quotesaid–><br>(.*?)<!–quote–></div>'
    
    def replace_quote(match):
        author = match.group(1)
        text = match.group(2)
        return f'<blockquote><p><strong>{author} said:</strong></p>{parse_mixed_content(text)}</blockquote>'
    
    return re.sub(quote_pattern, replace_quote, content, flags=re.DOTALL)

def parse_bbcode(content):
    # Handle [b], [i], [u] tags
    content = re.sub(r'\[b\](.*?)\[/b\]', r'<strong>\1</strong>', content)
    content = re.sub(r'\[i\](.*?)\[/i\]', r'<em>\1</em>', content)
    content = re.sub(r'\[u\](.*?)\[/u\]', r'<u>\1</u>', content)
    
    # Handle [img] tags with or without dimensions
    def img_replacer(match):
        align = match.group(1)
        width_height = match.group(2)
        src = match.group(3).strip()
        style = f' style="float: {align};"' if align else ''
        return f'<img src="{src}" alt="User posted image" class="max-w-72 lg:max-w-96">'
    
    content = re.sub(r'\[img(?:\s+align=(left|right))?(?:=(\d+x\d+))?\](.*?)\[/img\]', img_replacer, content, flags=re.DOTALL)
    content = re.sub(r'\[IMG(?:\s+ALIGN=(left|right))?(?:=(\d+x\d+))?\](.*?)\[/IMG\]', img_replacer, content, flags=re.DOTALL)

    # Handle [yt] tags for YouTube videos
    def yt_replacer(match):
        video_id = match.group(1)
        return f'<iframe class="max-w-fit aspect-video" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'

    content = re.sub(r'\[yt\](.*?)\[/yt\]', yt_replacer, content)

    spoiler_count = 0
    def spoiler_replacer(match):
        nonlocal spoiler_count
        random_string = ''.join(random.SystemRandom().choice('abcdefghijklmnopqrstuvwxyz') for _ in range(10))
        spoiler_count += 1
        title = match.group(1) or "Spoiler"
        spoiler_content = match.group(2)
        return f'<div class="spoiler"><button onclick="toggleSpoiler(\'spoiler-{random_string}-{spoiler_count}\')">Spoiler: {title}</button><div id="spoiler-{random_string}-{spoiler_count}" class="spoiler-content max-w-96" style="display:none;">{spoiler_content}</div></div>'

    content = re.sub(r'\[spoiler(?:=([^\]]+))?\](.*?)\[/spoiler\]', spoiler_replacer, content, flags=re.DOTALL)
    
    # Handle [size] tags
    content = re.sub(r'\[size=(\d+)\](.*?)\[/size\]', r'<span style="font-size:\1%">\2</span>', content)

    parser = bbcode.Parser()
    content = parser.format(content)
    
    return content
