from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    # Main conversation views
    path('', views.conversation_list, name='conversation_list'),
    path('conversation/<str:username>/', views.conversation_detail, name='conversation_detail'),
    path('start/', views.start_conversation, name='start_conversation'),
    
    # Compatibility with existing profile links
    path('<str:username>/', views.message_with_user, name='message_with_user'),
    
    # AJAX endpoints
    path('ajax/mark-read/<int:conversation_id>/', views.ajax_mark_read, name='ajax_mark_read'),
    path('ajax/unread-count/', views.get_unread_count, name='ajax_unread_count'),
]