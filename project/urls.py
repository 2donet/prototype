from django.urls import path, include

from . import views

app_name = "project"
urlpatterns = [
    path("", views.index, name="index"),
    path("<int:project_id>/", views.project, name="project"),
    path('create/', views.create_project, name='create_project'),
    path('skill/<str:skill_name>/', views.skill_projects, name='skill_detail'),
    path('api/', include('comment.api_urls')),

    # Member management URLs
    path('<int:project_id>/members/', views.project_members, name='project_members'),
    path('<int:project_id>/members/<int:user_id>/', views.member_detail, name='member_detail'),
    path('<int:project_id>/members/add/', views.add_member, name='add_member'),
    path('<int:project_id>/members/<int:user_id>/remove/', views.remove_member, name='remove_member'),
    path('<int:project_id>/join/', views.join_project, name='join_project'),
    path('<int:project_id>/leave/', views.leave_project, name='leave_project'),
]