from django.http import JsonResponse


def csrf_failure(request, reason=""):

    return JsonResponse(
        {
            "error": "CSRF validation failed.",
            "detail": "The CSRF token is missing or invalid.",
        },
        status=403,
    )