import os
import re
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

API_KEY = os.getenv("TMDB_API_KEY")
API_READ_ACCESS_TOKEN = os.getenv("TMDB_READ_ACCESS_TOKEN")
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_URL = "https://image.tmdb.org/t/p/original"

def get_headers():
    return {
        "Authorization": f"Bearer {API_READ_ACCESS_TOKEN}",
        "accept": "application/json"
    }

def compare_two_strings(str1, str2):
    str1 = re.sub(r'\s+', '', str1)
    str2 = re.sub(r'\s+', '', str2)
    if str1 == str2:
        return 1
    if len(str1) < 2 or len(str2) < 2:
        return 0
    bigrams = {}
    for i in range(len(str1) - 1):
        bigram = str1[i:i+2]
        bigrams[bigram] = bigrams.get(bigram, 0) + 1
    
    intersections = 0
    for i in range(len(str2) - 1):
        bigram = str2[i:i+2]
        if bigram in bigrams and bigrams[bigram] > 0:
            bigrams[bigram] -= 1
            intersections += 1
    
    return 2.0 * intersections / (len(str1) + len(str2) - 2)

def roman_to_decimal(roman):
    values = {
        'I': 1, 'V': 5, 'X': 10, 'L': 50,
        'C': 100, 'D': 500, 'M': 1000
    }
    total = 0
    prev_value = 0
    for char in reversed(roman.upper()):
        current_value = values[char]
        if current_value >= prev_value:
            total += current_value
        else:
            total -= current_value
        prev_value = current_value
    return total

def parse_title_and_season(title):
    media_types = ["TV", "TV_SHORT", "OVA", "ONA", "MOVIE", "SPECIAL", "MUSIC"]
    pattern = re.compile(r'\s*(' + '|'.join(media_types) + r')\s*$', re.IGNORECASE)
    title = pattern.sub('', title).strip()
    
    match = re.search(r'(.*?)(Season \d+|Cour \d+|Part \d+|Series \d+|Level \d+|(\bI{1,3}\b|\bIV\b|\bV\b|\bVI\b|\bVII\b|\bVIII\b|\bIX\b|\bX\b)( Part \d+)?|\bI{1,3}\b|\bIV\b|\bV\b|\bVI\b|\bVII\b|\bVIII\b|\bIX\b|\bX\b)$', title, re.IGNORECASE)
    
    if not match:
        return {"show_name": title, "season_info": ""}
    
    show_name = match.group(1).strip()
    season_info = match.group(2).strip()
    
    roman_match = re.search(r'(\bI{1,3}\b|\bIV\b|\bV\b|\bVI\b|\bVII\b|\bVIII\b|\bIX\b|\bX\b)', season_info, re.IGNORECASE)
    if roman_match:
        season_info = f"Season {roman_to_decimal(roman_match.group(1))}"
    
    return {"show_name": show_name, "season_info": season_info}

def search_tv_shows_by_title(title, alternative_title=None, is_adult=None, country_priority=None, max_year=None):
    try:
        query = title.split(':')[0].strip()
        if ' ' not in query and alternative_title:
            query += f" {alternative_title}"
        
        response = requests.get(f"{BASE_URL}/search/tv", headers=get_headers(), params={"query": query})
        results = response.json().get('results', [])
        
        if not results:
            response = requests.get(f"{BASE_URL}/search/tv", headers=get_headers(), params={"query": title})
            results = response.json().get('results', [])
        
        if not results:
            pattern = re.compile(r'\s*\([A-Z_]+\)\s*$', re.IGNORECASE)
            if pattern.search(title):
                clean_title = pattern.sub('', title).strip()
                response = requests.get(f"{BASE_URL}/search/tv", headers=get_headers(), params={"query": clean_title})
                results = response.json().get('results', [])
        
        if results:
            if is_adult is not None:
                results = [r for r in results if r.get('adult', False) == is_adult]
            
            if country_priority:
                results.sort(key=lambda x: int(country_priority in x.get('origin_country', [])), reverse=True)
            
            if max_year:
                try:
                    max_year = int(max_year)
                    results = [r for r in results if r.get('first_air_date') and int(r['first_air_date'].split('-')[0]) <= max_year]
                except ValueError:
                    # If max_year is not a valid integer, we'll skip this filter
                    pass
        
        return results
    except Exception as e:
        print(f"Error in search_tv_shows_by_title: {str(e)}")
        return []

