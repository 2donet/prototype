from django.urls import path, include
from rest_framework.routers import DefaultRouter
from comment.api_views import CommentViewSet, CommentVoteViewSet, CommentReactionViewSet

router = DefaultRouter()
router.register(r'comments', CommentViewSet)
router.register(r'votes', CommentVoteViewSet)
router.register(r'reactions', CommentReactionViewSet)

app_name = 'comment-api'

urlpatterns = [
    path('', include(router.urls)),
]