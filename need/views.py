from datetime import timedelta
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.db.models import Prefetch, Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden

from comment.models import Comment
from need.models import NEED_STATUSES, Need, TimeLog, NeedHistory, NeedAssignment
from task.models import Task
from project.models import Project
from utils.permissions import (
    user_can_moderate_need,
    user_has_project_permission
)
from skills.models import Skill
from user.models import User


def need(request, need_id):
    """Detailed view of a need with all related information"""
    need = get_object_or_404(
        Need.objects.select_related(
            'created_by',
            'completed_by',
            'to_project',
            'to_task',
            'to_task__to_project'
        ).prefetch_related(
            'required_skills',
            'depends_on',
            'related_needs',
            Prefetch('time_logs', queryset=TimeLog.objects.select_related('user')),
            Prefetch('assignments', queryset=NeedAssignment.objects.select_related('user', 'assigned_by')),
        ),
        pk=need_id
    )
    
    # Check visibility permissions
    if not need.user_can_view(request.user):
        return HttpResponseForbidden("You don't have permission to view this need.")
    
    # Get comments
    comments = Comment.objects.filter(
        to_need=need.id,
        parent__isnull=True
    ).select_related(
        'user', 
        'user__profile'
    ).prefetch_related(
        Prefetch(
            'replies', 
            queryset=Comment.objects.select_related('user', 'user__profile')
        ),
        'votes'
    )
    
    # Get potential volunteers based on skills
    potential_volunteers = None
    if request.user.is_authenticated and need.required_skills.exists():
        potential_volunteers = need.match_volunteers_by_skills()[:5]
    
    context = {
        'need': need,
        'comments': comments,
        'potential_volunteers': potential_volunteers,
        'time_logs': need.time_logs.all().order_by('-logged_at'),
        'assignments': need.assignments.filter(status='active'),
        'dependencies': need.depends_on.all(),
        'related_needs': need.related_needs.all(),
        'can_edit': need.user_can_edit(request.user),
        'can_assign': need.user_can_assign(request.user),
        'can_log_time': need.user_can_log_time(request.user),
    }
    return render(request, "need/details.html", context=context)


@login_required
def edit_need(request, need_id):
    """View to edit an existing need"""
    need = get_object_or_404(Need, pk=need_id)
    
    if not need.user_can_edit(request.user):
        messages.error(request, "You don't have permission to edit this need.")
        return redirect('need:need', need_id=need.id)
    
    parent = need.get_parent()
    all_skills = Skill.objects.all().order_by('name')
    
    if request.method == 'POST':
        form_data = request.POST
        
        # Update basic fields
        need.name = form_data.get('name', need.name)
        need.desc = form_data.get('desc', need.desc)
        need.priority = int(form_data.get('priority', need.priority))
        need.status = form_data.get('status', need.status)
        need.visibility = form_data.get('visibility', need.visibility)
        need.documentation_url = form_data.get('documentation_url', need.documentation_url)
        need.is_remote = form_data.get('is_remote') == 'on'
        need.is_stationary = form_data.get('is_stationary') == 'on'
        
        # Update time fields
        if form_data.get('deadline'):
            need.deadline = timezone.make_aware(
                timezone.datetime.strptime(form_data['deadline'], '%Y-%m-%d')
            )
        
        # Update resources and costs
        need.resources = form_data.get('resources', need.resources)
        if form_data.get('cost_estimate'):
            need.cost_estimate = float(form_data['cost_estimate'])
        
        # Save the changes
        need.save()
        
        # Handle skills
        skill_ids = request.POST.getlist('required_skills')
        need.required_skills.set(skill_ids)
        
        # Handle dependencies
        dependency_ids = request.POST.getlist('depends_on')
        need.depends_on.set(dependency_ids)
        
        # Handle related needs
        related_need_ids = request.POST.getlist('related_needs')
        need.related_needs.set(related_need_ids)
        
        messages.success(request, "Need updated successfully.")
        return redirect('need:need', need_id=need.id)
    
    context = {
        'need': need,
        'parent': parent,
        'all_skills': all_skills,
        'available_needs': Need.objects.exclude(pk=need_id).filter(
            Q(to_project=need.to_project) if need.to_project else Q()
        ).order_by('name'),
        'mode': 'edit',
    }
    return render(request, "need/edit_need.html", context=context)


@login_required
def create_need_for_project(request, project_id):
    """View to create a new need associated with a project"""
    project = get_object_or_404(Project, pk=project_id)
    
    if not project.user_can_contribute(request.user):
        messages.error(request, "You don't have permission to add needs to this project.")
        return redirect('project:project', project_id=project.id)
    
    if request.method == 'POST':
        form_data = request.POST
        
        # Create the need
        need = Need.objects.create(
            name=form_data['name'],
            desc=form_data.get('desc', ''),
            priority=int(form_data.get('priority', 0)),
            created_by=request.user,
            to_project=project,
            visibility=form_data.get('visibility', 'public'),
            is_remote=form_data.get('is_remote') == 'on',
            is_stationary=form_data.get('is_stationary') == 'on',
        )
        
        # Set additional fields
        if form_data.get('deadline'):
            need.deadline = timezone.make_aware(
                timezone.datetime.strptime(form_data['deadline'], '%Y-%m-%d'))
        
        if form_data.get('cost_estimate'):
            need.cost_estimate = float(form_data['cost_estimate'])
        
        need.save()
        
        # Handle skills
        skill_ids = request.POST.getlist('required_skills')
        need.required_skills.set(skill_ids)
        
        messages.success(request, f"Need '{need.name}' created successfully.")
        return redirect('project:project', project_id=project.id)
    
    context = {
        'project': project,
        'all_skills': Skill.objects.all().order_by('name'),
        'mode': 'create',
    }
    return render(request, 'need/edit_need.html', context=context)