def get_tv_show_details(show_id):
    try:
        response = requests.get(f"{BASE_URL}/tv/{show_id}", headers=get_headers())
        data = response.json()
        return {"show": data, "seasons": data.get("seasons", [])}
    except Exception as e:
        print(f"Error in get_tv_show_details: {str(e)}")
        return None

def get_image_url(path):
    return f"https://image.tmdb.org/t/p/original{path}" if path else None

def get_tv_season_details(show_id, season_number):
    try:
        response = requests.get(f"{BASE_URL}/tv/{show_id}/season/{season_number}", headers=get_headers())
        episodes = response.json().get('episodes', [])
        
        if not episodes:
            return []
        
        return [
            {
                "id": f"{show_id}-S{season_number}E{ep['episode_number']}",
                "lastVisited": None,
                "episodeId": str(ep['id']),
                "title": ep['name'],
                "description": ep['overview'] or "No Description.",
                "number": ep['episode_number'],
                "image": get_image_url(ep.get('still_path')),
                "airDate": ep.get('air_date'),
                "isFiller": False
            }
            for ep in episodes
        ]
    except Exception as e:
        print(f"Error in get_tv_season_details: {str(e)}")
        return None

def get_tv_episode_groups(show_id):
    try:
        response = requests.get(f"{BASE_URL}/tv/{show_id}/episode_groups", headers=get_headers())
        return response.json().get('results', [])
    except Exception as e:
        print(f"Error in get_tv_episode_groups: {str(e)}")
        return []

def get_tv_episode_group_details(group_id):
    try:
        response = requests.get(f"{BASE_URL}/tv/episode_group/{group_id}", headers=get_headers())
        data = response.json()
        
        if not data or 'groups' not in data:
            return []
        
        return [
            {
                "id": f"{group_id}-E{ep['episode_number']}",
                "lastVisited": None,
                "episodeId": str(ep['id']),
                "title": ep['name'],
                "description": ep['overview'],
                "number": ep['episode_number'],
                "image": get_image_url(ep.get('still_path')),
                "airDate": ep.get('air_date'),
                "isFiller": False
            }
            for group in data['groups']
            for ep in group.get('episodes', [])
        ]
    except Exception as e:
        print(f"Error in get_tv_episode_group_details: {str(e)}")
        return []

def filter_episodes_by_year(episodes, episode_count=None, start_date=None, start_year=None, duration=None, media_type=None):
    start_date = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
    start_year = int(start_year) if start_year else None
    
    filtered_episodes = [
        ep for ep in episodes
        if ep['airDate'] and (
            (not start_date or datetime.strptime(ep['airDate'], "%Y-%m-%d") >= start_date) and
            (not start_year or int(ep['airDate'].split('-')[0]) >= start_year)
        )
    ]
    
    if media_type in ['OVA', 'ONA', 'SPECIAL']:
        excluded_keywords = ['chibi', 'live', 'event', 'recap', 'summary']
        filtered_episodes = [
            ep for ep in filtered_episodes
            if not any(keyword in ep['title'].lower() for keyword in excluded_keywords) and
            (not ep.get('runtime') or ep['runtime'] >= 20)
        ]
    
    filtered_episodes.sort(key=lambda ep: (
        abs((datetime.strptime(ep['airDate'], "%Y-%m-%d") - start_date).total_seconds()) if start_date else 0,
        abs(int(ep['airDate'].split('-')[0]) - start_year) if start_year else 0,
        abs((ep.get('runtime') or 0) - (duration or 0))
    ))
    
    return filtered_episodes[:episode_count] if episode_count else filtered_episodes

