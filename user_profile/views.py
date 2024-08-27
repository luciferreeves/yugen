import json
from django.shortcuts import render
from django.http import JsonResponse
import requests
from user_profile.models import UserPreferences
from authentication.utils import get_mal_redirect_uri, get_single_anime_mal, get_user_mal_list

def user_profile(request):
    category = request.GET.get("category", "preferences")

    supported_categories = ["preferences", "anime_list", "update"]
    if category not in supported_categories:
        category = "preferences"


    context = {
        "req_category": category
    }

    if not request.user.mal_access_token:
        mal_auth_uri, code_challenge = get_mal_redirect_uri()
        context["mal_auth_uri"] = mal_auth_uri
    else:
        if category == "anime_list":
            offset = request.GET.get("offset", 0)
            filters_supported = ["watching", "completed", "on_hold", "dropped", "plan_to_watch"]
            filter = request.GET.get("filter", "")
            if filter not in filters_supported:
                filter = ""
            mal_list, prev, next = get_user_mal_list(request.user.mal_access_token, limit=24, offset=offset, filter=filter)
            context["mal_list"] = mal_list
            if prev:
                context["prev_offset"] = prev.split("offset=")[1].split("&")[0]
            if next:
                context["next_offset"] = next.split("offset=")[1].split("&")[0]
            if filter:
                context["filter"] = filter
        
        if category == "update":
            mal_id = request.GET.get("mal_id")
            if mal_id:
                mal_data = get_single_anime_mal(request.user.mal_access_token, mal_id)
                if mal_data:
                    mal_data["average_episode_duration"] = mal_data["average_episode_duration"] // 60 + 1
                    context["mal_data"] = mal_data
                    context["mal_episode_range"] = range(1, mal_data["num_episodes"] + 1)

    return render(request, "user_profile/user_profile.html", context)


def update_user_mal_list(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)
    
    user = request.user
    data = json.loads(request.body)
    mal_id = data.get("mal_id")
    status = data.get("status")
    score = data.get("score")
    num_watched_episodes = data.get("episodes")
    
    if status not in ["watching", "completed", "on_hold", "dropped", "plan_to_watch", "add_to_list"]:
        return JsonResponse({"error": "Invalid status"}, status=400)

    if not user.mal_access_token:
        return JsonResponse({"error": "User has not connected their MAL account"}, status=400)
    
    base_url = f"https://api.myanimelist.net/v2/anime/{mal_id}/my_list_status"
    headers = {"Authorization": f"Bearer {user.mal_access_token}", "Content-Type": "application/x-www-form-urlencoded"}
    formdata = {
        "score": int(score),
        "num_watched_episodes": num_watched_episodes
    }

    if status != "add_to_list":
        formdata["status"] = status

    response = requests.put(base_url, headers=headers, data=formdata)
    if response.status_code == 200:
        return JsonResponse({"success": "MAL list updated"}, status=200)
    else:
        return JsonResponse({"error": "Failed to update MAL list"}, status=500)


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
    smart_mal_sync = data.get("smartMALSync")

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
    user_preferences.smart_mal_sync = smart_mal_sync

    try:
        user_preferences.save()
        return JsonResponse({"success": "User preferences saved"}, status=200)
    except Exception as e:
        print(e)
        return JsonResponse({"error": "Failed to save user preferences"}, status=500)
