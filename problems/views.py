# problems/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.db.models import Q, Prefetch
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import Problem, ProblemActivity
from project.models import Project
from task.models import Task
from need.models import Need
from skills.models import Skill
from comment.models import Comment, CommentStatus

User = get_user_model()

import json
import logging

logger = logging.getLogger(__name__)


def problem_list_for_project(request, project_id):
    """List all problems for a specific project"""
    project = get_object_or_404(Project, id=project_id)
    
    # Check if user can view this project
    if not project.user_can_view(request.user):
        messages.error(request, "You don't have permission to view this project.")
        return redirect('project:index')
    
    # Get all problems related to this project (directly and through tasks/needs)
    problems = Problem.objects.filter(
        Q(to_project=project) |
        Q(to_task__to_project=project) |
        Q(to_need__to_project=project)
    ).select_related(
        'created_by', 'to_project', 'to_task', 'to_need'
    ).prefetch_related(
        'assigned_to', 'skills', 'activities'
    ).distinct()
    
    # Apply filtering based on user permissions
    filtered_problems = []
    for problem in problems:
        if problem.can_be_viewed_by(request.user):
            # Add permission check as attribute for template use
            problem.user_can_edit = problem.can_be_edited_by(request.user)
            filtered_problems.append(problem)
    
    # Apply URL-based filtering
    status_filter = request.GET.get('status')
    if status_filter and status_filter != 'all':
        filtered_problems = [p for p in filtered_problems if p.status == status_filter]
    
    priority_filter = request.GET.get('priority')
    if priority_filter and priority_filter != 'all':
        filtered_problems = [p for p in filtered_problems if p.priority == int(priority_filter)]
    
    assigned_filter = request.GET.get('assigned')
    if assigned_filter == 'me' and request.user.is_authenticated:
        filtered_problems = [p for p in filtered_problems if request.user in p.assigned_to.all()]
    elif assigned_filter == 'unassigned':
        filtered_problems = [p for p in filtered_problems if not p.assigned_to.exists()]
    
    # Sorting
    sort_by = request.GET.get('sort', '-priority')
    if sort_by == 'priority':
        filtered_problems.sort(key=lambda x: x.priority, reverse=True)
    elif sort_by == '-priority':
        filtered_problems.sort(key=lambda x: x.priority, reverse=False)
    elif sort_by == 'created_at':
        filtered_problems.sort(key=lambda x: x.created_at)
    elif sort_by == '-created_at':
        filtered_problems.sort(key=lambda x: x.created_at, reverse=True)
    elif sort_by == 'name':
        filtered_problems.sort(key=lambda x: x.name.lower())
    elif sort_by == '-name':
        filtered_problems.sort(key=lambda x: x.name.lower(), reverse=True)
    
    # Check if user can create problems
    can_create = request.user.is_authenticated and project.user_can_contribute(request.user)
    
    context = {
        'project': project,
        'problems': filtered_problems,
        'can_create': can_create,
        'status_choices': Problem.STATUS_CHOICES,
        'priority_choices': Problem.PRIORITY_CHOICES,
        'current_filters': {
            'status': status_filter,
            'priority': priority_filter,
            'assigned': assigned_filter,
            'sort': sort_by,
        }
    }
    
    return render(request, 'problems/problem_list.html', context)


def problem_detail(request, problem_id):
    """View for individual problem detail"""
    problem = get_object_or_404(
        Problem.objects.select_related(
            'created_by', 'created_by__profile',
            'to_project', 'to_task', 'to_need'
        ).prefetch_related(
            'assigned_to__profile', 'skills', 'activities__user'
        ), 
        id=problem_id
    )
    
    # Check permissions
    if not problem.can_be_viewed_by(request.user):
        messages.error(request, "You don't have permission to view this problem.")
        return redirect('project:index')
    
    # Get comments with permission filtering
    comment_filter = Q(to_problem=problem, parent__isnull=True)
    comment_filter &= ~Q(status=CommentStatus.THREAD_DELETED) & ~Q(status=CommentStatus.REJECTED)
    
    # Filter comments based on user permissions
    parent_obj = problem.get_related_object()
    can_moderate = False
    if parent_obj and hasattr(parent_obj, 'user_can_moderate_comments'):
        can_moderate = parent_obj.user_can_moderate_comments(request.user)
    
    if not can_moderate:
        comment_filter &= Q(status=CommentStatus.APPROVED)
    
    comments = Comment.objects.filter(comment_filter).select_related(
        'user', 'user__profile'
    ).prefetch_related(
        Prefetch(
            'replies',
            queryset=Comment.objects.filter(
                Q(status=CommentStatus.APPROVED) if not can_moderate else Q()
            ).select_related('user', 'user__profile')
        ),
        'votes'
    )
    
    # Get recent activities
    activities = problem.activities.select_related('user').order_by('-created_at')[:10]
    
    # Check user permissions
    can_edit = problem.can_be_edited_by(request.user)
    can_comment = problem.can_be_commented_by(request.user)
    
    context = {
        'problem': problem,
        'comments': comments,
        'activities': activities,
        'can_edit': can_edit,
        'can_comment': can_comment,
        'can_moderate': can_moderate,
        'parent_object': parent_obj,
    }
    
    return render(request, 'problems/problem_detail.html', context)


