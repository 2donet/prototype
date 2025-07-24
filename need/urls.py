from django.urls import path
from . import views

app_name = "need"
urlpatterns = [
    # Basic need operations
    path("<int:need_id>/", views.need, name="need"),
    path("<int:need_id>/edit/", views.edit_need, name="edit_need"),
    path("<int:need_id>/delete/", views.delete_need, name="delete_need"),
    path("<int:need_id>/status/<str:status>/", views.update_need_status, name="update_need_status"),
    
    # Need creation
    path("create/project/<int:project_id>/", views.create_need_for_project, name="create_need_for_project"),
    # path("create/task/<int:task_id>/", views.create_need_for_task, name="create_need_for_task"),
    
    # Time tracking
    path("<int:need_id>/log-time/", views.log_time, name="log_time"),
    
    # Assignments
    path("<int:need_id>/assign/", views.assign_need, name="assign_need"),
    # path("<int:need_id>/assignments/<int:assignment_id>/unassign/", views.unassign_need, name="unassign_need"),
    
    # Progress tracking
    path("<int:need_id>/progress/", views.update_progress, name="update_progress"),
    
    # History
    path("<int:need_id>/history/", views.need_history, name="history"),
    
    # Submissions
    # path("<int:need_id>/submissions/create/", views.create_submission, name="create_submission"),
    
]