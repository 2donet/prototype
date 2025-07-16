from django.urls import path

from . import views
# from .views import UpdateTaskView

app_name = "task"
urlpatterns = [
    path("<int:task_id>/", views.task_detail, name="task_detail"),
    path("all/", views.task_list, name="task_list"),
    path('<int:task_id>/add-skill/', views.add_skill_to_task, name='task_add_skill'),
    
]