@login_required
def create_problem(request):
    """Create a new problem"""
    # Get parent object from URL parameters
    to_project_id = request.GET.get('project')
    to_task_id = request.GET.get('task') 
    to_need_id = request.GET.get('need')
    
    parent_obj = None
    if to_project_id:
        parent_obj = get_object_or_404(Project, id=to_project_id)
    elif to_task_id:
        parent_obj = get_object_or_404(Task, id=to_task_id)
    elif to_need_id:
        parent_obj = get_object_or_404(Need, id=to_need_id)
    else:
        messages.error(request, "No parent object specified for the problem.")
        return redirect('project:index')
    
    # Check permissions
    can_create = False
    if hasattr(parent_obj, 'user_can_contribute'):
        can_create = parent_obj.user_can_contribute(request.user)
    elif hasattr(parent_obj, 'can_be_edited_by'):
        can_create = parent_obj.can_be_edited_by(request.user)
    
    if not can_create:
        messages.error(request, "You don't have permission to create problems for this object.")
        return redirect('project:index')
    
    if request.method == 'POST':
        try:
            # Basic problem data
            name = request.POST.get('name', '').strip()
            summary = request.POST.get('summary', '').strip()
            desc = request.POST.get('desc', '').strip()
            priority = int(request.POST.get('priority', 1))
            status = request.POST.get('status', 'open')
            visibility = request.POST.get('visibility', 'public')
            
            if not name:
                messages.error(request, "Problem name is required.")
                return render(request, 'problems/create_problem.html', {
                    'parent_obj': parent_obj,
                    'form_data': request.POST
                })
            
            # Create the problem
            problem_data = {
                'name': name,
                'summary': summary,
                'desc': desc,
                'priority': priority,
                'status': status,
                'visibility': visibility,
                'created_by': request.user,
            }
            
            # Set parent relationship
            if isinstance(parent_obj, Project):
                problem_data['to_project'] = parent_obj
            elif isinstance(parent_obj, Task):
                problem_data['to_task'] = parent_obj
            elif isinstance(parent_obj, Need):
                problem_data['to_need'] = parent_obj
            
            problem = Problem.objects.create(**problem_data)
            
            # Handle skills
            skills_json = request.POST.get('skills', '[]')
            if skills_json:
                try:
                    skill_names = json.loads(skills_json)
                    for skill_name in skill_names:
                        problem.add_skill(skill_name)
                except json.JSONDecodeError:
                    pass
            
            # Handle assignments
            assigned_users = request.POST.getlist('assigned_to')
            for user_id in assigned_users:
                try:
                    user = User.objects.get(id=user_id)
                    problem.assign_user(user)
                except User.DoesNotExist:
                    pass
            
            # Create activity log
            ProblemActivity.objects.create(
                problem=problem,
                user=request.user,
                activity_type='created',
                desc=f"Problem '{problem.name}' was created"
            )
            
            messages.success(request, f"Problem '{problem.name}' created successfully!")
            return redirect('problems:detail', problem_id=problem.id)
            
        except Exception as e:
            logger.error(f"Error creating problem: {str(e)}")
            messages.error(request, "An error occurred while creating the problem.")
            return render(request, 'problems/create_problem.html', {
                'parent_obj': parent_obj,
                'form_data': request.POST
            })
    
    # GET request
    context = {
        'parent_obj': parent_obj,
        'status_choices': Problem.STATUS_CHOICES,
        'priority_choices': Problem.PRIORITY_CHOICES,
        'visibility_choices': Problem.VISIBILITY_CHOICES,
    }
    
    return render(request, 'problems/create_problem.html', context)


