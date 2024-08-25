import dotenv
import os
import requests
from authentication.models import User

dotenv.load_dotenv()


def get_redirect_uri():
    # Only Authenticated Users who are in our Discord Server can access the website
    discord_client_id = os.environ.get("DISCORD_CLIENT_ID")
    discord_redirect_uri = os.environ.get("DISCORD_REDIRECT_URI")
    discord_scope = "identify guilds email"
    redirect_uri = f"https://discord.com/oauth2/authorize?client_id={discord_client_id}&response_type=code&redirect_uri={discord_redirect_uri}&scope={discord_scope}"
    return redirect_uri


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
        "scope": "identify email guilds",
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = requests.post(
        "https://discord.com/api/oauth2/token", data=data, headers=headers
    )
    return response.json()


def get_discord_user(access_token, token_type):
    user = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"{token_type} {access_token}"},
    ).json()
    guilds = requests.get(
        "https://discord.com/api/users/@me/guilds",
        headers={"Authorization": f"{token_type} {access_token}"},
    ).json()

    authorized_guilds = os.environ.get("DISCORD_AUTHORIZED_GUILDS").split(",")
    user["is_authorized"] = False
    if isinstance(guilds, list):
        for guild in guilds:
            if guild["id"] in authorized_guilds:
                user["is_authorized"] = True
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
                "email": discord_user["email"],
                "discord_id": discord_user["id"],
                "discord_access_token": access_token,
                "discord_refresh_token": refresh_token,
                "discord_token_type": token_type,
                "discord_username": discord_user["username"],
                "discord_avatar": discord_user["avatar"],
                "discord_banner": discord_user["banner"],
                "discord_global_name": discord_user["global_name"],
            },
        )

        if not created:
            user.username = discord_user["username"]
            user.email = discord_user["email"]
            user.discord_access_token = access_token
            user.discord_refresh_token = refresh_token
            user.discord_token_type = token_type
            user.discord_username = discord_user["username"]
            user.discord_avatar = discord_user["avatar"]
            user.discord_banner = discord_user["banner"]
            user.discord_global_name = discord_user["global_name"]
            user.save()

        return user

    return None
