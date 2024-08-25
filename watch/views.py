from django.shortcuts import render, redirect

def watch(request, anime_id, episode=None):
    if not episode or episode < 1:
        return redirect("watch:watch_episode", anime_id=anime_id, episode=1)
    return render(request, "watch/watch.html", {"anime_id": anime_id, "episode": episode})