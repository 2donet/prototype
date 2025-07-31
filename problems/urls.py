# problems/urls.py
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from .views import (
    problem_list_for_project,
    problem_detail,
    create_problem,
    edit_problem,
    assign_user,
    unassign_user,
)

app_name = "problems"

urlpatterns = [
    # Template-based views
    path("project/<int:project_id>/", problem_list_for_project, name="list_for_project"),
    path("<int:problem_id>/", problem_detail, name="detail"),
    path("create/", create_problem, name="create"),
    path("<int:problem_id>/edit/", edit_problem, name="edit"),
    
    # AJAX action endpoints
    path("<int:problem_id>/assign/", csrf_exempt(assign_user), name="assign_user"),
    path("<int:problem_id>/unassign/", csrf_exempt(unassign_user), name="unassign_user"),
]