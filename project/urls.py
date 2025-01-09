from django.urls import path

from . import views
# from .views import UpdateTaskView

app_name = "project"
urlpatterns = [
        path("", views.index, name="index"),
        path("<int:project_id>/", views.project, name="project"),
        path('create/', views.create_project, name='create_project'),
        path('old/<int:project_id>/', views.project_details, name='project_details'),
        ]



# urlpatterns = [
# ]