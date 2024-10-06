from django.urls import path
from . import views

app_name = "read"
urlpatterns = [
    path('', views.index, name='index'),
    path('/<int:manga_id>/<str:chapter_id>', views.read, name='read'),
]
