from django.urls import path

from . import views
# from .views import UpdateTaskView

app_name = "task"
urlpatterns = [
    path("<int:task_id>/", views.task_detail, name="task_detail"),
]