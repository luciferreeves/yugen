from django.urls import path

from . import views

app_name = "home"
urlpatterns = [
    path("", views.index, name="index"),
    path("q_search/", views.search_json, name="q_search"),
]
