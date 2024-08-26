from django.urls import path

from . import views

app_name = "auth"
urlpatterns = [
    path("callback", views.callback, name="callback"),
    path("MALSync", views.MALSync, name="MALSync"),
    path("logout", views.logout_user, name="logout"),
    path("unauthorized", views.unauthorized, name="unauthorized"),
]
