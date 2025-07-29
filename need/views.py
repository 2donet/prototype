from datetime import timedelta
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.db.models import Prefetch, Q, Count, Case, When, IntegerField, CharField, Value
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.humanize.templatetags.humanize import naturaltime, naturalday
import json

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


def need_list(request):
    """Enhanced need listing page with filtering, searching, and sorting"""
    # Get base queryset with optimizations
    needs = Need.objects.select_related(
        'created_by',
        'completed_by', 
        'to_project',
        'to_task'
    ).prefetch_related(
        'required_skills',
        'assignments'
    ).filter(is_current=True)
    
    # Apply visibility filtering based on user
    if not request.user.is_authenticated:
        needs = needs.filter(visibility='public')
    elif not request.user.is_superuser:
        # Filter based on visibility and user permissions
        needs = needs.filter(
            Q(visibility='public') |
            Q(visibility='members', to_project__members=request.user) |
            Q(visibility='admins', to_project__admins=request.user) |
            Q(created_by=request.user)
        ).distinct()
    
    # Get filter options for the template
    projects = Project.objects.filter(
        all_needs__in=needs
    ).distinct().order_by('name')
    
    # Add priority and status classes for templates
    needs = needs.annotate(
        priority_class=Case(
            When(priority__gte=75, then=Value('priority-critical')),
            When(priority__gte=50, then=Value('priority-high')),
            When(priority__gte=25, then=Value('priority-medium')),
            default=Value('priority-low'),
            output_field=CharField()
        ),
        status_class=Case(
            When(status='pending', then=Value('status-pending')),
            When(status='in_progress', then=Value('status-progress')),
            When(status='fulfilled', then=Value('status-complete')),
            When(status='canceled', then=Value('status-canceled')),
            default=Value('status-pending'),
            output_field=CharField()
        )
    )
    
    # Pagination
    paginator = Paginator(needs, 12)  # 12 needs per page
    page_number = request.GET.get('page')
    needs_page = paginator.get_page(page_number)
    
    context = {
        'needs': needs_page,
        'total_needs': needs.count(),
        'projects': projects,
        'all_skills': Skill.objects.all().order_by('name'),
    }
    
    return render(request, 'need/need_list.html', context)


def project_needs(request, project_id):
    """View showing all needs for a specific project"""
    project = get_object_or_404(
        Project.objects.prefetch_related('skills'),
        pk=project_id
    )
    
    # Check if user can view this project
    if not project.user_can_view(request.user):
        return HttpResponseForbidden("You don't have permission to view this project's needs.")
    
    # Get needs for this project
    needs = Need.objects.filter(
        to_project=project,
        is_current=True
    ).select_related(
        'created_by',
        'completed_by'
    ).prefetch_related(
        'required_skills',
        'assignments'
    ).annotate(
        priority_class=Case(
            When(priority__gte=75, then=Value('priority-critical')),
            When(priority__gte=50, then=Value('priority-high')),
            When(priority__gte=25, then=Value('priority-medium')),
            default=Value('priority-low'),
            output_field=CharField()
        ),
        status_class=Case(
            When(status='pending', then=Value('status-pending')),
            When(status='in_progress', then=Value('status-progress')),
            When(status='fulfilled', then=Value('status-complete')),
            When(status='canceled', then=Value('status-canceled')),
            default=Value('status-pending'),
            output_field=CharField()
        )
    )
    
    # Apply visibility filtering
    if not request.user.is_authenticated:
        needs = needs.filter(visibility='public')
    elif not request.user.is_superuser and not project.user_can_moderate(request.user):
        needs = needs.filter(
            Q(visibility='public') |
            Q(visibility='members') |
            Q(created_by=request.user)
        )
    
    # Calculate statistics
    stats = {
        'total_needs': needs.count(),
        'fulfilled_needs': needs.filter(status='fulfilled').count(),
        'in_progress_needs': needs.filter(status='in_progress').count(),
        'pending_needs': needs.filter(status='pending').count(),
    }
    
    # Pagination
    paginator = Paginator(needs, 12)
    page_number = request.GET.get('page')
    needs_page = paginator.get_page(page_number)
    
    context = {
        'project': project,
        'needs': needs_page,
        'stats': stats,
        'all_skills': Skill.objects.all().order_by('name'),
    }
    
    return render(request, 'need/project_needs.html', context)


