from django.urls import path
from .views import load_replies, add_comment

app_name = "comments"

urlpatterns = [
    path("load-replies/<int:comment_id>/", load_replies, name="load_replies"),
    path("add/", add_comment, name="add_comment"),
]



# from django.urls import path

# from . import views
# # from .views import UpdateTaskView
# from .views import comment_list_view, load_replies, add_comment
# app_name = "comment"
# urlpatterns = [
#     path("<str:object_type>/<int:object_id>/comments/", comment_list_view, name="comment_list"),
#     path("comments/load-replies/<int:comment_id>/", load_replies, name="load_replies"),
#     path("comments/add/", add_comment, name="add_comment"),
# ]