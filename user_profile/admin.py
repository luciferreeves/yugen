from django.contrib import admin
from .models import UserPreferences, UserHistory

# Register your models here.
admin.site.register(UserPreferences)
admin.site.register(UserHistory)