def skill_needs(request, skill_name):
    """View showing all needs that require a specific skill"""
    skill = get_object_or_404(Skill, name__iexact=skill_name)
    
    # Get needs that require this skill
    needs = Need.objects.filter(
        required_skills=skill,
        is_current=True
    ).select_related(
        'created_by',
        'completed_by',
        'to_project'
    ).prefetch_related(
        'required_skills',
        'assignments'
    ).annotate(
        priority_class=Case(
            When(priority__gte=75, then=Value('priority-critical')),
            When(priority__gte=50, then=Value('priority-high')),
            When(priority__gte=25, then=Value('priority-medium')),
            default=Value('priority-low'),
            output_field=CharField()
        ),
        status_class=Case(
            When(status='pending', then=Value('status-pending')),
            When(status='in_progress', then=Value('status-progress')),
            When(status='fulfilled', then=Value('status-complete')),
            When(status='canceled', then=Value('status-canceled')),
            default=Value('status-pending'),
            output_field=CharField()
        )
    )
    
    # Apply visibility filtering
    if not request.user.is_authenticated:
        needs = needs.filter(visibility='public')
    elif not request.user.is_superuser:
        needs = needs.filter(
            Q(visibility='public') |
            Q(visibility='members', to_project__members=request.user) |
            Q(visibility='admins', to_project__admins=request.user) |
            Q(created_by=request.user)
        ).distinct()
    
    # Calculate statistics
    stats = {
        'total_needs': needs.count(),
        'fulfilled_needs': needs.filter(status='fulfilled').count(),
        'in_progress_needs': needs.filter(status='in_progress').count(),
        'pending_needs': needs.filter(status='pending').count(),
    }
    
    # Get projects that have needs with this skill
    projects = Project.objects.filter(
        all_needs__in=needs
    ).distinct().order_by('name')
    
    # Get related skills (skills that appear together with this skill in needs)
    related_skills = Skill.objects.filter(
        need__required_skills=skill
    ).exclude(
        id=skill.id
    ).annotate(
        need_count=Count('need', distinct=True)
    ).order_by('-need_count')[:10]
    
    # Pagination
    paginator = Paginator(needs, 12)
    page_number = request.GET.get('page')
    needs_page = paginator.get_page(page_number)
    
    context = {
        'skill': skill,
        'needs': needs_page,
        'stats': stats,
        'projects': projects,
        'related_skills': related_skills,
    }
    
    return render(request, 'need/skill_needs.html', context)


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
    # Commenting out until User-Skills relationship is established
    # if request.user.is_authenticated and need.required_skills.exists():
    #     potential_volunteers = need.match_volunteers_by_skills()[:5]
    
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
        try:
            form_data = request.POST
            
            # Update basic fields
            need.name = form_data.get('name', need.name).strip()
            need.desc = form_data.get('desc', need.desc)
            need.priority = int(form_data.get('priority', need.priority))
            need.status = form_data.get('status', need.status)
            need.visibility = form_data.get('visibility', need.visibility)
            need.documentation_url = form_data.get('documentation_url', '') or None
            need.is_remote = form_data.get('is_remote') == 'on'
            need.is_stationary = form_data.get('is_stationary') == 'on'
            need.skill_level = form_data.get('skill_level', '') or None
            need.resources = form_data.get('resources', '') or None
            need.completion_notes = form_data.get('completion_notes', '') or None
            
            # Handle progress
            if form_data.get('progress'):
                progress = int(form_data.get('progress', need.progress))
                need.update_progress(progress, request.user, need.completion_notes)
            
            # Handle deadline
            if form_data.get('deadline'):
                try:
                    need.deadline = timezone.datetime.fromisoformat(form_data['deadline'].replace('T', ' '))
                    if timezone.is_naive(need.deadline):
                        need.deadline = timezone.make_aware(need.deadline)
                except ValueError:
                    need.deadline = None
            else:
                need.deadline = None
            
            # Handle estimated time
            if form_data.get('estimated_time_hours'):
                try:
                    hours = float(form_data.get('estimated_time_hours'))
                    need.estimated_time = timedelta(hours=hours)
                except ValueError:
                    need.estimated_time = None
            else:
                need.estimated_time = None
            
            # Handle cost estimate
            if form_data.get('cost_estimate'):
                try:
                    need.cost_estimate = float(form_data['cost_estimate'])
                except ValueError:
                    need.cost_estimate = None
            else:
                need.cost_estimate = None
            
            # Save the changes
            need.save()
            
            # Handle skills
            skill_names = request.POST.getlist('required_skills[]')
            if skill_names:
                skills = []
                for skill_name in skill_names:
                    skill_name = skill_name.strip()
                    if skill_name:
                        skill = Skill.get_or_create_skill(skill_name)
                        skills.append(skill)
                need.required_skills.set(skills)
            else:
                need.required_skills.clear()
            
            # Handle dependencies (by names)
            dependency_names = request.POST.getlist('depends_on[]')
            if dependency_names:
                dependencies = Need.objects.filter(
                    name__in=dependency_names,
                    to_project=need.to_project
                ).exclude(pk=need.pk)
                need.depends_on.set(dependencies)
            else:
                need.depends_on.clear()
            
            # Handle related needs (by names)
            related_names = request.POST.getlist('related_needs[]')
            if related_names:
                related_needs = Need.objects.filter(
                    name__in=related_names,
                    to_project=need.to_project
                ).exclude(pk=need.pk)
                need.related_needs.set(related_needs)
            else:
                need.related_needs.clear()
            
            messages.success(request, "Need updated successfully.")
            return redirect('need:need', need_id=need.id)
            
        except Exception as e:
            messages.error(request, f"Error updating need: {str(e)}")
    
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
        try:
            form_data = request.POST
            
            # Create the need with basic fields
            need = Need.objects.create(
                name=form_data['name'].strip(),
                desc=form_data.get('desc', ''),
                priority=int(form_data.get('priority', 0)),
                created_by=request.user,
                to_project=project,
                visibility=form_data.get('visibility', 'public'),
                is_remote=form_data.get('is_remote') == 'on',
                is_stationary=form_data.get('is_stationary') == 'on',
                skill_level=form_data.get('skill_level', '') or None,
                resources=form_data.get('resources', '') or None,
                documentation_url=form_data.get('documentation_url', '') or None,
            )
            
            # Handle deadline
            if form_data.get('deadline'):
                try:
                    need.deadline = timezone.datetime.fromisoformat(form_data['deadline'].replace('T', ' '))
                    if timezone.is_naive(need.deadline):
                        need.deadline = timezone.make_aware(need.deadline)
                except ValueError:
                    pass
            
            # Handle estimated time
            if form_data.get('estimated_time_hours'):
                try:
                    hours = float(form_data.get('estimated_time_hours'))
                    need.estimated_time = timedelta(hours=hours)
                except ValueError:
                    pass
            
            # Handle cost estimate
            if form_data.get('cost_estimate'):
                try:
                    need.cost_estimate = float(form_data['cost_estimate'])
                except ValueError:
                    pass
            
            need.save()
            
            # Handle skills
            skill_names = request.POST.getlist('required_skills[]')
            if skill_names:
                skills = []
                for skill_name in skill_names:
                    skill_name = skill_name.strip()
                    if skill_name:
                        skill = Skill.get_or_create_skill(skill_name)
                        skills.append(skill)
                need.required_skills.set(skills)
            
            messages.success(request, f"Need '{need.name}' created successfully.")
            return redirect('project:project', project_id=project.id)
            
        except Exception as e:
            messages.error(request, f"Error creating need: {str(e)}")
    
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
            
            # Create time log with description
            TimeLog.objects.create(
                need=need,
                user=request.user,
                duration=duration,
                description=description
            )
            
            # Update need's actual time
            need.actual_time = (need.actual_time or timedelta()) + duration
            need.save()
            
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
    # Commenting out until User-Skills relationship is established
    # potential_assignees = need.match_volunteers_by_skills()
    potential_assignees = User.objects.filter(is_active=True).order_by('username')[:10]
    
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
            return redirect('need:need_list')
    
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


