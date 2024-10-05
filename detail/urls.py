from django.urls import path

from . import views

app_name = "detail"
urlpatterns = [
   path('anime', views.index, name='index'),
   path('manga', views.index, name='index'),
   path('anime/<int:anime_id>', views.anime, name='anime'),
]
