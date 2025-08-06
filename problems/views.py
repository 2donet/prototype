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
from .forms import ProblemForm
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
    comment_filter = Q(to_problem=problem) & Q(parent__isnull=True)
    comment_filter &= ~Q(status=CommentStatus.THREAD_DELETED) & ~Q(status=CommentStatus.REJECTED)
    comment_filter &= Q(to_task__isnull=True) & Q(to_project__isnull=True) & Q(to_need__isnull=True) 
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
                Q(status=CommentStatus.APPROVED))
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
        form = ProblemForm(request.POST, parent_object=parent_obj, user=request.user)
        
        if form.is_valid():
            try:
                problem = form.save()
                
                # Handle skills from JavaScript chips - similar to need system
                skill_names = request.POST.getlist('skills[]')
                form.save_skills(skill_names)  # This will clear if empty list
                
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
                messages.error(request, f"Error creating problem: {str(e)}")
        else:
            # Form has validation errors
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProblemForm(parent_object=parent_obj, user=request.user)
    
    context = {
        'form': form,
        'parent_obj': parent_obj,
        'status_choices': Problem.STATUS_CHOICES,
        'priority_choices': Problem.PRIORITY_CHOICES,
        'visibility_choices': Problem.VISIBILITY_CHOICES,
        'all_skills': Skill.objects.all().order_by('name'),
        'mode': 'create',
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
        form = ProblemForm(
            request.POST, 
            instance=problem, 
            parent_object=problem.get_related_object(), 
            user=request.user
        )
        
        if form.is_valid():
            try:
                # Store original values for activity logging
                original_status = problem.status
                original_priority = problem.priority
                
                problem = form.save()
                
                # Handle skills from JavaScript chips - similar to need system
                skill_names = request.POST.getlist('skills[]')
                form.save_skills(skill_names)  # This will clear if empty list
                
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
                messages.error(request, f"Error updating problem: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProblemForm(
            instance=problem, 
            parent_object=problem.get_related_object(), 
            user=request.user
        )
    
    context = {
        'form': form,
        'problem': problem,
        'status_choices': Problem.STATUS_CHOICES,
        'priority_choices': Problem.PRIORITY_CHOICES,
        'visibility_choices': Problem.VISIBILITY_CHOICES,
        'all_skills': Skill.objects.all().order_by('name'),
        'mode': 'edit',
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


def users_search_api(request):
    """API endpoint for searching users to assign to problems"""
    try:
        query = request.GET.get('q', '').strip()
        project_id = request.GET.get('project_id')
        
        if not query or len(query) < 2:
            return JsonResponse({'results': []})
        
        # Base user query
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).filter(is_active=True)
        
        # Prioritize project members if project_id is provided
        if project_id:
            try:
                project = Project.objects.get(id=project_id)
                project_members = users.filter(membership__project=project)
                non_members = users.exclude(membership__project=project)
                # Combine with project members first
                users = list(project_members) + list(non_members)
            except Project.DoesNotExist:
                users = list(users[:20])
        else:
            users = list(users[:20])
        
        results = []
        for user in users:
            results.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.get_full_name() or user.username,
                'avatar_url': user.profile.avatar_small.url if hasattr(user, 'profile') and user.profile.avatar else '/static/images/default-avatar.png'
            })
        
        return JsonResponse({'results': results})
        
    except Exception as e:
        logger.error(f"Error in user search API: {str(e)}")
        return JsonResponse({'results': [], 'error': str(e)})