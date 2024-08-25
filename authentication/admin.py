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
                )
            },
        ),
    )


admin.site.register(User, UserAdmin)
