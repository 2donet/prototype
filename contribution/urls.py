from django.urls import path

from . import views

app_name = "contribution"
urlpatterns = [
        path("review", views.review, name="review"),
        ]

