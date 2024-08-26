from django.db import models
from django.contrib.auth.models import AbstractUser


# Adding Discord Specific Fields to the User Model
class User(AbstractUser):
    discord_id = models.CharField(max_length=255, unique=True)
    discord_access_token = models.CharField(max_length=255)
    discord_refresh_token = models.CharField(max_length=255)
    discord_token_type = models.CharField(max_length=255)
    discord_username = models.CharField(max_length=255, unique=True)
    discord_avatar = models.CharField(max_length=255, blank=True)
    discord_banner = models.CharField(max_length=255, blank=True)
    discord_global_name = models.CharField(max_length=255)
    discord_guild_name = models.CharField(max_length=255, blank=True)
