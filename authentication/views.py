from django.http import JsonResponse
from django.contrib.auth import login
from authentication.utils import exchange_code, authenticate_user
from django.shortcuts import redirect


def callback(request):
    # Coming from Discord OAuth2
    code = request.GET.get("code")
    if not code:
        return JsonResponse({"error": "No code provided"})

    response = exchange_code(code=code)

    if "error" in response:
        return JsonResponse(response)

    user = authenticate_user(exchange_response=response)

    if not user:
        return JsonResponse({"error": "User not authorized"})

    # login the user and redirect to the referrer
    login(request, user)
    return redirect("home:index")
