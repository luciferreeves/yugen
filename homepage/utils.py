from collections import defaultdict
import os
import dotenv
import requests
import time
import datetime
import pytz
import requests
from django.utils import timezone

dotenv.load_dotenv()

CONSUMET_URL = os.getenv("CONSUMET_URL")


def get_current_season():
    current_month = time.localtime().tm_mon

    if current_month in [1, 2, 3]:
        season = "WINTER"
    elif current_month in [4, 5, 6]:
        season = "SPRING"
    elif current_month in [7, 8, 9]:
        season = "SUMMER"
    else:
        season = "FALL"

    return season


def get_current_year():
    return time.localtime().tm_year


def get_next_season():
    current_season = get_current_season()
    if current_season == "WINTER":
        return "SPRING"
    elif current_season == "SPRING":
        return "SUMMER"
    elif current_season == "SUMMER":
        return "FALL"
    else:
        return "WINTER"


def get_next_season_year():
    current_season = get_current_season()
    current_year = get_current_year()
    if current_season == "WINTER":
        return current_year + 1
    else:
        return current_year


def get_trending_anime(page=1, per_page=34):
    request_url = f"{CONSUMET_URL}/meta/anilist/trending?page={page}&perPage={per_page}"
    response = requests.get(request_url)
    return response.json()


def get_popular_anime(page=1, per_page=34):
    request_url = f"{CONSUMET_URL}/meta/anilist/advanced-search?type=ANIME&sort=[%22POPULARITY_DESC%22]&?page={page}&perPage={per_page}"
    response = requests.get(request_url)
    return response.json()


def get_top_anime(page=1, per_page=34):
    request_url = f"{CONSUMET_URL}/meta/anilist/advanced-search?type=ANIME&sort=[%22SCORE_DESC%22]&?page={page}&perPage={per_page}"
    response = requests.get(request_url)
    return response.json()


def get_top_airing_anime(page=1, per_page=6):
    season = get_current_season()
    year = get_current_year()
    request_url = f"{CONSUMET_URL}/meta/anilist/advanced-search?type=ANIME&status=RELEASING&sort=[%22POPULARITY_DESC%22]&season={season}&year={year}&?page={page}&perPage={per_page}"
    response = requests.get(request_url)
    return response.json()


def get_upcoming_anime(page=1, per_page=6):
    season = get_next_season()
    year = get_next_season_year()
    request_url = f"{CONSUMET_URL}/meta/anilist/advanced-search?type=ANIME&status=NOT_YET_RELEASED&sort=[%22POPULARITY_DESC%22]&season={season}&year={year}&?page={page}&perPage={per_page}"
    response = requests.get(request_url)
    return response.json()

def get_start_end_times():
    now = datetime.datetime.now(pytz.UTC)
    
    start_time = now.replace(hour=4, minute=0, second=0, microsecond=0)
    if now.hour < 4:
        start_time -= datetime.timedelta(days=1)
    
    times = []
    for i in range(7):
        start = start_time + datetime.timedelta(days=i)
        end = start + datetime.timedelta(days=1)
        times.append({
            "start": int(start.timestamp()),
            "end": int(end.timestamp()),
            "day": start.strftime("%A"),
            "date": start.strftime("%Y-%m-%d"),
            "today": i == 0
        })

    return times

def get_anime_schedule(week_start, week_end):
    # GraphQL query
    query = """
    query ($weekStart: Int, $weekEnd: Int, $page: Int, $perPage: Int) {
      Page(page: $page, perPage: $perPage) {
        pageInfo {
          hasNextPage
          total
          currentPage
          lastPage
          perPage
        }
        airingSchedules(
          airingAt_greater: $weekStart
          airingAt_lesser: $weekEnd
          sort: TIME
        ) {
          id
          episode
          timeUntilAiring
          airingAt
          mediaId
          media {
            isAdult
            title {
              romaji
              native
              english
            }
            coverImage {
              extraLarge
              medium
              color
            }
            bannerImage
            siteUrl
          }
        }
      }
    }
    """
    
    # Variables for the query
    variables = {
        "weekStart": week_start,
        "weekEnd": week_end,
        "page": 1,
        "perPage": 50  # Adjust as needed
    }
    
    # Make the request to the AniList API
    url = 'https://graphql.anilist.co'
    response = requests.post(url, json={'query': query, 'variables': variables})
    
    if response.status_code == 200:
        return response.json()['data']['Page']['airingSchedules']
    else:
        return None

def group_anime_schedules(schedules):
    grouped = defaultdict(list)
    for schedule in schedules:
        airing_time = datetime.datetime.fromtimestamp(schedule['airingAt'])
        grouped[airing_time].append(schedule)
    return dict(sorted(grouped.items()))

def find_target_anime(grouped_schedules):
    flat_list = [
        (time, anime) 
        for time, animes in grouped_schedules.items() 
        for anime in animes
    ]
    flat_list.sort(key=lambda x: x[0])  # Sort by airing time

    first_positive = next((i for i, (_, anime) in enumerate(flat_list) if anime['timeUntilAiring'] > 0), None)
    
    if first_positive is None or first_positive < 2:
        return None, []
    
    target = flat_list[first_positive][1]
    last_two = [anime for _, anime in flat_list[first_positive-2:first_positive]]
    
    return target, last_two