from django.urls import path

from .views import sample_view
from .views import stock_view

urlpatterns = [
    path('',sample_view.api_home), # http://localhost:8000/tmu/
    path('update_stocks',stock_view.fetch_and_update_stocks), # http://localhost:8000/tmu/update_stocks
    path('get_all_stocks',stock_view.get_stocks_list)
] 