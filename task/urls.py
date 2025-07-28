from django.urls import path
from . import views
from .views import UpdateTaskView, CreateTaskView

app_name = "task"
urlpatterns = [
    # Existing routes
    path("<int:task_id>/", views.task_detail, name="task_detail"),
    path("all/", views.task_list, name="task_list"),  #

    path('create/', CreateTaskView.as_view(), name='task_create'),
    path('<int:task_id>/edit/', UpdateTaskView.as_view(), name='task_update'),
    path('<int:task_id>/add-skill/', views.add_skill_to_task, name='task_add_skill'),
    
    # New enhanced routes
    path('skill/<str:skill_name>/', views.skill_tasks, name='skill_tasks'),
    
    # AJAX API endpoints
    path('api/search/', views.api_task_search, name='api_task_search'),
    path('api/quick-update/<int:task_id>/', views.quick_task_update, name='api_quick_task_update'),
    path('api/skills/autocomplete/', views.api_skills_autocomplete, name='api_skills_autocomplete'),
    path('api/filter-options/', views.api_filter_options, name='api_filter_options'),
    path('debug/<int:task_id>/', views.debug_task_form, name='debug_task_form'),
]