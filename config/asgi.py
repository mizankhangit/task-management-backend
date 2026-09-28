import os

from channels.routing import (
    ProtocolTypeRouter,
    URLRouter,
)
from django.core.asgi import (
    get_asgi_application,
)

from apps.core.middleware import (
    JWTAuthMiddleware,
)

from apps.notifications.routing import (
    websocket_urlpatterns as notification_urls,
)

from apps.tasks.routing import (
    websocket_urlpatterns as task_urls,
)


websocket_urlpatterns = (
    notification_urls
    + task_urls
)


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

django_asgi_app = get_asgi_application()


application = ProtocolTypeRouter({
    "http": django_asgi_app,

    "websocket": JWTAuthMiddleware(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})