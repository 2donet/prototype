from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .api_views import (
    ProblemViewSet,
    filtered_problems_api,
    search_users_for_assignment,
)

router = DefaultRouter()
router.register(r'problems', ProblemViewSet)

app_name = 'problems-api'

urlpatterns = [
    # DRF router URLs
    path('', include(router.urls)),
    
    # Custom API endpoints
    path('problems/filtered/', filtered_problems_api, name='filtered_problems'),
    path('users/search/', search_users_for_assignment, name='search_users'),
]