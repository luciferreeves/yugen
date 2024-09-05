from django.urls import path

from . import views

app_name = "detail"
urlpatterns = [
   path('<int:anime_id>', views.detail, name='detail'),
]
