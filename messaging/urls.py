from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    # Main conversation views
    path('', views.conversation_list, name='conversation_list'),
    path('start/', views.start_conversation, name='start_conversation'),
    path('conversation/<str:username>/', views.conversation_detail, name='conversation_detail'),
    
    # AJAX endpoints
    path('ajax/mark-read/<int:conversation_id>/', views.ajax_mark_read, name='ajax_mark_read'),
    path('ajax/unread-count/', views.get_unread_count, name='ajax_unread_count'),
    
    # Auth required page for anonymous users
    path('auth/<str:username>/', views.auth_required, name='auth_required'),
    
    # Compatibility with existing profile links - MUST BE LAST to avoid conflicts
    path('<str:username>/', views.message_with_user, name='message_with_user'),
]