# API ENDPOINTS FOR AJAX FUNCTIONALITY

def skills_autocomplete_api(request):
    """API endpoint for skills autocomplete"""
    try:
        skills = Skill.objects.all().order_by('name')
        skills_data = [{'id': skill.id, 'name': skill.name} for skill in skills]
        
        return JsonResponse({
            'success': True,
            'skills': skills_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def need_search_api(request):
    """API endpoint for searching and filtering needs"""
    try:
        # Get query parameters
        search_query = request.GET.get('search', '').strip()
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 24))
        
        # Parse filter parameters
        projects = request.GET.get('projects', '').split(',') if request.GET.get('projects') else []
        skills = request.GET.get('skills', '').split(',') if request.GET.get('skills') else []
        statuses = request.GET.get('statuses', '').split(',') if request.GET.get('statuses') else []
        priorities = request.GET.get('priorities', '').split(',') if request.GET.get('priorities') else []
        work_types = request.GET.get('work_types', '').split(',') if request.GET.get('work_types') else []
        
        skill_logic = request.GET.get('skill_logic', 'any')
        created_after = request.GET.get('created_after', '')
        deadline_before = request.GET.get('deadline_before', '')
        sort_by = request.GET.get('sort', '-created_date')
        
        # Remove empty strings from lists
        projects = [p for p in projects if p]
        skills = [s for s in skills if s]
        statuses = [s for s in statuses if s]
        priorities = [p for p in priorities if p]
        work_types = [w for w in work_types if w]
        
        # Base queryset
        needs = Need.objects.select_related(
            'created_by', 'to_project'
        ).prefetch_related(
            'required_skills'
        ).filter(is_current=True)
        
        # Apply search
        if search_query:
            needs = needs.filter(
                Q(name__icontains=search_query) |
                Q(desc__icontains=search_query) |
                Q(required_skills__name__icontains=search_query)
            ).distinct()
        
        # Apply status filters
        if statuses:
            needs = needs.filter(status__in=statuses)
        
        # Apply priority filters
        if priorities:
            priority_conditions = Q()
            for priority_range in priorities:
                if priority_range == 'high':
                    priority_conditions |= Q(priority__gte=75)
                elif priority_range == 'medium':
                    priority_conditions |= Q(priority__gte=50, priority__lt=75)
                elif priority_range == 'low':
                    priority_conditions |= Q(priority__gte=25, priority__lt=50)
                elif priority_range == 'minimal':
                    priority_conditions |= Q(priority__lt=25)
            if priority_conditions:
                needs = needs.filter(priority_conditions)
        
        # Apply project filters
        if projects:
            needs = needs.filter(to_project__id__in=projects)
        
        # Apply skill filters
        if skills:
            if skill_logic == 'all':
                # Need must have ALL selected skills
                for skill_name in skills:
                    needs = needs.filter(required_skills__name__iexact=skill_name)
            else:
                # Need must have ANY of the selected skills
                needs = needs.filter(required_skills__name__in=skills).distinct()
        
        # Apply work type filters
        if work_types and 'all' not in work_types:
            work_conditions = Q()
            if 'remote' in work_types:
                work_conditions |= Q(is_remote=True)
            if 'stationary' in work_types:
                work_conditions |= Q(is_stationary=True)
            if work_conditions:
                needs = needs.filter(work_conditions)
        
        # Apply date filters
        if created_after:
            try:
                created_date = timezone.datetime.strptime(created_after, '%Y-%m-%d').date()
                needs = needs.filter(created_date__date__gte=created_date)
            except ValueError:
                pass
        
        if deadline_before:
            try:
                deadline_date = timezone.datetime.strptime(deadline_before, '%Y-%m-%d').date()
                needs = needs.filter(deadline__date__lte=deadline_date)
            except ValueError:
                pass
        
        # Apply visibility filters
        if not request.user.is_authenticated:
            needs = needs.filter(visibility='public')
        elif not request.user.is_superuser:
            needs = needs.filter(
                Q(visibility='public') |
                Q(visibility='members', to_project__members=request.user) |
                Q(visibility='admins', to_project__admins=request.user) |
                Q(created_by=request.user)
            ).distinct()
        
        # Get total count before pagination
        total_count = Need.objects.filter(is_current=True).count()
        filtered_count = needs.count()
        
        # Apply sorting
        valid_sorts = [
            'name', '-name', 'created_date', '-created_date',
            'priority', '-priority', 'deadline', '-deadline', 'status'
        ]
        if sort_by in valid_sorts:
            needs = needs.order_by(sort_by)
        
        # Pagination
        paginator = Paginator(needs, per_page)
        needs_page = paginator.get_page(page)
        
        # Serialize results
        results = []
        for need in needs_page:
            # Calculate display values
            is_overdue = need.deadline and need.deadline < timezone.now()
            
            priority_class = (
                'priority-critical' if need.priority >= 75 else
                'priority-high' if need.priority >= 50 else
                'priority-medium' if need.priority >= 25 else
                'priority-low'
            )
            
            status_class = {
                'pending': 'status-pending',
                'in_progress': 'status-progress', 
                'fulfilled': 'status-complete',
                'canceled': 'status-canceled'
            }.get(need.status, 'status-pending')
            
            results.append({
                'id': need.id,
                'name': need.name,
                'description': need.desc,
                'priority': need.priority,
                'priority_class': priority_class,
                'status': need.status,
                'status_display': need.get_status_display(),
                'status_class': status_class,
                'progress': need.progress,
                'is_overdue': is_overdue,
                'created_by': {
                    'id': need.created_by.id,
                    'username': need.created_by.username,
                } if need.created_by else None,
                'created_date': need.created_date.isoformat(),
                'created_date_display': naturaltime(need.created_date),
                'deadline': need.deadline.isoformat() if need.deadline else None,
                'deadline_display': naturalday(need.deadline) if need.deadline else None,
                'project': {
                    'id': need.to_project.id,
                    'name': need.to_project.name,
                } if need.to_project else None,
                'required_skills': [
                    {'id': skill.id, 'name': skill.name}
                    for skill in need.required_skills.all()
                ],
                'cost_estimate': float(need.cost_estimate) if need.cost_estimate else None,
                'is_remote': need.is_remote,
                'is_stationary': need.is_stationary,
                'can_edit': need.user_can_edit(request.user),
                'url': reverse('need:need', args=[need.id]),
            })
        
        return JsonResponse({
            'success': True,
            'needs': results,
            'has_next': needs_page.has_next(),
            'has_previous': needs_page.has_previous(),
            'current_page': needs_page.number,
            'total_pages': paginator.num_pages,
            'total_count': total_count,
            'filtered_count': filtered_count,
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def quick_update_need_api(request, need_id):
    """API endpoint for quick need updates"""
    try:
        need = get_object_or_404(Need, pk=need_id)
        
        if not need.user_can_edit(request.user):
            return JsonResponse({
                'success': False,
                'error': 'Permission denied'
            }, status=403)
        
        data = json.loads(request.body)
        field = data.get('field')
        value = data.get('value')
        
        if field == 'status':
            valid_statuses = [s[0] for s in NEED_STATUSES]
            if value not in valid_statuses:
                return JsonResponse({
                    'success': False,
                    'error': f'Invalid status: {value}'
                }, status=400)
            
            old_status = need.status
            need.status = value
            
            if value == 'fulfilled':
                need.progress = 100
                need.completed_by = request.user
                need.completed_date = timezone.now()
            elif value == 'canceled' and need.progress == 100:
                need.progress = 0
            
            need.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Status updated from "{old_status}" to "{value}"'
            })
        
        elif field == 'progress':
            try:
                progress = int(value)
                if not 0 <= progress <= 100:
                    raise ValueError("Progress must be between 0 and 100")
                
                need.update_progress(progress, request.user)
                
                return JsonResponse({
                    'success': True,
                    'message': f'Progress updated to {progress}%'
                })
            except ValueError as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=400)
        
        else:
            return JsonResponse({
                'success': False,
                'error': f'Invalid field: {field}'
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)