@login_required
def edit_problem(request, problem_id):
    """Edit an existing problem"""
    problem = get_object_or_404(Problem, id=problem_id)
    
    # Check permissions
    if not problem.can_be_edited_by(request.user):
        messages.error(request, "You don't have permission to edit this problem.")
        return redirect('problems:detail', problem_id=problem.id)
    
    if request.method == 'POST':
        try:
            # Store original values for activity logging
            original_name = problem.name
            original_status = problem.status
            original_priority = problem.priority
            
            # Update basic fields
            problem.name = request.POST.get('name', '').strip()
            problem.summary = request.POST.get('summary', '').strip()
            problem.desc = request.POST.get('desc', '').strip()
            problem.priority = int(request.POST.get('priority', 1))
            problem.status = request.POST.get('status', 'open')
            problem.visibility = request.POST.get('visibility', 'public')
            
            # Handle due date
            due_date_str = request.POST.get('due_date')
            if due_date_str:
                try:
                    problem.due_date = timezone.datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                except ValueError:
                    pass
            else:
                problem.due_date = None
                
            # Handle resolution
            if problem.status == 'solved':
                if not problem.resolved_at:
                    problem.resolved_at = timezone.now()
                problem.resolution = request.POST.get('resolution', '')
            else:
                problem.resolved_at = None
                problem.resolution = ''
            
            problem.save()
            
            # Log status change
            if original_status != problem.status:
                ProblemActivity.objects.create(
                    problem=problem,
                    user=request.user,
                    activity_type='status_changed',
                    desc=f"Status changed from '{original_status}' to '{problem.status}'"
                )
            
            # Log priority change
            if original_priority != problem.priority:
                ProblemActivity.objects.create(
                    problem=problem,
                    user=request.user,
                    activity_type='priority_changed',
                    desc=f"Priority changed from {original_priority} to {problem.priority}"
                )
            
            messages.success(request, "Problem updated successfully!")
            return redirect('problems:detail', problem_id=problem.id)
            
        except Exception as e:
            logger.error(f"Error updating problem: {str(e)}")
            messages.error(request, "An error occurred while updating the problem.")
    
    context = {
        'problem': problem,
        'status_choices': Problem.STATUS_CHOICES,
        'priority_choices': Problem.PRIORITY_CHOICES,
        'visibility_choices': Problem.VISIBILITY_CHOICES,
    }
    
    return render(request, 'problems/edit_problem.html', context)


@login_required
def assign_user(request, problem_id):
    """Assign a user to a problem"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    problem = get_object_or_404(Problem, id=problem_id)
    
    # Check permissions
    if not problem.can_be_edited_by(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        user_id = request.POST.get('user_id')
        user_to_assign = get_object_or_404(User, id=user_id)
        
        # Check if already assigned
        if user_to_assign in problem.assigned_to.all():
            return JsonResponse({'error': 'User already assigned'}, status=400)
        
        problem.assign_user(user_to_assign)
        
        return JsonResponse({
            'success': True,
            'message': f'{user_to_assign.username} assigned successfully',
            'assigned_users': [
                {'id': u.id, 'username': u.username} 
                for u in problem.assigned_to.all()
            ]
        })
        
    except Exception as e:
        logger.error(f"Error assigning user: {str(e)}")
        return JsonResponse({'error': 'An error occurred'}, status=500)


@login_required
def unassign_user(request, problem_id):
    """Unassign a user from a problem"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    problem = get_object_or_404(Problem, id=problem_id)
    
    # Check permissions
    if not problem.can_be_edited_by(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        user_id = request.POST.get('user_id')
        user_to_unassign = get_object_or_404(User, id=user_id)
        
        # Check if actually assigned
        if user_to_unassign not in problem.assigned_to.all():
            return JsonResponse({'error': 'User not assigned'}, status=400)
        
        problem.unassign_user(user_to_unassign)
        
        return JsonResponse({
            'success': True,
            'message': f'{user_to_unassign.username} unassigned successfully',
            'assigned_users': [
                {'id': u.id, 'username': u.username} 
                for u in problem.assigned_to.all()
            ]
        })
        
    except Exception as e:
        logger.error(f"Error unassigning user: {str(e)}")
        return JsonResponse({'error': 'An error occurred'}, status=500)