from django.urls import path
from . import views
from .views import submission_detail

app_name = "submissions"
urlpatterns = [
    path("<int:submission_id>/", views.submission_detail, name="submission_detail"),

]