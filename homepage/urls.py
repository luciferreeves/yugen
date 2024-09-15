from django.urls import path

from . import views

app_name = "home"
urlpatterns = [
    path("", views.index, name="index"),
    path("search", views.search, name="search"),
    path("schedule", views.schedule, name="schedule"),
    path("watchlist", views.watchlist, name="watchlist"),
    path("q_search", views.search_json, name="q_search"),
]
