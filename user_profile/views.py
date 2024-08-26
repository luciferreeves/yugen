import json
from django.shortcuts import render
from django.http import JsonResponse
from user_profile.models import UserPreferences

def user_profile(request):
    category = request.GET.get("category", "preferences")

    supported_categories = ["preferences", "anime_list", "user_directory"]
    if category not in supported_categories:
        category = "preferences"

    print(category)

    context = {
        "req_category": category
    }

    return render(request, "user_profile/user_profile.html", context)


def save_user_preferences(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)
    
    user = request.user

    data = json.loads(request.body)
    card_layout = data.get("cardLayout")
    title_language = data.get("titleLanguage")
    character_name_language = data.get("characterNameLanguage")
    default_language = data.get("defaultLanguage")
    default_provider = data.get("defaultProvider")
    default_watch_page = data.get("defaultWatchPage")
    show_history_on_home = data.get("showHistoryOnHome")
    auto_skip_intro = data.get("autoSkipIntro")
    auto_play_video = data.get("autoPlayVideo")
    auto_next_episode = data.get("autoNextEpisode")
    display_guild_name_instead_of_username = data.get("displayGuildNameInsteadOfUsername")

    user_preferences, created = UserPreferences.objects.get_or_create(user=user)
    user_preferences.card_layout = card_layout
    user_preferences.title_language = title_language
    user_preferences.character_name_language = character_name_language
    user_preferences.default_language = default_language
    user_preferences.default_provider = default_provider
    user_preferences.default_watch_page = default_watch_page
    user_preferences.show_history_on_home = show_history_on_home
    user_preferences.auto_skip_intro = auto_skip_intro
    user_preferences.auto_play_video = auto_play_video
    user_preferences.auto_next_episode = auto_next_episode
    user_preferences.display_guild_name_instead_of_username = display_guild_name_instead_of_username

    user_preferences.save()

    return JsonResponse({"success": "User preferences saved"}, status=200)
