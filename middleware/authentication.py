from django.shortcuts import redirect
from django.contrib.auth import logout
from django.urls import reverse
from authentication.utils import (
    get_redirect_uri,
    get_discord_user,
)  # Import your utility functions


class AuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip authentication if the path contains "admin" or is not a view
        if (
            "admin" in request.path
            or "auth" in request.path
            or not hasattr(request, "user")
        ):
            response = self.get_response(request)
            return response

        # Perform the authentication check
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

        # Proceed to the view
        response = self.get_response(request)
        return response
