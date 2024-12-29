from django.urls import path

from . import views
from .views import person_memberships, membership_details
# from .views import UpdateTaskView


app_name = "user"
urlpatterns = [
    path("<int:person_id>/", views.userprofile, name="userprofile"),
    path('<int:person_id>/memberships', person_memberships, name='person_memberships'),
    path('membership/<int:membership_id>/', membership_details, name='membership_details'),
]