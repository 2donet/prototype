from django.urls import path
from .views import SkillListCreateView, skill_detail, api_skills_autocomplete

urlpatterns = [
    path('api/skills/', SkillListCreateView.as_view(), name='skills-list'),
    path('api/skills-autocomplete/', api_skills_autocomplete, name='api_skills_autocomplete'),
    path('p/skill/<int:skill_id>/', skill_detail, name='skill_detail'),
]