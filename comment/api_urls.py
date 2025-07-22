from django.urls import path, include
from rest_framework.routers import DefaultRouter
from comment.api_views import CommentViewSet, CommentVoteViewSet

router = DefaultRouter()
router.register(r'comments', CommentViewSet)
router.register(r'votes', CommentVoteViewSet)

app_name = 'comment-api'

urlpatterns = [
    path('', include(router.urls)),
]