from django.shortcuts import render

# Create your views here.

from django.shortcuts import get_object_or_404, render, redirect
from comment.models import Comment

from need.models import Need
from django.urls import path, reverse
from django.db.models import Prefetch




def need(request, need_id):
    content = get_object_or_404(Need, pk=need_id)
    
    comments = Comment.objects.filter(to_need=need_id).prefetch_related(
        Prefetch("replies", queryset=Comment.objects.select_related("user"))
    )
    context = {"content": content,
    "comments":comments,
    
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
    # when loading template using "details.html" instead of "need/details.html", the project template is loaded (even when)
    # adding more logic to the project's details.html may be used 