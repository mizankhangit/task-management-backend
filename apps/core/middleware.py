from urllib.parse import parse_qs
import uuid
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def get_user_from_token(token):
    try:
        access_token = AccessToken(token)

        user_id = access_token["user_id"]

        from django.contrib.auth.models import User

        return User.objects.get(
            id=user_id,
            is_active=True,
        )

    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):

    async def __call__(
        self,
        scope,
        receive,
        send,
    ):
        query_string = scope.get(
            "query_string",
            b"",
        ).decode()

        query_params = parse_qs(
            query_string
        )

        token = query_params.get(
            "token",
            [None],
        )[0]

        if token:
            scope["user"] = (
                await get_user_from_token(token)
            )
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(
            scope,
            receive,
            send,
        )

class RequestIDMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        request_id = request.headers.get(
            "X-Request-ID"
        )

        if not request_id:
            request_id = str(uuid.uuid4())

        request.request_id = request_id

        response = self.get_response(
            request
        )

        response["X-Request-ID"] = request_id

        return response