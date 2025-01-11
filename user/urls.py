from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import person_memberships, membership_details
# from .views import UpdateTaskView


app_name = "user"
urlpatterns = [
    path("<int:person_id>/", views.userprofile, name="userprofile"),
    path('<int:person_id>/memberships', person_memberships, name='person_memberships'),
    path('membership/<int:membership_id>/', membership_details, name='membership_details'),
    path('signin/', views.signin_view, name='signin'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.custom_logout, name='logout'),
]