from user_profile.models import UserPreferences

class PreferencesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            user_preferences = UserPreferences.objects.get_or_create(user=request.user)[0]
            request.user.preferences = user_preferences

        response = self.get_response(request)
        return response
    
    