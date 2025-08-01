from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, Http404
from django.db.models import Count

from rest_framework import generics, permissions
from .models import Skill
from .serializers import SkillSerializer
from rest_framework.permissions import AllowAny
from project.models import Project  


class SkillListCreateView(generics.ListCreateAPIView):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [AllowAny]  # Allows public access 


def api_skills_autocomplete(request):
    """
    AJAX endpoint for skills autocomplete in task forms.
    Returns skills with task counts for better suggestions.
    """
    query = request.GET.get('q', '').strip()
    
    if not query:
        # Return popular skills when no query provided
        skills = Skill.objects.annotate(
            task_count=Count('task')
        ).order_by('-task_count', 'name')[:50]
    else:
        if len(query) < 2:
            return JsonResponse({'skills': []})
        
        # Filter skills based on query
        skills = Skill.objects.filter(
            name__icontains=query
        ).annotate(
            task_count=Count('task')
        ).order_by('-task_count', 'name')[:20]
    
    skills_data = [
        {
            'name': skill.name,
            'task_count': getattr(skill, 'task_count', 0)
        }
        for skill in skills
    ]
    
    return JsonResponse({'skills': skills_data})


def skill_detail(request, skill_id):
    # Use get_object_or_404 for cleaner error handling
    skill = get_object_or_404(Skill, id=skill_id)
    
    projects = Project.objects.filter(skills=skill)
    return render(request, 'skills/projects_with_skill.html', {'skill': skill, 'projects': projects})