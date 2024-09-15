from django.urls import path

from . import views

app_name = "watch"
urlpatterns = [
   path('', views.index, name='index'),
   path('/<int:anime_id>', views.watch, name='watch'),
   path('/<int:anime_id>/<int:episode>', views.watch, name='watch_episode'),
   path('/zid:<str:zid>', views.watch_via_zid, name='watch_via_zid'),
   path('/update_watch_history', views.update_episode_watch_time, name='update_watch_history'),
   path('/remove_anime_from_watchlist', views.remove_anime_from_watchlist, name='remove_anime_from_watchlist'),
   path('/malId:<int:mal_id>$zid:<str:zid>', views.watch_via_zid_mal_id, name='watch_via_zid_mal_id'), # if anilist id is not available
]
