from django.urls import path
from .views import (
    load_replies, 
    add_comment, 
    comment_list_view, 
    single_comment_view,
    report_comment_view,
    report_list_view,
    report_detail_view
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
]