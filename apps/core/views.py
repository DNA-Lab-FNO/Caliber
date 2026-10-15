from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from django.middleware.csrf import get_token
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.shortcuts import render

from .auth import parse_request_data, serialize_user
from .models import User


def index(request):
    get_token(request)
    return render(
        request, "core/index.html", {"debug": settings.DEBUG}
    )  # Pass debug flag to template for conditional frontend behavior


@require_GET
def auth_status(request):
    get_token(request)
    if request.user.is_authenticated:
        return JsonResponse({"authenticated": True, "user": serialize_user(request.user)})

    return JsonResponse({"authenticated": False, "user": None})


@require_POST
def login_view(request):
    data = parse_request_data(request)
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not email or not password:
        return JsonResponse({"error": "Email and password are required."}, status=400)

    user = authenticate(request, email=email, password=password)
    if user is None:
        return JsonResponse({"error": "Invalid email or password."}, status=400)

    login(request, user)
    get_token(request)
    return JsonResponse({"authenticated": True, "user": serialize_user(user)})


@require_POST
def register_view(request):
    data = parse_request_data(request)
    email = str(data.get("email", "")).strip().lower()
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    password_confirm = str(data.get("password_confirm", ""))

    if not email or not username or not password:
        return JsonResponse(
            {"error": "Email, username, and password are required."}, status=400
        )

    if password != password_confirm:
        return JsonResponse({"error": "Passwords do not match."}, status=400)

    if User.objects.filter(email=email).exists():
        return JsonResponse({"error": "An account with that email already exists."}, status=400)

    user = User.objects.create_user(email=email, username=username, password=password)
    login(request, user)
    get_token(request)
    return JsonResponse({"authenticated": True, "user": serialize_user(user)}, status=201)


@require_POST
def logout_view(request):
    logout(request)
    get_token(request)
    return JsonResponse({"authenticated": False})
