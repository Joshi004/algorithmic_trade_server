from django.urls import path
from .views.AuthView import register, login, refresh_token

urlpatterns = [
    # Registration endpoint
    path('register/', register, name='register'),
    # Login endpoint
    path('login/', login, name='login'),
    # Token refresh endpoint
    path('refresh-token/', refresh_token, name='refresh_token'),
]
