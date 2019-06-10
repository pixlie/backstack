from sanic import response

from ..config import settings


def handle_cors(request, allowed_methods, allowed_headers):
    if "ORIGIN" in request.headers:
        origin = request.headers["ORIGIN"]
        if origin in settings.ALLOWED_ORIGINS:
            headers = {
                "Access-Control-Allow-Methods": allowed_methods,
                "Access-Control-Allow-Headers": allowed_headers,
            }
            return response.raw("", status=204, headers=headers)
        else:
            return response.raw("", status=204)
    else:
        return response.raw("", status=204)
