from django.urls import path
from . import views

app_name = 'submissions'

urlpatterns = [
    # General submission creation
    path('create/', 
         views.create_submission, 
         name='create_submission'),
    
    # Quick submission for specific content
    path('create/<str:content_type>/<int:content_id>/', 
         views.create_submission_for_content, 
         name='create_submission_for_content'),
    
    # List submissions for specific content
    path('<str:content_type>/<int:content_id>/submissions/', 
         views.submission_list, 
         name='submission_list'),
    
    # Submission detail view
    path('<int:submission_id>/', 
         views.submission_detail, 
         name='submission_detail'),
    
    # AJAX endpoint for status updates
    path('<int:submission_id>/update-status/', 
         views.update_submission_status, 
         name='update_submission_status'),
]