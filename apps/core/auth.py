import json
from functools import wraps

from django.http import JsonResponse


def parse_request_data(request):
    if request.content_type and "application/json" in request.content_type:
        if not request.body:
            return {}
        try:
            return json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    return request.POST


def serialize_user(user):
    return {
        "email": user.email,
        "username": user.username,
    }


def login_required_json(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required."}, status=401)
        return view_func(request, *args, **kwargs)

    return wrapped