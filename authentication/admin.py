from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            None,
            {
                "fields": (
                    "discord_id",
                    "discord_access_token",
                    "discord_refresh_token",
                    "discord_token_type",
                    "discord_username",
                    "discord_avatar",
                    "discord_banner",
                    "discord_global_name",
                    "discord_guild_name",
                    "mal_token_type",
                    "mal_token_expires_in",
                    "mal_access_token",
                    "mal_refresh_token",
                )
            },
        ),
    )


admin.site.register(User, UserAdmin)
