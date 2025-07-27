from django.urls import path
from . import views

app_name = 'plans'

urlpatterns = [
    # General plan management
    path('create/', views.create_plan, name='create_plan'),
    path('<int:plan_id>/', views.plan_detail, name='plan_detail'),
    path('<int:plan_id>/edit/', views.edit_plan, name='edit_plan'),
    path('<int:plan_id>/delete/', views.delete_plan, name='delete_plan'),
    
    # Step management
    path('<int:plan_id>/steps/add/', views.add_step, name='add_step'),
    path('<int:plan_id>/steps/<int:step_id>/edit/', views.edit_step, name='edit_step'),
    path('<int:plan_id>/steps/<int:step_id>/delete/', views.delete_step, name='delete_step'),
    path('<int:plan_id>/steps/reorder/', views.reorder_steps, name='reorder_steps'),
    
    # Plan suggestions
    path('suggestion/<str:content_type>/<int:object_id>/', views.suggest_plan, name='suggest_plan'),
    path('suggestions/<int:suggestion_id>/approve/', views.approve_suggestion, name='approve_suggestion'),
    path('suggestions/<int:suggestion_id>/reject/', views.reject_suggestion, name='reject_suggestion'),
    path('suggestions/<int:suggestion_id>/withdraw/', views.withdraw_suggestion, name='withdraw_suggestion'),
    
]