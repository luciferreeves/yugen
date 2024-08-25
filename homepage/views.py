import os
import dotenv
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from authentication.utils import get_discord_user, get_redirect_uri

dotenv.load_dotenv()


def index(request):
    if (
        not request.user.is_authenticated
        or not request.user.discord_id
        or not request.user.discord_access_token
    ):
        logout(request)
        return redirect(get_redirect_uri())

    # Get the User's Discord Information
    user = get_discord_user(
        access_token=request.user.discord_access_token,
        token_type=request.user.discord_token_type,
    )

    if not user["is_authorized"]:
        logout(request)
        return redirect(get_redirect_uri())

    return render(request, "home/index.html")
