"""
ASGI config for ats_base project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path 
from ats_gateway.consumers.ats_consumer import ATSConsumer
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ats_base.settings')

ws_patterns = [
path('ws/ats/', ATSConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    'http' : get_asgi_application(),
    'websocket': URLRouter(ws_patterns)
})
