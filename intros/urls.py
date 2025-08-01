from django.urls import path
from . import views

app_name = "intros"

urlpatterns = [
    # Main views
    path('', views.IntroListView.as_view(), name='list'),
    path('<int:pk>/', views.IntroDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.IntroUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.delete_intro, name='delete'),
    
    # Context-aware creation (creates new intro + relationship)
    path('create/<str:entity_type>/<int:entity_id>/', views.IntroCreateView.as_view(), name='create'),
    
    # Link existing intro to entity
    path('link/<str:entity_type>/<int:entity_id>/', views.IntroLinkView.as_view(), name='link'),
    
    # Relationship management
    path('relation/<int:relation_id>/status/', views.relation_status_update, name='relation_status_update'),
    path('relation/<int:relation_id>/delete/', views.delete_relation, name='delete_relation'),
    
    # Linking issues
    path('linking-issue/<int:intro_id>/<str:entity_type>/<int:entity_id>/', 
         views.linking_issue_view, name='linking_issue'),
    
    # AJAX endpoints for fetching intros (with relationship data)
    path('api/for-task/<int:task_id>/', views.ajax_intros_for_task, name='ajax_task_intros'),
    path('api/for-project/<int:project_id>/', views.ajax_intros_for_project, name='ajax_project_intros'),
    path('api/for-need/<int:need_id>/', views.ajax_intros_for_need, name='ajax_need_intros'),
    path('api/for-problem/<int:problem_id>/', views.ajax_intros_for_problem, name='ajax_problem_intros'),
    path('api/for-plan/<int:plan_id>/', views.ajax_intros_for_plan, name='ajax_plan_intros'),
]