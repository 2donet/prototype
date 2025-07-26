from django.urls import path, include

from . import views

app_name = "project"
urlpatterns = [
    path("", views.index, name="index"),
    path("<int:project_id>/", views.project, name="project"),
    path('create/', views.create_project, name='create_project'),
    path('api/', include('comment.api_urls')),
    
    path('skill/<str:skill_name>/', views.skill_projects, name='skill_detail'), #list of projects with a selected skill

    path('<int:project_id>/join/', views.join_project, name='join_project'),
    path('<int:project_id>/leave/', views.leave_project, name='leave_project'),
    
    path('<int:project_id>/members/', views.project_members, name='project_members'),
    path('<int:project_id>/members/<int:user_id>/', views.member_detail, name='member_detail'),
    path('<int:project_id>/members/add/', views.add_member, name='add_member'),
    path('<int:project_id>/members/<int:user_id>/remove/', views.remove_member, name='remove_member'),

    path('<int:project_id>/localizations/add/', views.add_localization, name='add_localization'),
    path('<int:project_id>/localizations/<int:localization_id>/edit/', views.edit_localization, name='edit_localization'),
    path('<int:project_id>/localizations/<int:localization_id>/delete/', views.delete_localization, name='delete_localization'),
    path('<int:project_id>/localizations/', views.manage_localizations, name='manage_localizations'),


    path('<int:project_id>/moderate/', views.project_moderation_dashboard, name='moderation_dashboard'),
    path('<int:project_id>/moderate/comments/', views.project_comments_moderation, name='comments_moderation'),
    path('<int:project_id>/moderate/comments/<int:comment_id>/action/', views.moderate_comment_action, name='moderate_comment_action'),
    path('<int:project_id>/moderate/tasks/', views.project_tasks_management, name='tasks_management'),
    path('<int:project_id>/moderate/needs/', views.project_needs_management, name='needs_management'),
    path('<int:project_id>/moderate/members/', views.project_members_management, name='members_management'),
    path('<int:project_id>/moderate/locations/', views.project_locations_management, name='locations_management'),
    path('<int:project_id>/moderate/subprojects/', views.project_subprojects_management, name='subprojects_management'),


        # Subproject management
    path('<int:project_id>/subprojects/', views.project_subprojects_management, name='subprojects_management'),
    path('<int:project_id>/subprojects/create/', views.create_subproject, name='create_subproject'),
    path('<int:project_id>/subprojects/connect/', views.connect_existing_project, name='connect_existing_project'),
    path('<int:project_id>/subprojects/request-parent/', views.request_parent_connection, name='request_parent_connection'),  # NEW LINE
    path('<int:project_id>/subprojects/disconnect/<int:connection_id>/', views.disconnect_subproject, name='disconnect_subproject'),
    
    # Connection approval/rejection
    path('connections/<int:connection_id>/approve/', views.approve_connection, name='approve_connection'),
    path('connections/<int:connection_id>/reject/', views.reject_connection, name='reject_connection'),
    
    # API endpoints
    path('api/search-projects/', views.api_search_projects, name='api_search_projects'),
    
]