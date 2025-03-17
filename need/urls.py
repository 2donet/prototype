from django.urls import path

from . import views
# from .views import UpdateTaskView

app_name = "need"
urlpatterns = [
    path("<int:need_id>/", views.need, name="need"),
    path("<int:need_id>/edit/", views.edit_need, name="edit_need"),
    path("create/<int:project_id>/", views.create_need_for_project, name="create_need_for_project"),
    path("create/task/<int:task_id>/", views.create_need_for_task, name="create_need_for_task"),
    path("<int:need_id>/delete/", views.delete_need, name="delete_need"),
    path("<int:need_id>/mark_status/<str:status>/", views.update_need_status, name="update_need_status"),
]