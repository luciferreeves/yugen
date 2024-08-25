import os
import dotenv
import requests
import time

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
        return current_year
    else:
        return current_year + 1


def get_trending_anime():
    request_url = f"{CONSUMET_URL}/meta/anilist/trending?page=1&perPage=34"
    response = requests.get(request_url)
    return response.json()


def get_popular_anime():
    request_url = f"{CONSUMET_URL}/meta/anilist/advanced-search?type=ANIME&sort=[%22POPULARITY_DESC%22]&?page=1&perPage=34"
    response = requests.get(request_url)
    return response.json()


def get_top_anime():
    request_url = f"{CONSUMET_URL}/meta/anilist/advanced-search?type=ANIME&sort=[%22SCORE_DESC%22]&?page=1&perPage=34"
    response = requests.get(request_url)
    return response.json()


def get_top_airing_anime():
    season = get_current_season()
    year = get_current_year()
    request_url = f"{CONSUMET_URL}/meta/anilist/advanced-search?type=ANIME&status=RELEASING&sort=[%22POPULARITY_DESC%22]&season={season}&year={year}&?page=1&perPage=6"
    response = requests.get(request_url)
    return response.json()


def get_upcoming_anime():
    season = get_next_season()
    year = get_next_season_year()
    request_url = f"{CONSUMET_URL}/meta/anilist/advanced-search?type=ANIME&status=NOT_YET_RELEASED&sort=[%22POPULARITY_DESC%22]&season={season}&year={year}&?page=1&perPage=6"
    response = requests.get(request_url)
    return response.json()
