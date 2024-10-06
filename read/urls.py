from django.urls import path

from . import views

app_name = "read"
urlpatterns = [
    path('', views.index, name='index'),
    path('/<str:manga_encoded_string>', views.read, name='read'),
]
