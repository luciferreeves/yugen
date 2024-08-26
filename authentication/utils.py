import dotenv
import os
import requests
import secrets
from authentication.models import User
from user_profile.models import UserPreferences

dotenv.load_dotenv()

def generate_mal_code_challenge():
    # 128 bytes PKCE code challenge
    token = secrets.token_urlsafe(128)
    return token[:128]

def get_mal_redirect_uri():
    mal_client_id = os.environ.get("MAL_CLIENT_ID")
    # mal_client_secret = os.environ.get("MAL_CLIENT_SECRET")
    mal_redirect_uri = os.environ.get("MAL_REDIRECT_URI")

    code_challenge = generate_mal_code_challenge()
    code_challenge_method = "plain"

    redirect_uri = f"https://myanimelist.net/v1/oauth2/authorize?response_type=code&client_id={mal_client_id}&code_challenge={code_challenge}&code_challenge_method={code_challenge_method}&redirect_uri={mal_redirect_uri}&state={code_challenge}"

    return redirect_uri, code_challenge

def get_redirect_uri():
    # Only Authenticated Users who are in our Discord Server can access the website
    discord_client_id = os.environ.get("DISCORD_CLIENT_ID")
    discord_redirect_uri = os.environ.get("DISCORD_REDIRECT_URI")
    discord_scope = "identify guilds guilds.members.read"
    redirect_uri = f"https://discord.com/oauth2/authorize?client_id={discord_client_id}&response_type=code&redirect_uri={discord_redirect_uri}&scope={discord_scope}"
    return redirect_uri

def exchange_mal_code(code, code_verifier):
    mal_client_id = os.environ.get("MAL_CLIENT_ID")
    mal_client_secret = os.environ.get("MAL_CLIENT_SECRET")
    mal_redirect_uri = os.environ.get("MAL_REDIRECT_URI")

    data = {
        "client_id": mal_client_id,
        "client_secret": mal_client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "code_verifier": code_verifier,
        "grant_type": "authorization_code",
        "redirect_uri": mal_redirect_uri,
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = requests.post(
        "https://myanimelist.net/v1/oauth2/token", data=data, headers=headers
    )
    return response.json()

def exchange_code(code):
    discord_client_id = os.environ.get("DISCORD_CLIENT_ID")
    discord_client_secret = os.environ.get("DISCORD_CLIENT_SECRET")
    discord_redirect_uri = os.environ.get("DISCORD_REDIRECT_URI")

    data = {
        "client_id": discord_client_id,
        "client_secret": discord_client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": discord_redirect_uri,
        "scope": "identify guilds guilds.members.read",
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = requests.post(
        "https://discord.com/api/oauth2/token", data=data, headers=headers
    )
    return response.json()

def get_user_mal_list(access_token, limit=10, offset=0):
    base_url = f"https://api.myanimelist.net/v2/users/@me/animelist?limit={limit}&offset={offset}&fields=my_list_status,anime&sort=list_updated_at"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(base_url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        if data["data"] and "paging" in data:
            if "next" in data["paging"]:
                page_next = data["paging"]["next"]
            else:
                page_next = None
            
            if "previous" in data["paging"]:
                page_previous = data["paging"]["previous"]
            else:
                page_previous = None
        mal_ids = [anime["node"]["id"] for anime in data["data"]]
        user_list = {anime["node"]["id"]: anime["node"]["my_list_status"] for anime in data["data"]}

    query = f'''
        query {{
            Page {{
                media(idMal_in: {mal_ids}) {{
                    id
                    title {{
                        romaji
                        english
                        native
                    }}
                    idMal
                    status
                    coverImage {{
                        large
                    }}
                    episodes
                    duration
                    averageScore
                    genres
                    seasonYear
                }}
            }}
        }}
    '''
    response = requests.post(
        "https://graphql.anilist.co",
        json={"query": query},
    )

    user_anime_list = []
    if response.status_code == 200:
        data = response.json()
        for anime in data["data"]["Page"]["media"]:
            anime["my_list_status"] = user_list[anime["idMal"]]
            user_anime_list.append(anime)
    else:
        print(response.json(), "Error in fetching Anilist Anime Details")
            
    return user_anime_list, page_previous, page_next

    

def get_discord_user(access_token, token_type):
    guilds = requests.get(
        "https://discord.com/api/users/@me/guilds",
        headers={"Authorization": f"{token_type} {access_token}"},
    ).json()

    authorized_guilds = os.environ.get("DISCORD_AUTHORIZED_GUILDS").split(",")
    user = {}
    user["is_authorized"] = False
    if isinstance(guilds, list):
        for guild in guilds:
            if guild["id"] in authorized_guilds:
                # get the user's guild display name
                member = requests.get(
                    f"https://discord.com/api//users/@me/guilds/{guild['id']}/member",
                    headers={"Authorization": f"{token_type} {access_token}"},
                ).json()
                
                user = member["user"]
                user["is_authorized"] = True
                user["guild_name"] = member["nick"] if member["nick"] is not None else ""

                break

    else:
        print(guilds)
        print(user)

    return user


def authenticate_user(exchange_response):
    access_token = exchange_response.get("access_token")
    token_type = exchange_response.get("token_type")
    refresh_token = exchange_response.get("refresh_token")

    discord_user = get_discord_user(access_token, token_type)

    if discord_user["is_authorized"]:
        user, created = User.objects.update_or_create(
            discord_id=discord_user["id"],
            defaults={
                "username": discord_user["username"],
                "discord_id": discord_user["id"],
                "discord_access_token": access_token,
                "discord_refresh_token": refresh_token,
                "discord_token_type": token_type,
                "discord_username": discord_user["username"],
                "discord_avatar": discord_user["avatar"],
                "discord_banner": discord_user["banner"] if discord_user["banner"] is not None else "",
                "discord_global_name": discord_user["global_name"],
                "discord_guild_name": discord_user["guild_name"],
            },
        )
        print(discord_user["banner"])

        if not created:
            user.username = discord_user["username"]
            user.discord_access_token = access_token
            user.discord_refresh_token = refresh_token
            user.discord_token_type = token_type
            user.discord_username = discord_user["username"]
            user.discord_avatar = discord_user["avatar"]
            user.discord_banner = (
                discord_user["banner"] if discord_user["banner"] is not None else ""
            )
            user.discord_global_name = discord_user["global_name"]
            user.discord_guild_name = discord_user["guild_name"]
            user.save()

        UserPreferences.objects.get_or_create(user=user)

        return user

    return None
