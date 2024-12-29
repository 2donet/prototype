from django.shortcuts import render

# Create your views here.

from django.shortcuts import get_object_or_404, render, redirect
from project.models import Project
from comment.models import Comment
from task.models import Task
from need.models import Need
from django.urls import path, reverse
from django.db.models import Prefetch



def index(request):
    latest_projects_list = Project.objects.order_by('id')
    context = {"latest_projects_list": latest_projects_list,}
    return render(request, "index.html", context=context)

def project(request, project_id):
    content = get_object_or_404(Project, pk=project_id)
    tasks = Task.objects.filter(to_project=project_id)

    needs = Need.objects.filter(to_project=project_id)

    # part_of_project = Project.objects.filter(subprojects=project_id).order_by('-importance')
    # subprojects = project.subprojects.order_by('-importance')
    # goals = Goal.objects.filter(project=project_id).order_by('-importance')
    # introductions = Introduction.objects.filter(project=project_id).order_by('-importance')
    # requirements = Requirement.objects.filter(project=project_id).order_by('-importance')
    # last_status = Status.objects.filter(project=project_id).order_by('-pub_date')[:1]
    # old_status = Status.objects.filter(project=project_id).order_by('-pub_date')[1:]
    # comments = Comment.objects.filter(project=project_id).order_by('-pub_date')
    # needs = Need.objects.filter(project=project_id).order_by('-importance')
    # assumptions = Assumption.objects.filter(project=project_id).order_by('-importance')
    # communities = Community.objects.filter(project=project_id).order_by('-importance')
    # problems = Problem.objects.filter(project=project_id).order_by('-importance')

    comments = Comment.objects.filter(to_project=project_id)
    # comments = Comment.objects.filter(to_project=project_id).prefetch_related(
    #     Prefetch("replies", queryset=Comment.objects.select_related("user"))
    # )

    context = {"content": content,
    "comments":comments,
    "tasks": tasks,
    "needs":needs,
            #    "part_of_project": part_of_project,
            #    "subprojects": subprojects,
            #    "tasks": tasks,
            #    "goals": goals,
            #    "problems": problems,
            #    "introductions": introductions,
            #    "last_status": last_status,
            #    "old_status": old_status,
            #    "requirements": requirements,
            #    "comments": comments,
            #    "assumptions": assumptions,
            #    "needs": needs,
            #    "communities": communities,
               }
    return render(request, "details.html", context=context)