def search_movies_by_title(title, alternative_title=None, year=None):
    try:
        if alternative_title:
            response = requests.get(f"{BASE_URL}/search/movie", headers=get_headers(), params={"query": alternative_title, "year": year})
            results = response.json().get('results', [])
            if len(results) == 1 and compare_two_strings((results[0].get('original_title') or '').lower(), alternative_title.lower()) >= 0.9:
                return results
        
        response = requests.get(f"{BASE_URL}/search/movie", headers=get_headers(), params={"query": title, "year": year})
        results = response.json().get('results', [])
        
        if not results:
            pattern = re.compile(r'\s*\([A-Z_]+\)\s*$', re.IGNORECASE)
            if pattern.search(title):
                clean_title = pattern.sub('', title).strip()
                response = requests.get(f"{BASE_URL}/search/movie", headers=get_headers(), params={"query": clean_title, "year": year})
                results = response.json().get('results', [])
        
        return results
    except Exception as e:
        print(f"Error in search_movies_by_title: {str(e)}")
        return None

def get_movie_details(movie_id):
    try:
        response = requests.get(f"{BASE_URL}/movie/{movie_id}", headers=get_headers())
        movie = response.json()
        
        return {
            "id": str(movie['id']),
            "lastVisited": None,
            "episodeId": str(movie['id']),
            "title": movie['title'],
            "description": movie['overview'],
            "number": 1,
            "image": get_image_url(movie.get('poster_path')),
            "airDate": movie.get('release_date'),
            "isFiller": False
        }
    except Exception as e:
        print(f"Error in get_movie_details: {str(e)}")
        return None

def fetch_and_filter_episodes(show_id, season, start_date, year, episode_count, media_type):
    episodes = get_tv_season_details(show_id, season['season_number'])
    return filter_episodes_by_year(episodes, episode_count or season['episode_count'], start_date, year, None, media_type) if episodes else []

def find_best_matching_season(seasons, season_info, episode_count, year, date):
    matching_seasons = [
        s for s in seasons
        if (season_info and f"Season {s['season_number']}".lower() == season_info.lower()) or
           (s['episode_count'] == episode_count and 
            (not s.get('air_date') or 
             (s.get('air_date') and str(s['air_date']).startswith(str(year or '')))))
    ]
    
    if len(matching_seasons) > 1 and date:
        matching_seasons = [
            s for s in matching_seasons
            if s.get('air_date') and datetime.strptime(s['air_date'], "%Y-%m-%d").month == date.month
        ]
    
    if len(matching_seasons) > 1 and date:
        matching_seasons = [
            s for s in matching_seasons
            if s.get('air_date') and datetime.strptime(s['air_date'], "%Y-%m-%d").day == date.day
        ]
    
    return matching_seasons[0] if matching_seasons else None

