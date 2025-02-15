from django.shortcuts import render, get_object_or_404

from rest_framework import generics, permissions
from .models import Skill
from .serializers import SkillSerializer
from rest_framework.permissions import AllowAny
from project.models import Project  

class SkillListCreateView(generics.ListCreateAPIView):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [AllowAny]  # Allows public access 




def skill_detail(request, skill_name):
    skill = get_object_or_404(Skill, name__iexact=skill_name)  # Case-insensitive match
    projects = Project.objects.filter(skills=skill)  # Get all projects using this skill

    return render(request, 'skills/projects_with_skill.html', {'skill': skill, 'projects': projects})
