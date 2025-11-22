from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/live-session/(?P<session_id>[\w-]+)/$', consumers.LiveSessionConsumer.as_asgi()),
]