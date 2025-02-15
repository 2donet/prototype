from django.urls import path
from .views import SkillListCreateView, skill_detail

urlpatterns = [
    path('api/skills/', SkillListCreateView.as_view(), name='skills-list'),
    path('p/skill/<str:skill_name>/', skill_detail, name='skill_detail'),
    
]