@login_required
def log_time(request, need_id):
    """View to log time against a need"""
    need = get_object_or_404(Need, pk=need_id)
    
    if not need.user_can_log_time(request.user):
        messages.error(request, "You don't have permission to log time for this need.")
        return redirect('need:need', need_id=need.id)
    
    if request.method == 'POST':
        try:
            hours = float(request.POST.get('hours', 0))
            minutes = float(request.POST.get('minutes', 0))
            description = request.POST.get('description', '')
            
            if hours <= 0 and minutes <= 0:
                raise ValueError("Time must be greater than zero")
                
            duration = timedelta(hours=hours, minutes=minutes)
            need.log_time(duration, request.user, description)
            
            messages.success(request, f"Successfully logged {hours}h {minutes}m")
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('need:need', need_id=need.id)
    
    context = {
        'need': need,
    }
    return render(request, 'need/log_time.html', context)


@login_required
def assign_need(request, need_id):
    """View to assign a need to a user"""
    need = get_object_or_404(Need, pk=need_id)
    
    if not need.user_can_assign(request.user):
        messages.error(request, "You don't have permission to assign this need.")
        return redirect('need:need', need_id=need.id)
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        role = request.POST.get('role', 'volunteer')
        
        try:
            user = User.objects.get(pk=user_id)
            
            # Create or update assignment
            assignment, created = NeedAssignment.objects.get_or_create(
                need=need,
                user=user,
                defaults={
                    'assigned_by': request.user,
                    'role': role,
                    'status': 'active'
                }
            )
            
            if not created:
                assignment.role = role
                assignment.status = 'active'
                assignment.save()
            
            messages.success(request, f"Need assigned to {user.username}")
        except User.DoesNotExist:
            messages.error(request, "User not found")
        
        return redirect('need:need', need_id=need.id)
    
    # Get potential assignees (users with matching skills)
    potential_assignees = need.match_volunteers_by_skills()
    
    context = {
        'need': need,
        'potential_assignees': potential_assignees,
    }
    return render(request, 'need/assign.html', context)


@login_required
def update_progress(request, need_id):
    """View to update progress of a need"""
    need = get_object_or_404(Need, pk=need_id)
    
    if not need.user_can_edit(request.user):
        messages.error(request, "You don't have permission to update this need.")
        return redirect('need:need', need_id=need.id)
    
    if request.method == 'POST':
        try:
            progress = int(request.POST.get('progress', 0))
            notes = request.POST.get('notes', '')
            
            need.update_progress(progress, request.user, notes)
            
            messages.success(request, f"Progress updated to {progress}%")
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('need:need', need_id=need.id)
    
    context = {
        'need': need,
    }
    return render(request, 'need/update_progress.html', context)


@login_required
def need_history(request, need_id):
    """View showing history of changes to a need"""
    need = get_object_or_404(Need, pk=need_id)
    
    if not need.user_can_view(request.user):
        messages.error(request, "You don't have permission to view this need's history.")
        return redirect('need:need', need_id=need.id)
    
    history = NeedHistory.objects.filter(need=need).select_related('changed_by').order_by('-changed_at')
    
    context = {
        'need': need,
        'history': history,
    }
    return render(request, 'need/history.html', context)


@login_required
def delete_need(request, need_id):
    """View to delete an existing need"""
    need = get_object_or_404(Need, pk=need_id)
    parent = need.get_parent()
    
    if not (request.user == need.created_by or 
            (need.to_project and need.to_project.user_can_moderate(request.user)) or
            request.user.is_superuser):
        messages.error(request, "You don't have permission to delete this need.")
        return redirect('need:need', need_id=need.id)
    
    if request.method == 'POST':
        need_name = need.name
        need.delete()
        
        messages.success(request, f"Need '{need_name}' has been deleted.")
        
        # Redirect to appropriate parent
        if isinstance(parent, Project):
            return redirect('project:project', project_id=parent.id)
        elif isinstance(parent, Task):
            return redirect('task:task', task_id=parent.id)
        else:
            return redirect('project:index')
    
    context = {
        'need': need,
        'parent': parent,
    }
    return render(request, 'need/delete_confirm.html', context)


@login_required
def update_need_status(request, need_id, status):
    """View to update the status of a need"""
    need = get_object_or_404(Need, pk=need_id)
    
    if not need.user_can_edit(request.user):
        messages.error(request, "You don't have permission to update this need's status.")
        return redirect('need:need', need_id=need.id)
    
    valid_statuses = [s[0] for s in NEED_STATUSES]
    if status not in valid_statuses:
        messages.error(request, f"Invalid status: {status}")
        return redirect('need:need', need_id=need.id)
    
    old_status = need.status
    need.status = status
    
    # Handle completion
    if status == 'fulfilled':
        need.progress = 100
        need.completed_by = request.user
        need.completed_date = timezone.now()
    elif status == 'canceled' and need.progress == 100:
        need.progress = 0
    
    need.save()
    
    messages.success(request, f"Status updated from '{old_status}' to '{status}'")
    return redirect('need:need', need_id=need.id)


