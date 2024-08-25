import json
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import redirect
from django.contrib.auth import logout
from authentication.utils import (
    get_redirect_uri,
    get_discord_user,
)


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

        if (
            not request.user.is_authenticated
            or not request.user.discord_id
            or not request.user.discord_access_token
        ):
            logout(request)
            return redirect(get_redirect_uri())

        # Check the verification cookie
        verification_cookie = request.COOKIES.get("guild_verified")
        if verification_cookie:
            try:
                cookie_data = json.loads(verification_cookie)
                verified_at = timezone.datetime.fromisoformat(
                    cookie_data["verified_at"]
                )
                if timezone.now() > verified_at + timedelta(hours=24):
                    # Verification expired, need to re-check
                    raise ValueError("Verification expired")
            except (json.JSONDecodeError, ValueError):
                # Cookie is invalid or expired, need to re-check
                pass
        else:
            # No verification cookie, need to check guild membership
            pass

        if not verification_cookie or not self._is_authorized(request):
            user = get_discord_user(
                access_token=request.user.discord_access_token,
                token_type=request.user.discord_token_type,
            )

            if not user["is_authorized"]:
                logout(request)
                response = redirect(get_redirect_uri())
                response.delete_cookie("guild_verified")  # Ensure cookie is removed
                return response

            # Set the verification cookie
            response = self.get_response(request)
            response.set_cookie(
                "guild_verified",
                json.dumps({"verified_at": timezone.now().isoformat()}),
                max_age=24 * 60 * 60,  # Cookie expires after 24 hours
                httponly=True,  # Cookie cannot be accessed via JavaScript
                secure=True,  # Ensure cookie is sent over HTTPS
            )
            return response

        response = self.get_response(request)
        return response

    def _is_authorized(self, request):
        # Check if the user is authorized based on the current cookie or session
        # This function should ideally be a lightweight check
        return True
