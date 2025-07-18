from django.shortcuts import render, get_object_or_404

from rest_framework import generics, permissions
from .models import Skill
from .serializers import SkillSerializer
from rest_framework.permissions import AllowAny
from project.models import Project  
from django.http import Http404

class SkillListCreateView(generics.ListCreateAPIView):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [AllowAny]  # Allows public access 





def skill_detail(request, skill_name):
    try:
        skill = Skill.objects.get(name__iexact=skill_name)
    except Skill.DoesNotExist:
        # Handle case where skill doesn't exist
        raise Http404("Skill not found")
    except Skill.MultipleObjectsReturned:
        # Handle case where multiple skills exist
        # You could either:
        # 1. Get the first one
        skill = Skill.objects.filter(name__iexact=skill_name).first()
        # 2. Or redirect to an error page
        # return render(request, 'error.html', {'message': 'Multiple skills found'})
    
    projects = Project.objects.filter(skills=skill)
    return render(request, 'skills/projects_with_skill.html', {'skill': skill, 'projects': projects})