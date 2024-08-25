from django.db import models
from django.conf import settings

# Create your models here.
class UserPreferences(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    card_layout = models.CharField(max_length=16, default="classic") # classic, wide, compact
    title_language = models.CharField(max_length=16, default="english") # english, romaji, native
    character_name_language = models.CharField(max_length=16, default="romaji") # romaji, native
    default_language = models.CharField(max_length=16, default="sub") # sub, dub
    default_provider = models.CharField(max_length=16, default="gogoanime") # gogoanime, zoro
    default_watch_page = models.CharField(max_length=16, default="watch") # detail, watch
    show_history_on_home = models.BooleanField(default=True)
    auto_skip_intro = models.BooleanField(default=False)
    auto_play_video = models.BooleanField(default=False)
    auto_next_episode = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s preferences"
    
    class Meta:
        verbose_name_plural = "User Preferences"

class UserHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    anime_id = models.IntegerField()
    episode = models.IntegerField()
    timestamp = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} watched episode {self.episode} of anime {self.anime_id}"
    
    class Meta:
        verbose_name_plural = "User Histories"

# MAL Like Anime List for MAL Sync Compatibility
class UserAnimeList(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    anime_id = models.IntegerField()
    anime_mal_id = models.IntegerField()
    status = models.CharField(max_length=16) # watching, completed, on-hold, dropped, plan-to-watch
    score = models.IntegerField()
    episodes_watched = models.IntegerField()
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} {self.status} {self.anime_id}"
    
    class Meta:
        verbose_name_plural = "User Anime Lists"
