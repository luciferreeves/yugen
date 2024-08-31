from django.urls import path

from . import views

app_name = "watch"
urlpatterns = [
   path('<int:anime_id>/', views.watch, name='watch'),
   path('<int:anime_id>/<int:episode>/', views.watch, name='watch_episode'),
   path('update_watch_history/', views.update_episode_watch_time, name='update_watch_history'),
]
