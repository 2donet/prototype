from django.shortcuts import render

# Create your views here.

from django.shortcuts import get_object_or_404, render, redirect
from comment.models import Comment

from need.models import Need
from django.urls import path, reverse
from django.db.models import Prefetch
from django.contrib import messages
from utils.permissions import user_can_moderate_need
from django.contrib.auth.decorators import login_required

from task.models import Task
from project.models import Project

def need(request, need_id):
    content = get_object_or_404(Need, pk=need_id)
    
    comments = Comment.objects.filter(to_need=need_id).prefetch_related(
        Prefetch("replies", queryset=Comment.objects.select_related("user"))
    )
    context = {"content": content,
    "comments":comments,
               }
    return render(request, "details.html", context=context)
    
@login_required
def edit_need(request, need_id):
    """View to edit an existing need"""
    need = get_object_or_404(Need, pk=need_id)
    
    # Check permissions
    if not need.user_can_edit(request.user):
        messages.error(request, "You don't have permission to edit this need.")
        return redirect('need:need', need_id=need.id)
    
    if request.method == 'POST':
        # Process form data
        need.name = request.POST.get('name', need.name)
        need.desc = request.POST.get('desc', need.desc)
        need.priority = request.POST.get('priority', need.priority)
        need.status = request.POST.get('status', need.status)
        need.tags = request.POST.get('tags', need.tags)
        need.visibility = request.POST.get('visibility', need.visibility)
        need.save()
        
        messages.success(request, "Need updated successfully.")
        return redirect('need:need', need_id=need.id)
    
    context = {
        'need': need,
        'parent': need.get_parent(),
    }
    return render(request, "need/edit_need.html", context=context)


def moderate_need_comment(request, need_id, comment_id):
    need = get_object_or_404(Need, pk=need_id)
    comment = get_object_or_404(Comment, pk=comment_id, to_need=need)
    
    # Check if the user has permission to moderate
    if not user_can_moderate_need(request.user, need):
        messages.error(request, "You don't have permission to moderate comments on this need.")
        return redirect('need:need', need_id=need.id)
    
@login_required
def create_need_for_project(request, project_id):
    """View to create a new need associated with a project"""
    project = get_object_or_404(Project, pk=project_id)
    
    # Check if user has permission to add needs to this project
    if not project.user_can_contribute(request.user):
        messages.error(request, "You don't have permission to add needs to this project.")
        return redirect('project:project', project_id=project.id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        desc = request.POST.get('desc')
        priority = request.POST.get('priority', 0)
        
        if not name:
            messages.error(request, "Need name is required.")
            return redirect('need:create_need_for_project', project_id=project.id)
        
        # Create the need
        need = Need.objects.create(
            name=name,
            desc=desc,
            priority=priority,
            created_by=request.user,
            to_project=project
        )
        
        messages.success(request, f"Need '{name}' created successfully.")
        return redirect('project:project', project_id=project.id)
    
    context = {
        'project': project,
        'mode': 'create',
    }
    return render(request, 'need/edit_need.html', context)

@login_required
def create_need_for_task(request, task_id):
    """View to create a new need associated with a task"""
    task = get_object_or_404(Task, pk=task_id)
    
    # Check if task has a project and user has permission
    project = task.to_project
    if project and not project.user_can_contribute(request.user):
        messages.error(request, "You don't have permission to add needs to this task.")
        return redirect('task:task', task_id=task.id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        desc = request.POST.get('desc')
        priority = request.POST.get('priority', 0)
        
        if not name:
            messages.error(request, "Need name is required.")
            return redirect('need:create_need_for_task', task_id=task.id)
        
        # Create the need
        need = Need.objects.create(
            name=name,
            desc=desc,
            priority=priority,
            created_by=request.user,
            to_task=task
        )
        
        messages.success(request, f"Need '{name}' created successfully.")
        return redirect('task:task', task_id=task.id)
    
    context = {
        'task': task,
        'mode': 'create',
    }
    return render(request, 'need/edit_need.html', context)


@login_required
def delete_need(request, need_id):
    """View to delete an existing need"""
    need = get_object_or_404(Need, pk=need_id)
    
    # Store references for redirection after deletion
    project = need.to_project
    task = need.to_task
    
    # Check if user has permission to delete this need
    if not (request.user == need.created_by or 
            (project and project.user_can_moderate(request.user)) or
            request.user.is_superuser):
        messages.error(request, "You don't have permission to delete this need.")
        return redirect('need:need', need_id=need.id)
    
    if request.method == 'POST':
        # Delete the need
        need_name = need.name
        need.delete()
        
        messages.success(request, f"Need '{need_name}' has been deleted.")
        
        # Redirect based on context
        if project:
            return redirect('project:project', project_id=project.id)
        elif task:
            return redirect('task:task', task_id=task.id)
        else:
            return redirect('project:index')
    
    # For GET requests, show confirmation page
    context = {
        'need': need,
        'project': project,
        'task': task,
    }
    return render(request, 'need/delete_need.html', context)


@login_required
def update_need_status(request, need_id, status):
    """View to update the status of a need"""
    need = get_object_or_404(Need, pk=need_id)
    
    # Check if user has permission to update this need
    if not (request.user == need.created_by or 
            (need.to_project and need.to_project.user_can_contribute(request.user)) or
            request.user.is_superuser):
        messages.error(request, "You don't have permission to update this need's status.")
        return redirect('need:need', need_id=need.id)
    
    # Validate status
    valid_statuses = ['pending', 'in_progress', 'fulfilled', 'canceled']
    if status not in valid_statuses:
        messages.error(request, f"Invalid status: {status}. Must be one of: {', '.join(valid_statuses)}")
        return redirect('need:need', need_id=need.id)
    
    # Update the need status
    old_status = need.status if hasattr(need, 'status') else 'pending'
    need.status = status
    need.save()
    
    messages.success(request, f"Need status updated from '{old_status}' to '{status}'.")
    
    # Redirect back to the need
    return redirect('need:need', need_id=need.id)