def search_and_fetch_all_episodes(title, media_type, alternative_title, year, episode_count, date, is_adult, country_priority, duration):
    parsed_title = parse_title_and_season(title)
    show_name, season_info = parsed_title['show_name'], parsed_title['season_info']
    
    if media_type == "MOVIE":
        movies = search_movies_by_title(title, alternative_title, year)
        if movies and len(movies) > 0:
            movie = max(movies, key=lambda m: m['popularity'])
            movie_details = get_movie_details(movie['id'])
            return [movie_details] if movie_details else []
        return []
    
    start_date = f"{year}-{date.month:02d}-{date.day:02d}" if date else None
    tv_shows = search_tv_shows_by_title(show_name, alternative_title, is_adult, country_priority, year)
    
    if not tv_shows:
        print(f"No TV shows found for title: {show_name}")
        return []
    
    best_match = next(
        (show for show in tv_shows if (
            show['name'].lower() == show_name.lower() or
            show.get('original_name', '').lower() == show_name.lower()
        ) and (not year or show['first_air_date'].startswith(str(year)))),
        tv_shows[0]
    )
    
    show_details = get_tv_show_details(best_match['id'])
    if not show_details:
        return []
    
    seasons = show_details['seasons']
    if media_type == "TV":
        seasons = [s for s in seasons if s['season_number'] != 0]
    
    best_season = find_best_matching_season(seasons, season_info, episode_count, year, date)
    
    if best_season:
        return fetch_and_filter_episodes(best_match['id'], best_season, start_date, year, episode_count, media_type)
    else:
        print(f"No matching season found for {show_name}")
        # You might want to implement a fallback strategy here, such as:
        # 1. Try to fetch episodes from the latest season
        # 2. Generate placeholder episodes
        # 3. Or simply return an empty list
        # return [] <- removed this early return to avoid breaking the code
    
    if media_type in ["OVA", "ONA", "SPECIAL"]:
        episode_groups = get_tv_episode_groups(best_match['id'])
        if episode_groups and len(episode_groups) > 0:
            absolute_order_group = next((g for g in episode_groups if "absolute order" in g['name'].lower()), None)
            if absolute_order_group:
                episodes = get_tv_episode_group_details(absolute_order_group['id'])
                filtered_episodes = filter_episodes_by_year(episodes, episode_count, start_date, year, duration, media_type)
                if filtered_episodes:
                    return filtered_episodes
        
        special_season = next((s for s in seasons if s['season_number'] == 0), None)
        if special_season:
            episodes = fetch_and_filter_episodes(best_match['id'], special_season, start_date, year, episode_count, media_type)
            if episodes:
                return episodes
    
    if season_info:
        matching_season = next((s for s in seasons if f"Season {s['season_number']}".lower() == season_info.lower()), None)
        if matching_season:
            return fetch_and_filter_episodes(best_match['id'], matching_season, start_date, year, episode_count, media_type)
    
    episode_groups = get_tv_episode_groups(best_match['id'])
    if episode_groups and len(episode_groups) > 0:
        all_episodes_group = next(
            (g for g in episode_groups if any(keyword in g['name'].lower() for keyword in 
             ['all episodes', 'absolute order', 'absolute', 'correct order', 'bluray order'])),
            None
        )
        if all_episodes_group:
            episodes = get_tv_episode_group_details(all_episodes_group['id'])
            return filter_episodes_by_year(episodes, episode_count, start_date, year, duration, media_type)
    
    best_match = max(tv_shows, key=lambda show: compare_two_strings(show_name.lower(), (show['name'] or '').lower()))
    show_details = get_tv_show_details(best_match['id'])
    if show_details:
        seasons = show_details['seasons']
        if media_type == "TV":
            seasons = [s for s in seasons if s['season_number'] != 0]
        
        best_season = next(
            (s for s in seasons if s['episode_count'] == episode_count and 
             (s['air_date'] and s['air_date'].startswith(str(year)))),
            None
        )
        
        if not best_season:
            possible_seasons = [s for s in seasons if s['episode_count'] > episode_count and 
                                (s['air_date'] and int(s['air_date'].split('-')[0]) <= int(year))]
            if possible_seasons:
                best_season = min(
                    possible_seasons,
                    key=lambda s: (
                        abs(int(s['air_date'].split('-')[0]) - int(year)),
                        abs(s['episode_count'] - episode_count)
                    )
                )
        
        if best_season:
            return fetch_and_filter_episodes(best_match['id'], best_season, start_date, year, episode_count, media_type)
    
    return []

# Usage example
def get_anime_episodes(anime_data):
    title = anime_data['title']['english'] or anime_data['title']['romaji']
    alternative_title = anime_data['title']['native']
    media_type = anime_data['type']
    year = anime_data['startDate']['year']
    episode_count = anime_data['totalEpisodes']
    date = datetime(
        year=anime_data['startDate']['year'],
        month=anime_data['startDate']['month'],
        day=anime_data['startDate']['day']
    )
    is_adult = anime_data.get('isAdult', False)
    country_priority = anime_data['countryOfOrigin']
    duration = anime_data['duration']

    episodes = search_and_fetch_all_episodes(
        title=title,
        media_type=media_type,
        alternative_title=alternative_title,
        year=year,
        episode_count=episode_count,
        date=date,
        is_adult=is_adult,
        country_priority=country_priority,
        duration=duration
    )

    return episodes
