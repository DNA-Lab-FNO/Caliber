from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("auth/status/", views.auth_status, name="auth_status"),
    path("auth/login/", views.login_view, name="login_view"),
    path("auth/register/", views.register_view, name="register_view"),
    path("auth/logout/", views.logout_view, name="logout_view"),
]
