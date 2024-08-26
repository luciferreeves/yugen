from django.http import HttpResponseRedirect
from django.contrib.auth import login, logout
from authentication.utils import exchange_code, authenticate_user, get_redirect_uri
from django.shortcuts import redirect, render


def callback(request):
    if request.user.is_authenticated:
        return redirect("home:index")

    code = request.GET.get("code")
    if not code:
        return render(request, "messages/unauthorized.html", {"error": "You can't access the site if you keep cancelling the login!", "redirect_uri": get_redirect_uri()})

    response = exchange_code(code=code)

    if "error" in response:
        return render(request, "messages/unauthorized.html", {"error": "You did something crazy, didn't you?", "redirect_uri": get_redirect_uri()})

    user = authenticate_user(exchange_response=response)

    if not user:
        return redirect("auth:unauthorized")

    next_url = request.session.pop("next", None)
    # login the user and redirect to the referrer
    login(request, user)
    return redirect(next_url if next_url else "home:index")

def logout_user(request):
    logout(request)
    return HttpResponseRedirect(request.META.get("HTTP_REFERER"))

def unauthorized(request):
    if request.user.is_authenticated:
        return redirect("home:index")

    return render(request, "messages/unauthorized.html", {"redirect_uri": get_redirect_uri(), "error": "You are not part of our elite cult!"})
