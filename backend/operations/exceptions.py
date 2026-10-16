from rest_framework.views import exception_handler as drf_exception_handler


def api_exception_handler(exc, context):
    """Keep Django/DRF errors compatible with the frontend's `{error}` contract."""

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    details = response.data
    if isinstance(details, dict):
        message = details.get("detail")
        if not isinstance(message, str):
            message = "Request validation failed"
    elif isinstance(details, list) and details:
        message = str(details[0])
    else:
        message = str(details)

    response.data = {"error": message, "errors": details}
    return response
