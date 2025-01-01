from django.urls import path

from . import views
# from .views import UpdateTaskView

app_name = "project_constructor"
# urlpatterns = [
#         path("", views.index, name="index"),
# ]

urlpatterns = [
    path('', views.create_project, name='create_project'),
    path('<int:project_id>/', views.project_details, name='project_details'),
]