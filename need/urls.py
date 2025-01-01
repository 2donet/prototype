from django.urls import path

from . import views
# from .views import UpdateTaskView

app_name = "need"
urlpatterns = [
            path("<int:need_id>/", views.need, name="need"),
]