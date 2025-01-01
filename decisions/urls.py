from django.urls import path
from .views import decision_details
app_name = "decisions"
urlpatterns = [

    path('decision/<int:decision_id>/', decision_details, name='decision_details'),
]
