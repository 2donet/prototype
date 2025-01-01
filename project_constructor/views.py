from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from project.models import Project
from user.models import User

from django.contrib.auth import get_user_model

@login_required
def create_project(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        visibility = request.POST.get('visibility')
        status = request.POST.get('status')
        area = request.POST.get('area')
        tags = request.POST.get('tags')
        summary = request.POST.get('summary')
        desc = request.POST.get('desc')
        published = request.POST.get('published') == '1'  # Checkbox or select input

        # Upewnij się, że `request.user` jest instancją `User`
        # User = get_user_model()
        # user = "tester-1"
        user = User.objects.get(name='tester-1')

        # Tworzenie projektu
        project = Project.objects.create(
            name=name,
            visibility=visibility,
            collaboration_mode='volunteering',
            status=status,
            area=area,
            tags=tags,
            summary=summary,
            desc=desc,
            created_by=user,  # Użycie instancji User
            published=published,
        )
        return redirect('project_constructor:project_details', project_id=project.id)

    return render(request, 'create_project.html')



@login_required
def project_details(request, project_id):
    # Pobierz instancję użytkownika na podstawie request.user
    # user = User.objects.get(name=request.user.name)
    user = User.objects.get(name='tester-1')
    # Pobierz projekt przypisany do tego użytkownika
    project = get_object_or_404(Project, id=project_id, created_by=user)

    return render(request, 'project_details.html', {'project': project})





















# from django.shortcuts import render
# from django.urls import path
# from . import views
# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.auth.decorators import login_required
# # from .models import ProjectDraft
#
# # Create your views here.
#
# def index(request):
#     context = {"key": "value"}  # Przykładowy kontekst
#     return render(request, "index.html", context)
#
#
#
#
# @login_required
# def create_project(request):
#     if request.method == 'POST':
#         title = request.POST.get('title')
#         visibility = request.POST.get('visibility')
#         collaboration_mode = 'volunteering'  # Fixed value
#         status = request.POST.get('status')
#         area = request.POST.get('area')
#         tags = request.POST.get('tags')
#         summary = request.POST.get('summary')
#         description = request.POST.get('description')
#
#         # Save project draft
#         project = ProjectDraft.objects.create(
#             title=title,
#             visibility=visibility,
#             collaboration_mode=collaboration_mode,
#             status=status,
#             area=area,
#             tags=tags,
#             summary=summary,
#             description=description,
#             created_by=request.user,
#         )
#         return redirect('project_constructor:project_details', project_id=project.id)
#
#     return render(request, 'create_project.html')
#
# @login_required
# def project_details(request, project_id):
#     project = get_object_or_404(ProjectDraft, id=project_id, created_by=request.user)
#     return render(request, 'project_details.html', {'project': project})
