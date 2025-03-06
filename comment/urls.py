from django.urls import path
from .views import load_replies, add_comment, comment_list_view, single_comment_view

app_name = "comments"

urlpatterns = [
    path("load-replies/<int:comment_id>/", load_replies, name="load_replies"),
    path("add/", add_comment, name="add_comment"),
    path("list/<str:object_type>/<int:object_id>/", comment_list_view, name="comment_list"),
    path("<int:comment_id>/", single_comment_view, name="single_comment"),
]