from django.shortcuts import render

# Functions used to generate project related pages (remember to declare them in urls.py)

from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from project.models import Project, Connection
from comment.models import Comment
from task.models import Task
from need.models import Need
from user.models import User
from django.urls import path, reverse
from django.db.models import Prefetch
import json

from skills.models import Skill

from django.contrib.auth import get_user_model

def index(request):
    """
        Display a list of the latest projects.
        """
    # latest_projects_list = Project.objects.filter().order_by('id')
    latest_projects_list = Project.objects.exclude(
        incoming_connections__type='child'
    ).order_by('-id') # getting only standalone projects (excluding children)

    context = {"latest_projects_list": latest_projects_list,}
    return render(request, "index.html", context=context)

def project(request, project_id):
    content = get_object_or_404(Project, pk=project_id)
    tasks = Task.objects.filter(to_project=project_id)
    needs = Need.objects.filter(to_project=project_id).order_by('-priority', 'id')

    comments = Comment.objects.filter(to_project=project_id)


    # Get all child projects
    child_connections = Connection.objects.filter(
        from_project=content, 
        type='child', 
        status='approved'
    ).select_related('to_project')
    child_projects = [connection.to_project for connection in child_connections]
    # get parents
    parent_connections = Connection.objects.filter(
        to_project=content, 
        type='child', 
        status='approved'
    ).select_related('from_project')
    parent_projects = [connection.from_project for connection in parent_connections]
    
 

    context = {
        "content": content,
        "child_projects": child_projects, #list of project's children 
        "parent_projects": parent_projects, #list of project's parents
        "comments": comments,
        "tasks": tasks,
        "needs": needs,
    }
    return render(request, "details.html", context=context)


# @login_required
def project_details(request, project_id):
    # Pobierz instancję użytkownika na podstawie request.user
    # user = User.objects.get(name=request.user.name)
    user = User.objects.get(name='tester-1')
    project = get_object_or_404(Project, id=project_id, created_by=user)
    return render(request, 'project_details.html', {'project': project})



# @login_required
def create_project(request):
    if request.user.is_authenticated and request.method == 'POST':
        # Dane projektu
        name = request.POST.get('name')
        visibility = request.POST.get('visibility')
        status = request.POST.get('status')
        area = request.POST.get('area')
        tags = request.POST.get('tags')
        summary = request.POST.get('summary')
        desc = request.POST.get('desc')
        published = request.POST.get('published') == '1'  # Checkbox or select input

        # Utwórz projekt
        user = request.user 
        project = Project.objects.create(
            name=name,
            visibility=visibility,
            collaboration_mode='volunteering',
            status=status,
            area=area,
            tags=tags,
            summary=summary,
            desc=desc,
            created_by=user,
            published=published,
        )

        # Dane potrzeb
        need_names = request.POST.getlist('need_name[]')  # Lista nazw potrzeb
        need_descs = request.POST.getlist('need_desc[]')  # Lista opisów potrzeb
        need_priorities = request.POST.getlist('need_priority[]')  

        # Tworzenie każdej potrzeby (only if data exists)
        if need_names and need_descs and need_priorities:
            for name, desc, priority in zip(need_names, need_descs, need_priorities):
                if name.strip():  # Ensure name is not empty
                    Need.objects.create(
                        name=name,
                        desc=desc,
                        priority=priority,
                        created_by=user,
                        to_project=project,
                    )
        task_names = request.POST.getlist('task_name[]')  # List of task names
        task_descs = request.POST.getlist('task_desc[]')  # List of task descriptions
        task_priorities = request.POST.getlist('task_priority[]')  # List of task priorities

        # Create each task (only if data exists)
        if task_names and task_descs and task_priorities:
            for name, desc, priority in zip(task_names, task_descs, task_priorities):
                if name.strip():  # Ensure name is not empty
                    Task.objects.create(
                        name=name,
                        desc=desc,
                        priority=priority,
                        created_by=user,
                        to_project=project,
                    )
        skills_json = request.POST.get('skills')
        if skills_json:
            skill_names = json.loads(skills_json)
            for skill_name in skill_names:
                project.add_skill(skill_name)

        return redirect('project:project', project_id=project.id)

    return render(request, 'create_project.html')


# lsit of projects with certain skill

def skill_projects(request, skill_name):
    skill = get_object_or_404(Skill, name__iexact=skill_name)
    projects = skill.project_set.all()
    return render(request, 'skills/skill_projects.html', {'skill': skill, 'projects': projects})
