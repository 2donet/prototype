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
    delete_comment,
    enhanced_delete_comment,
    ban_user,
    edit_comment,
    # Enhanced views
    enhanced_report_list_view,
    enhanced_report_detail_view,
    # New history views
    comment_history_view,
    comment_moderated_history,
)

app_name = "comments"

urlpatterns = [
    # Existing URLs
    path("load-replies/<int:comment_id>/", load_replies, name="load_replies"),
    path("add/", add_comment, name="add_comment"),
    path("list/<str:object_type>/<int:object_id>/", comment_list_view, name="comment_list"),
    path("<int:comment_id>/", single_comment_view, name="single_comment"),
    path("<int:comment_id>/report/", report_comment_view, name="report_comment"),
    
    # Legacy report URLs (keep for backwards compatibility)
    path("reports/", report_list_view, name="report_list"),
    path("reports/<int:report_id>/", report_detail_view, name="report_detail"),
    
    # Enhanced moderation URLs
    path("moderation/", enhanced_report_list_view, name="enhanced_report_list"),
    path("moderation/<int:comment_id>/", enhanced_report_detail_view, name="enhanced_report_detail"),
    path("moderation/<int:comment_id>/delete/", enhanced_delete_comment, name="enhanced_delete_comment"),
    
    # Action URLs
    path("<int:comment_id>/vote/", csrf_exempt(vote_comment), name="vote_comment"),
    path("<int:comment_id>/remove-vote/", csrf_exempt(remove_vote), name="remove_vote"),
    path("<int:comment_id>/delete/", delete_comment, name="delete_comment"),  # Legacy delete
    path("user/<int:user_id>/ban/", ban_user, name="ban_user"),
    path("<int:comment_id>/edit/", edit_comment, name="edit_comment"),
    
    # New History URLs
    path("<int:comment_id>/history/", comment_history_view, name="comment_history"),
    path("<int:comment_id>/history/moderated/", comment_moderated_history, name="comment_moderated_history"),
]
