from django.urls import path, re_path
from .views.AuthView import register, login, refresh_token, logout

urlpatterns = [
    # Registration endpoint - handle both with and without trailing slash
    re_path(r'^register/?$', register, name='register'),
    # Login endpoint - handle both with and without trailing slash
    re_path(r'^login/?$', login, name='login'),
    # Token refresh endpoint - handle both with and without trailing slash
    re_path(r'^refresh-token/?$', refresh_token, name='refresh_token'),
    # Logout endpoint - handle both with and without trailing slash
    re_path(r'^logout/?$', logout, name='logout'),
]
