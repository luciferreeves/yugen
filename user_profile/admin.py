from django.contrib import admin
from .models import UserPreferences, UserHistory, UserAnimeList

# Register your models here.
admin.site.register(UserPreferences)
admin.site.register(UserHistory)
admin.site.register(UserAnimeList)