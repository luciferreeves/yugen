import os
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
import requests

class MALTokenRefreshMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            user = request.user
            self.refresh_mal_token_if_needed(user)
        return self.get_response(request)

    def refresh_mal_token_if_needed(self, user):
        # Check if the token is expired or will expire within 48 hours
        if user.mal_token_expires_in:
            now = timezone.now()
            expiry_threshold = now + timedelta(hours=48)
            
            if user.mal_token_expires_in <= expiry_threshold:
                self.refresh_mal_token(user)

    def refresh_mal_token(self, user):
        # MAL API endpoint for refreshing token
        refresh_url = "https://myanimelist.net/v1/oauth2/token"

        mal_client_id = os.environ.get("MAL_CLIENT_ID")
        mal_client_secret = os.environ.get("MAL_CLIENT_SECRET")
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": user.mal_refresh_token,
            "client_id": mal_client_id,
            "client_secret": mal_client_secret,
        }

        print(f"Refreshing MAL token for user {user.username}")

        try:
            response = requests.post(refresh_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()

            print(f"Successfully refreshed MAL token for user {user.username}")
            
            # Update user's MAL token information
            user.mal_access_token = token_data["access_token"]
            user.mal_refresh_token = token_data["refresh_token"]
            user.mal_token_type = token_data["token_type"]
            user.mal_token_expires_in = timezone.now() + timedelta(seconds=token_data["expires_in"])
            user.save()
            
        except requests.RequestException as e:
            # Handle any errors that occur during the refresh process
            # You might want to log this error or handle it in a way that fits your application
            print(f"Error refreshing MAL token: {str(e)}")