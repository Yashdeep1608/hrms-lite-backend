from fastapi import Request


def get_lang_from_request(request: Request):
    return request.headers.get("Accept-Language", "en")
