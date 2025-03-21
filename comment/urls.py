from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from .views import (
    load_replies, 
    add_comment, 
    comment_list_view, 
    single_comment_view,
    report_comment_view,
    report_list_view,
    report_detail_view,
    vote_comment,
    remove_vote,
    toggle_reaction,
    get_reactions_summary,
    delete_comment,
    ban_user,
    edit_comment
)

app_name = "comments"

urlpatterns = [
    path("load-replies/<int:comment_id>/", load_replies, name="load_replies"),
    path("add/", add_comment, name="add_comment"),
    path("list/<str:object_type>/<int:object_id>/", comment_list_view, name="comment_list"),
    path("<int:comment_id>/", single_comment_view, name="single_comment"),
    path("<int:comment_id>/report/", report_comment_view, name="report_comment"),
    path("reports/", report_list_view, name="report_list"),
    path("reports/<int:report_id>/", report_detail_view, name="report_detail"),
    
    # Rating-related paths
    path("<int:comment_id>/vote/", csrf_exempt(vote_comment), name="vote_comment"),
    path("<int:comment_id>/remove-vote/", csrf_exempt(remove_vote), name="remove_vote"),
    path("<int:comment_id>/reaction/", csrf_exempt(toggle_reaction), name="toggle_reaction"),
    path("<int:comment_id>/reactions/", get_reactions_summary, name="reactions_summary"),
    path("<int:comment_id>/delete/", delete_comment, name="delete_comment"),
    path("user/<int:user_id>/ban/", ban_user, name="ban_user"),
    path("<int:comment_id>/edit/", edit_comment, name="edit_comment"),
]