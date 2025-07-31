from django.shortcuts import render

# Functions used to generate project related pages (remember to declare them in urls.py)

from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required,  user_passes_test
from django.db import models
from project.models import Project, Connection, Membership, ProjectPermissionGroup, Localization
from comment.models import (
    Comment, CommentReport, CommentStatus, ModerationAction, 
    ModerationDecision, DecisionScope, ReportType, ReportStatus
)
from plans.models import Plan, PlanSuggestion, PlanSuggestionStatus
from comment.utils import is_moderator, get_moderator_level

from task.models import Task
from need.models import Need
from django.urls import path, reverse
from django.db.models import Prefetch, Q, Count
from django.http import JsonResponse, Http404
from django.contrib import messages
from django.urls import reverse
from django.core.paginator import Paginator
import json
from problems.models import Problem 
from skills.models import Skill

from django.contrib.auth import get_user_model
User = get_user_model()
import logging
from django.utils import timezone
logger = logging.getLogger(__name__)


from django.contrib.contenttypes.models import ContentType


def index(request):
    """
    Display a list of the latest projects.
    """
    # Filter projects based on visibility
    if request.user.is_authenticated:
        # For logged-in users, show public projects and projects visible to logged-in users
        # FIXED: Only exclude projects that are APPROVED children (not pending/rejected)
        latest_projects_list = Project.objects.exclude(
            incoming_connections__type='child',
            incoming_connections__status='approved'  # Only exclude approved child connections
        ).filter(
                    models.Q(visibility='public') | 
                    models.Q(visibility='logged_in') |
                    models.Q(membership__user=request.user) |
                    models.Q(created_by=request.user)
                ).distinct().order_by('-id')
    else:
        # For anonymous users, only show public projects
        # FIXED: Only exclude projects that are APPROVED children (not pending/rejected)
        latest_projects_list = Project.objects.exclude(
            incoming_connections__type='child',
            incoming_connections__status='approved'  # Only exclude approved child connections
        ).filter(visibility='public').order_by('-id')

    context = {"latest_projects_list": latest_projects_list,}
    return render(request, "index.html", context=context)
@login_required
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
        project.add_member(user, 'ADMIN')
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
        
        # Handle skills with simplified approach
        skills_json = request.POST.get('skills')
        if skills_json:
            skill_names = json.loads(skills_json)
            project.add_skills(skill_names)  # Uses the helper method

        return redirect('project:project', project_id=project.id)

    return render(request, 'create_project.html')


# lsit of projects with certain skill

def skill_projects(request, skill_name):
    skill = get_object_or_404(Skill, name__iexact=skill_name)
    projects = skill.project_set.all()
    return render(request, 'skills/skill_projects.html', {'skill': skill, 'projects': projects})

@login_required
def project_members(request, project_id):
    """View to display all project members with options to manage them"""
    project = get_object_or_404(Project, pk=project_id)
    
    # Check if user has permission to view members
    if not project.visibility == 'public' and not Membership.objects.filter(
            project=project, 
            user=request.user
        ).exists() and not request.user == project.created_by:
        messages.error(request, "You don't have permission to view this project's members.")
        return redirect('project:project', project_id=project.id)
    
    # Get all memberships for this project with user profiles prefetched
    memberships = Membership.objects.filter(project=project).select_related(
        'user', 
        'user__profile'  # This is the key addition for avatar loading
    ).order_by('user__username')
    
    # Organize users by role
    admin_users = []
    moderator_users = []
    contributor_users = []
    member_users = []
    all_members = User.objects.filter(
        membership__project=project
    ).select_related('profile').order_by('username')
    
    paginator = Paginator(all_members, 15)  # Show 15 members per page
    page_number = request.GET.get('page')
    all_members = paginator.get_page(page_number)

    for membership in memberships:
        user = membership.user
        # Add membership data to the user object for template access
        user.membership_date_joined = membership.date_joined
        user.membership_id = membership.id
        user.membership_role = membership.role
        
        if membership.is_administrator:
            admin_users.append(user)
        elif membership.is_moderator:
            moderator_users.append(user)
        elif membership.is_contributor:
            contributor_users.append(user)
        else:
            member_users.append(user)
    
    # Check if current user can manage members
    can_manage_members = False
    if request.user.is_authenticated:
        if request.user == project.created_by:
            can_manage_members = True
        else:
            user_membership = Membership.objects.filter(project=project, user=request.user).first()
            if user_membership and (user_membership.is_administrator or user_membership.is_moderator):
                can_manage_members = True
    
    context = {
        'content': project,  # Added for template compatibility
        'project': project,
        'admin_users': admin_users,
        'moderator_users': moderator_users,
        'contributor_users': contributor_users,
        'member_users': member_users,
        'can_manage_members': can_manage_members,
        'role_choices': ProjectPermissionGroup.choices,
        'all_members': all_members,
        'total_members': paginator.count,
    }
    
    return render(request, 'members.html', context)


def project(request, project_id):
    # Efficiently load project with creator profile
    content = get_object_or_404(
        Project.objects.select_related(
            'created_by',
            'created_by__profile'  # Load creator's profile for avatar/bio
        ), 
        id=project_id
    )
    project = content  # Keep both for backward compatibility
    
    # Check if user has permission to view this project
    can_view = False
    
    if content.visibility == 'public':
        can_view = True
    elif content.visibility == 'logged_in' and request.user.is_authenticated:
        can_view = True
    elif content.visibility == 'restricted' and request.user.is_authenticated:
        # Check if user is a member or the creator
        if request.user == content.created_by or Membership.objects.filter(project=content, user=request.user).exists():
            can_view = True
    elif content.visibility == 'private' and request.user.is_authenticated:
        # Only the creator can view
        if request.user == content.created_by:
            can_view = True
    
    # If user doesn't have permission, show error or redirect
    if not can_view:
        if not request.user.is_authenticated:
            messages.error(request, "You need to log in to view this project.")
            return redirect('user:signin')
        else:
            messages.error(request, "You don't have permission to view this project.")
            return redirect('project:index')
    
    # Continue with the rest of the view logic
    tasks = Task.objects.filter(to_project=project_id)
    needs = Need.objects.filter(to_project=project_id).order_by('-priority', 'id')
    
    # Load comments with filtering based on user permissions
    comment_filter = Q(to_project=content.id, parent__isnull=True) & ~Q(status=CommentStatus.THREAD_DELETED) & ~Q(status=CommentStatus.REJECTED) 
    
    # Filter comments based on user role
    if can_moderate_project(request.user, content):
        # Moderators see all comments
        comment_filter = comment_filter
    else:
        # Regular users only see approved comments
        comment_filter = comment_filter & Q(status=CommentStatus.APPROVED)
    
    comments = Comment.objects.filter(comment_filter).select_related(
        'user', 
        'user__profile'  # Load comment author profiles
    ).prefetch_related(
        Prefetch(
            'replies', 
            queryset=Comment.objects.filter(
                # Also filter replies based on user permissions
                Q(status=CommentStatus.APPROVED) if not can_moderate_project(request.user, content) else Q()
            ).select_related('user', 'user__profile')
        ),
        'votes'
    )

    # Get all child projects
    child_connections = Connection.objects.filter(
        from_project=content, 
        type='child', 
        status='approved'
    ).select_related('to_project')
    child_projects = [connection.to_project for connection in child_connections]
    
    # Get parent projects
    parent_connections = Connection.objects.filter(
        to_project=content, 
        type='child', 
        status='approved'
    ).select_related('from_project')
    parent_projects = [connection.from_project for connection in parent_connections]
    
    # Get project members with profiles for avatars
    memberships = Membership.objects.filter(project=content).select_related(
        'user',
        'user__profile'  # Load member profiles for avatars
    ).order_by('user__username')
    
    # Organize users by role
    admin_users = []
    moderator_users = []
    contributor_users = []
    member_users = []
    
    for membership in memberships:
        user = membership.user
        # Add membership data to the user object
        user.membership_date_joined = membership.date_joined
        user.membership_id = membership.id
        user.membership_role = membership.role
        
        if membership.is_administrator:
            admin_users.append(user)
            member_users.append(user)
        elif membership.is_moderator:
            moderator_users.append(user)
            member_users.append(user)
        elif membership.is_contributor:
            contributor_users.append(user)
        else:
            member_users.append(user)
    
    # Check if current user is a member of this project
    is_member = False
    can_manage_members = False
    can_moderate = can_moderate_project(request.user, content)
    
    if request.user.is_authenticated:
        is_member = Membership.objects.filter(project=content, user=request.user).exists()
        
        # Check if user can manage members
        if request.user == content.created_by:
            can_manage_members = True
        else:
            user_membership = Membership.objects.filter(project=content, user=request.user).first()
            if user_membership and (user_membership.is_administrator or user_membership.is_moderator):
                can_manage_members = True

    # NEW: Get count of pending connection requests for notification
    pending_connection_requests_count = 0
    if can_moderate:
        pending_connection_requests_count = Connection.objects.filter(
            to_project=content,
            type='child',
            status='pending'
        ).count()
    project_ct = ContentType.objects.get_for_model(Project)
    task_ct = ContentType.objects.get_for_model(Task)
    need_ct = ContentType.objects.get_for_model(Need)
    project_plans = PlanSuggestion.objects.filter(
    content_type=project_ct,
    object_id=content.id,
    status=PlanSuggestionStatus.APPROVED
    ).select_related('plan', 'suggested_by', 'plan__created_by').prefetch_related('plan__steps')
    pending_plan_suggestions = []
    problems = Problem.objects.filter(
        Q(to_project=project_id) |
        Q(to_task__to_project=project_id) |
        Q(to_need__to_project=project_id)
    ).select_related(
        'created_by', 'to_task', 'to_need'
    ).prefetch_related(
        'assigned_to', 'skills'
    ).distinct()

    # Filter problems based on user permissions and add edit permissions
    filtered_problems = []
    for problem in problems:
        if problem.can_be_viewed_by(request.user):
            # Add permission check as attribute for template use
            problem.user_can_edit = problem.can_be_edited_by(request.user)
            filtered_problems.append(problem)

    # Sort by priority and creation date
    filtered_problems.sort(key=lambda x: (-x.priority, -x.created_at.timestamp()))

    # Limit to recent problems for the component (show all in dedicated page)
    recent_problems = filtered_problems[:10]  # Show only 10 most recent/important

    # Check if user can contribute to this project
    can_contribute = request.user.is_authenticated and content.user_can_contribute(request.user)
    if can_moderate:
        pending_plan_suggestions = PlanSuggestion.objects.filter(
            Q(content_type=project_ct, object_id=content.id) |
            Q(content_type=task_ct, object_id__in=content.task_set.values_list('id', flat=True)) |
            Q(content_type=need_ct, object_id__in=content.need_set.values_list('id', flat=True)),
            status=PlanSuggestionStatus.PENDING
        ).select_related('plan', 'suggested_by')[:5]  # Limit to 5 for the preview
    context = {
        "content": content,
        "child_projects": child_projects,
        "parent_projects": parent_projects,
        "comments": comments,
        "tasks": tasks,
        "needs": needs,
        "project": project,
        "admin_users": admin_users,
        "moderator_users": moderator_users,
        "contributor_users": contributor_users,
        "member_users": member_users,
        "is_member": is_member,
        "can_manage_members": can_manage_members,
        "can_moderate": can_moderate,
        "pending_connection_requests_count": pending_connection_requests_count,
        "project_plans": project_plans,
        "pending_plan_suggestions": pending_plan_suggestions,
        "problems": recent_problems,  # For the component
        "total_problems_count": len(filtered_problems),  # For display
        "can_contribute": can_contribute,  # For template permissions
    }
    return render(request, "details.html", context=context)

@login_required
def member_detail(request, project_id, user_id):
    """View to display and edit a specific member's role and permissions"""
    project = get_object_or_404(Project, pk=project_id)
    
    # Load user with profile for avatar display
    user = get_object_or_404(
        User.objects.select_related('profile'), 
        pk=user_id
    )
    
    membership = get_object_or_404(Membership, project=project, user=user)
    
    # Check if current user can manage this member
    can_manage = False
    if request.user.is_authenticated:
        if request.user == project.created_by:
            can_manage = True
        else:
            user_membership = Membership.objects.filter(project=project, user=request.user).first()
            if user_membership and user_membership.is_administrator:
                # Only admin can manage other admins
                if not (membership.is_administrator and not user_membership.is_owner):
                    can_manage = True
            # Moderators can manage regular members but not admins or other moderators
            elif user_membership and user_membership.is_moderator:
                if not (membership.is_administrator or membership.is_moderator):
                    can_manage = True
    
    if not can_manage and request.user.id != user_id:
        messages.error(request, "You don't have permission to view or edit this membership.")
        return redirect('project:project_members', project_id=project.id)
    
    if request.method == 'POST' and can_manage:
        new_role = request.POST.get('role')
        if new_role in dict(ProjectPermissionGroup.choices):
            # Update membership
            membership.role = new_role
            membership.is_administrator = new_role == 'ADMIN'
            membership.is_moderator = new_role in ['ADMIN', 'MODERATOR']
            membership.is_contributor = new_role in ['ADMIN', 'CONTRIBUTOR', 'MENTOR']
            
            # Check if trying to remove the last admin
            if membership.is_owner and not membership.is_administrator:
                messages.error(request, "The project owner must remain an administrator.")
                return redirect('project:member_detail', project_id=project.id, user_id=user.id)
                
            # Save changes
            membership.save()
            messages.success(request, f"Successfully updated {user.username}'s role to {dict(ProjectPermissionGroup.choices)[new_role]}.")
            return redirect('project:project_members', project_id=project.id)
        else:
            messages.error(request, "Invalid role selected.")
    
    context = {
        'project': project,
        'user_profile': user,  # Keep this name for template compatibility
        'user': user,          # Add this for consistency
        'membership': membership,
        'can_manage': can_manage,
        'role_choices': ProjectPermissionGroup.choices,
    }
    
    return render(request, 'member_detail.html', context)


@login_required
def add_member(request, project_id):
    """View to add a new member to the project"""
    project = get_object_or_404(Project, pk=project_id)
    
    # Check if user has permission to add members
    can_add_members = False
    if request.user.is_authenticated:
        if request.user == project.created_by:
            can_add_members = True
        else:
            user_membership = Membership.objects.filter(project=project, user=request.user).first()
            if user_membership and (user_membership.is_administrator or user_membership.is_moderator):
                can_add_members = True
    
    if not can_add_members:
        messages.error(request, "You don't have permission to add members to this project.")
        return redirect('project:project_members', project_id=project.id)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        role = request.POST.get('role', 'VIEWER')
        
        try:
            # Load user with profile for potential avatar display
            user_to_add = User.objects.select_related('profile').get(username=username)
            
            # Check if already a member
            if Membership.objects.filter(project=project, user=user_to_add).exists():
                messages.error(request, f"{username} is already a member of this project.")
                return redirect('project:add_member', project_id=project.id)
            
            # Add member with specified role
            membership = project.add_member(user_to_add, role)
            messages.success(request, f"Successfully added {username} as a {dict(ProjectPermissionGroup.choices)[role]}.")
            
            # Redirect to the member detail page for the new member
            return redirect('project:member_detail', project_id=project.id, user_id=user_to_add.id)
            
        except User.DoesNotExist:
            messages.error(request, f"User '{username}' not found.")
    
    context = {
        'project': project,
        'role_choices': ProjectPermissionGroup.choices,
    }
    
    return render(request, 'add_member.html', context)


@login_required
def remove_member(request, project_id, user_id):
    """View to remove a member from the project"""
    project = get_object_or_404(Project, pk=project_id)
    
    # Load user with profile for avatar display
    user = get_object_or_404(
        User.objects.select_related('profile'), 
        pk=user_id
    )
    
    membership = get_object_or_404(Membership, project=project, user=user)
    
    # Check if current user can remove this member
    can_remove = False
    if request.user.is_authenticated:
        # Project owner can remove anyone except themselves
        if request.user == project.created_by and request.user.id != user_id:
            can_remove = True
        # Admin can remove anyone except the owner and themselves
        elif Membership.objects.filter(project=project, user=request.user, is_administrator=True).exists():
            if not membership.is_owner and request.user.id != user_id:
                can_remove = True
        # Moderator can remove regular members
        elif Membership.objects.filter(project=project, user=request.user, is_moderator=True).exists():
            if not (membership.is_administrator or membership.is_moderator or membership.is_owner):
                can_remove = True
        # Users can remove themselves
        elif request.user.id == user_id:
            can_remove = True
    
    if not can_remove:
        messages.error(request, "You don't have permission to remove this member.")
        return redirect('project:project_members', project_id=project.id)
    
    if request.method == 'POST':
        # Prevent removing the last administrator
        if membership.is_administrator:
            admin_count = Membership.objects.filter(project=project, is_administrator=True).count()
            if admin_count <= 1:
                messages.error(request, "Cannot remove the last administrator from the project.")
                return redirect('project:project_members', project_id=project.id)
        
        # Delete the membership
        username = user.username
        membership.delete()
        
        messages.success(request, f"Successfully removed {username} from the project.")
        return redirect('project:project_members', project_id=project.id)
    
    context = {
        'project': project,
        'user_to_remove': user,
        'membership': membership,
    }
    
    return render(request, 'remove_member.html', context)

@login_required
def join_project(request, project_id):
    """View for a user to join a project"""
    project = get_object_or_404(Project, pk=project_id)
    
    # Check if user is already a member
    if Membership.objects.filter(project=project, user=request.user).exists():
        messages.info(request, "You are already a member of this project.")
        return redirect('project:project', project_id=project.id)
    
    # Check project visibility
    if project.visibility == 'private':
        messages.error(request, "This is a private project. You cannot join without an invitation.")
        return redirect('project:project', project_id=project.id)
    
    if project.visibility == 'restricted' and not request.user == project.created_by:
        messages.error(request, "This project has restricted membership. Contact an administrator for access.")
        return redirect('project:project', project_id=project.id)
    
    # Add user as a member with VIEWER role
    membership = project.add_member(request.user, 'VIEWER')
    
    messages.success(request, f"Successfully joined project '{project.name}'.")
    return redirect('project:project', project_id=project.id)

@login_required
def leave_project(request, project_id):
    """View for a user to leave a project"""
    project = get_object_or_404(Project, pk=project_id)
    
    # Check if user is a member
    try:
        membership = Membership.objects.get(project=project, user=request.user)
    except Membership.DoesNotExist:
        messages.error(request, "You are not a member of this project.")
        return redirect('project:project', project_id=project.id)
    
    # Prevent project owner from leaving
    if membership.is_owner:
        messages.error(request, "As the project owner, you cannot leave the project. You can delete it or transfer ownership instead.")
        return redirect('project:project', project_id=project.id)
    
    # Check if user is the last administrator
    if membership.is_administrator:
        admin_count = Membership.objects.filter(project=project, is_administrator=True).count()
        if admin_count <= 1:
            messages.error(request, "You are the last administrator. Please assign another administrator before leaving.")
            return redirect('project:project_members', project_id=project.id)
    
    if request.method == 'POST':
        # Remove the membership
        membership.delete()
        messages.success(request, f"You have left the project '{project.name}'.")
        return redirect('project:index')
    
    context = {
        'project': project,
    }
    
    return render(request, 'leave_project.html', context)


@login_required
def add_localization(request, project_id):
    """Add a new localization to a project"""
    project = get_object_or_404(Project, pk=project_id)
    
    # Check if user can contribute to this project
    if not project.user_can_contribute(request.user):
        messages.error(request, "You don't have permission to add localizations to this project.")
        return redirect('project:project', project_id=project.id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        # Validate the data
        if not all([name, latitude, longitude]):
            messages.error(request, "Please provide all required fields.")
            return render(request, 'add_localization.html', {'project': project})
        
        try:
            latitude = float(latitude)
            longitude = float(longitude)
            
            # Create the localization
            localization = Localization.objects.create(
                project=project,
                name=name,
                description=description,
                latitude=latitude,
                longitude=longitude
            )
            
            messages.success(request, f"Successfully added location '{name}' to the project.")
            return redirect('project:project', project_id=project.id)
            
        except ValueError:
            messages.error(request, "Invalid latitude or longitude values.")
            return render(request, 'add_localization.html', {'project': project})
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return render(request, 'add_localization.html', {'project': project})
    
    # GET request - show the form
    return render(request, 'add_localization.html', {'project': project})


@login_required
def manage_localizations(request, project_id):
    """View to manage all localizations for a project"""
    project = get_object_or_404(Project, pk=project_id)
    
    # Check if user can view this project
    can_view = False
    can_edit = False
    
    if project.visibility == 'public':
        can_view = True
    elif request.user.is_authenticated:
        if project.visibility == 'logged_in':
            can_view = True
        elif request.user == project.created_by or Membership.objects.filter(project=project, user=request.user).exists():
            can_view = True
    
    if not can_view:
        messages.error(request, "You don't have permission to view this project.")
        return redirect('project:index')
    
    # Check if user can edit localizations
    if request.user.is_authenticated:
        can_edit = project.user_can_contribute(request.user)
    
    localizations = project.localizations.all()
    
    context = {
        'project': project,
        'localizations': localizations,
        'can_edit': can_edit,
    }
    
    return render(request, 'manage_localizations.html', context)


@login_required
def delete_localization(request, project_id, localization_id):
    """Delete a localization"""
    project = get_object_or_404(Project, pk=project_id)
    localization = get_object_or_404(Localization, pk=localization_id, project=project)
    
    # Check if user can contribute to this project
    if not project.user_can_contribute(request.user):
        messages.error(request, "You don't have permission to delete localizations from this project.")
        return redirect('project:project', project_id=project.id)
    
    if request.method == 'POST':
        name = localization.name
        localization.delete()
        messages.success(request, f"Successfully deleted location '{name}'.")
    
    return redirect('project:manage_localizations', project_id=project.id)

@login_required
def edit_localization(request, project_id, localization_id):
    """Edit an existing localization"""
    project = get_object_or_404(Project, pk=project_id)
    localization = get_object_or_404(Localization, pk=localization_id, project=project)
    
    # Check if user can contribute to this project
    if not project.user_can_contribute(request.user):
        messages.error(request, "You don't have permission to edit localizations in this project.")
        return redirect('project:project', project_id=project.id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        # Validate the data
        if not all([name, latitude, longitude]):
            messages.error(request, "Please provide all required fields.")
            return render(request, 'edit_localization.html', {
                'project': project,
                'localization': localization
            })
        
        try:
            latitude = float(latitude)
            longitude = float(longitude)
            
            # Update the localization
            localization.name = name
            localization.description = description
            localization.latitude = latitude
            localization.longitude = longitude
            localization.save()
            
            messages.success(request, f"Successfully updated location '{localization.name}'.")
            return redirect('project:project', project_id=project.id)
            
        except ValueError:
            messages.error(request, "Invalid latitude or longitude values.")
            return render(request, 'edit_localization.html', {
                'project': project,
                'localization': localization
            })
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return render(request, 'edit_localization.html', {
                'project': project,
                'localization': localization
            })
    
    # GET request - show the form with existing data
    return render(request, 'edit_localization.html', {
        'project': project,
        'localization': localization
    })


def can_moderate_project(user, project):
    """Check if user can moderate this project"""
    if not user.is_authenticated:
        return False
    
    # Global moderators
    if user.is_superuser or user.is_staff or is_moderator(user):
        return True
    
    # Project-level moderators/admins
    if user == project.created_by:
        return True
    
    membership = Membership.objects.filter(project=project, user=user).first()
    if membership and (membership.is_administrator or membership.is_moderator):
        return True
    
    return False

@user_passes_test(lambda u: u.is_authenticated)
def project_moderation_dashboard(request, project_id):
    """Main project moderation dashboard"""
    project = get_object_or_404(Project, id=project_id)
    
    if not can_moderate_project(request.user, project):
        messages.error(request, "You don't have permission to moderate this project.")
        return redirect('project:project', project_id=project.id)
    
    # Get statistics
    stats = {
        'total_comments': Comment.objects.filter(to_project=project).count(),
        'pending_comments': Comment.objects.filter(to_project=project, status=CommentStatus.PENDING).count(),
        'reported_comments': CommentReport.objects.filter(
            comment__to_project=project, 
            status__in=[ReportStatus.PENDING, ReportStatus.REVIEWED]
        ).count(),
        'total_tasks': Task.objects.filter(to_project=project).count(),
        'total_needs': Need.objects.filter(to_project=project).count(),
        'total_members': Membership.objects.filter(project=project).count(),
        'total_locations': project.localizations.count(),
        'total_subprojects': Connection.objects.filter(
            from_project=project, type='child', status='approved'
        ).count(),        
        'total_plan_suggestions': PlanSuggestion.objects.filter(
            Q(content_type=ContentType.objects.get_for_model(Project), object_id=project.id) |
            Q(content_type=ContentType.objects.get_for_model(Task), object_id__in=project.task_set.values_list('id', flat=True)) |
            Q(content_type=ContentType.objects.get_for_model(Need), object_id__in=project.need_set.values_list('id', flat=True))
        ).count(),
        'pending_plan_suggestions': PlanSuggestion.objects.filter(
            Q(content_type=ContentType.objects.get_for_model(Project), object_id=project.id) |
            Q(content_type=ContentType.objects.get_for_model(Task), object_id__in=project.task_set.values_list('id', flat=True)) |
            Q(content_type=ContentType.objects.get_for_model(Need), object_id__in=project.need_set.values_list('id', flat=True)),
            status=PlanSuggestionStatus.PENDING
        ).count(),

    }
    
    context = {
        'project': project,
        'stats': stats,
    }
    
    return render(request, 'moderation/dashboard.html', context)

@user_passes_test(lambda u: u.is_authenticated)
def project_comments_moderation(request, project_id):
    """Project comments moderation page"""
    project = get_object_or_404(Project, id=project_id)
    
    if not can_moderate_project(request.user, project):
        messages.error(request, "You don't have permission to moderate this project.")
        return redirect('project:project', project_id=project.id)
    
    # Get all comments related to this project (including tasks and needs)
    comments = Comment.objects.filter(
        Q(to_project=project) |
        Q(to_task__to_project=project) |
        Q(to_need__to_project=project)
    ).select_related('user', 'user__profile').prefetch_related('reports').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        comments = comments.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(comments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'project': project,
        'comments': page_obj,
        'comment_statuses': CommentStatus.choices,
        'current_status_filter': status_filter,
    }
    
    return render(request, 'moderation/comments.html', context)

@user_passes_test(lambda u: u.is_authenticated)
def moderate_comment_action(request, project_id, comment_id):
    """Handle comment moderation actions"""
    project = get_object_or_404(Project, id=project_id)
    comment = get_object_or_404(Comment, id=comment_id)
    
    if not can_moderate_project(request.user, project):
        messages.error(request, "You don't have permission to moderate this project.")
        return redirect('project:project', project_id=project.id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        reason = request.POST.get('reason', 'No reason provided')
        
        try:
            # Create moderation action for audit trail
            moderation_action = ModerationAction.objects.create(
                moderator=request.user,
                comment=comment,
                decision=action,
                decision_scope=DecisionScope.ALL_REPORTS,
                reason=reason,
                project=project
            )
            
            # Apply the moderation action
            if action == ModerationDecision.REMOVE_CONTENT_ONLY:
                comment.remove_content_only(moderator=request.user, reason=reason)
                success_msg = "Comment content removed successfully."
                
            elif action == ModerationDecision.REMOVE_AUTHOR_ONLY:
                comment.remove_author_only(moderator=request.user, reason=reason)
                success_msg = "Comment author hidden successfully."
                
            elif action == ModerationDecision.REMOVE_AUTHOR_AND_CONTENT:
                comment.remove_author_and_content(moderator=request.user, reason=reason)
                success_msg = "Comment author and content removed successfully."
                
            elif action == ModerationDecision.DELETE_THREAD:
                comment.soft_delete_thread(moderator=request.user, reason=reason)
                success_msg = "Comment thread deleted successfully."
                
            elif action == ModerationDecision.APPROVE:
                comment.approve(moderator=request.user)
                success_msg = "Comment approved successfully."
                
            elif action == ModerationDecision.REJECT:
                comment.reject(moderator=request.user, note=reason)
                success_msg = "Comment rejected successfully."
                
            else:
                messages.error(request, "Invalid moderation action.")
                return redirect('project:comments_moderation', project_id=project.id)
            
            # Resolve related reports
            comment.reports.filter(
                status__in=[ReportStatus.PENDING, ReportStatus.REVIEWED]
            ).update(
                status=ReportStatus.RESOLVED,
                reviewed_by=request.user,
                moderator_notes=f"Resolved via project moderation: {reason}"
            )
            
            messages.success(request, success_msg)
            
        except Exception as e:
            logger.error(f"Error in comment moderation: {str(e)}")
            messages.error(request, "An error occurred while processing the moderation action.")
    
    return redirect('project:comments_moderation', project_id=project.id)

@user_passes_test(lambda u: u.is_authenticated)
def project_tasks_management(request, project_id):
    """Project tasks management page"""
    project = get_object_or_404(Project, id=project_id)
    
    if not can_moderate_project(request.user, project):
        messages.error(request, "You don't have permission to manage this project.")
        return redirect('project:project', project_id=project.id)
    
    tasks = Task.objects.filter(to_project=project).select_related('created_by').order_by('-created_at')
    
    context = {
        'project': project,
        'tasks': tasks,
    }
    
    return render(request, 'moderation/tasks.html', context)

@user_passes_test(lambda u: u.is_authenticated)
def project_needs_management(request, project_id):
    """Project needs management page"""
    project = get_object_or_404(Project, id=project_id)
    
    if not can_moderate_project(request.user, project):
        messages.error(request, "You don't have permission to manage this project.")
        return redirect('project:project', project_id=project.id)
    
    needs = Need.objects.filter(to_project=project).select_related('created_by').order_by('-created_date')    
    context = {
        'project': project,
        'needs': needs,
    }
    
    return render(request, 'moderation/needs.html', context)

@user_passes_test(lambda u: u.is_authenticated)
def project_members_management(request, project_id):
    """Project members management page"""
    project = get_object_or_404(Project, id=project_id)
    
    if not can_moderate_project(request.user, project):
        messages.error(request, "You don't have permission to manage this project.")
        return redirect('project:project', project_id=project.id)
    
    memberships = Membership.objects.filter(project=project).select_related(
        'user', 'user__profile'
    ).order_by('-date_joined')
    
    context = {
        'project': project,
        'memberships': memberships,
    }
    
    return render(request, 'moderation/members.html', context)

@user_passes_test(lambda u: u.is_authenticated)
def project_locations_management(request, project_id):
    """Project locations management page"""
    project = get_object_or_404(Project, id=project_id)
    
    if not can_moderate_project(request.user, project):
        messages.error(request, "You don't have permission to manage this project.")
        return redirect('project:project', project_id=project.id)
    
    locations = project.localizations.all().order_by('name')
    
    context = {
        'project': project,
        'locations': locations,
    }
    
    return render(request, 'moderation/locations.html', context)

@user_passes_test(lambda u: u.is_authenticated)
@user_passes_test(lambda u: u.is_authenticated)
def project_subprojects_management(request, project_id):
    """Project subprojects management page"""
    project = get_object_or_404(Project, id=project_id)
    
    if not can_moderate_project(request.user, project):
        messages.error(request, "You don't have permission to manage this project.")
        return redirect('project:project', project_id=project.id)
    
    # Get child projects (subprojects that this project manages)
    # These are projects where this project is the FROM_PROJECT (parent)
    child_connections = Connection.objects.filter(
        from_project=project, type='child'
    ).select_related('to_project', 'to_project__created_by').prefetch_related(
        'to_project__membership_set'  # Prefetch memberships for member count
    ).order_by('-added_date')

    # Get parent projects (projects that this project is a subproject of)  
    # These are projects where this project is the TO_PROJECT (child)
    parent_connections = Connection.objects.filter(
        to_project=project, type='child'
    ).select_related('from_project', 'from_project__created_by').prefetch_related(
        'from_project__membership_set'  # Prefetch memberships for member count
    ).order_by('-added_date')
    
    # FIXED: Get pending INCOMING connection requests 
    # These are requests where OTHER projects want THIS project to become their subproject
    # So this project is the TO_PROJECT (child) in pending requests
    pending_incoming_connections = Connection.objects.filter(
        to_project=project, 
        type='child', 
        status='pending'
    ).select_related(
        'from_project', 'from_project__created_by', 'added_by'
    ).prefetch_related(
        'from_project__membership_set'  # Prefetch memberships for member count
    ).order_by('-added_date')
    
    # Get pending OUTGOING connection requests 
    # These are requests where THIS project wants to become someone else's subproject
    # So this project is the TO_PROJECT (child) in these pending requests
    # OR requests where this project wants to add another project as their subproject
    # So this project is the FROM_PROJECT (parent) in these pending requests
    pending_outgoing_connections = Connection.objects.filter(
        Q(from_project=project, type='child', status='pending') |  # This project requesting to add subprojects
        Q(to_project=project, type='child', status='pending', from_project__isnull=False)  # This project requesting to join as subproject
    ).select_related('to_project', 'to_project__created_by', 'from_project', 'from_project__created_by').order_by('-added_date')
    
    # Actually, let's separate these more clearly:
    # Outgoing requests where THIS project wants to add subprojects
    outgoing_subproject_requests = Connection.objects.filter(
        from_project=project, type='child', status='pending'
    ).select_related('to_project', 'to_project__created_by').order_by('-added_date')
    
    # Outgoing requests where THIS project wants to join as a subproject  
    outgoing_parent_requests = Connection.objects.filter(
        to_project=project, type='child', status='pending'
    ).select_related('from_project', 'from_project__created_by').order_by('-added_date')
    
    context = {
        'project': project,
        'child_connections': child_connections,
        'parent_connections': parent_connections,
        'pending_incoming_connections': pending_incoming_connections,
        'pending_outgoing_connections': outgoing_subproject_requests,  # Only subproject requests
        'pending_parent_requests': outgoing_parent_requests,  # Separate parent requests
    }
    
    return render(request, 'moderation/subprojects.html', context)
@login_required
def create_subproject(request, project_id):
    """Create a new subproject linked to parent project"""
    parent_project = get_object_or_404(Project, pk=project_id)
    
    if not can_moderate_project(request.user, parent_project):
        messages.error(request, "You don't have permission to create subprojects for this project.")
        return redirect('project:project', project_id=parent_project.id)
    
    if request.method == 'POST':
        # Basic project data
        name = request.POST.get('name')
        visibility = request.POST.get('visibility', 'public')
        status = request.POST.get('status', 'planning')
        area = request.POST.get('area', '')
        tags = request.POST.get('tags', '')
        summary = request.POST.get('summary', '')
        desc = request.POST.get('desc', '')
        published = request.POST.get('published') == '1'
        
        if not name:
            messages.error(request, "Project name is required.")
            return render(request, 'subprojects/create_subproject.html', {
                'parent_project': parent_project,
                'form_data': request.POST
            })
        
        try:
            # Create the subproject
            subproject = Project.objects.create(
                name=name,
                visibility=visibility,
                collaboration_mode='volunteering',
                status=status,
                area=area,
                tags=tags,
                summary=summary,
                desc=desc,
                created_by=request.user,
                published=published,
            )
            
            # Create the connection
            connection = Connection.objects.create(
                from_project=parent_project,
                to_project=subproject,
                type='child',
                status='approved',  # Auto-approve since creator is adding it
                added_by=request.user
            )
            
            # Add creator as admin of subproject
            subproject.add_member(request.user, 'ADMIN')
            
            # Handle initial needs
            need_names = request.POST.getlist('need_name[]')
            need_descs = request.POST.getlist('need_desc[]')
            need_priorities = request.POST.getlist('need_priority[]')
            
            if need_names and need_descs and need_priorities:
                for name, desc, priority in zip(need_names, need_descs, need_priorities):
                    if name.strip():
                        Need.objects.create(
                            name=name,
                            desc=desc,
                            priority=int(priority) if priority.isdigit() else 1,
                            created_by=request.user,
                            to_project=subproject,
                        )
            
            messages.success(request, f"Subproject '{subproject.name}' created successfully!")
            return redirect('project:project', project_id=subproject.id)
            
        except Exception as e:
            logger.error(f"Error creating subproject: {str(e)}")
            messages.error(request, "An error occurred while creating the subproject.")
            return render(request, 'subprojects/create_subproject.html', {
                'parent_project': parent_project,
                'form_data': request.POST
            })
    
    # GET request
    context = {
        'parent_project': parent_project,
        'form_data': {}
    }
    return render(request, 'subprojects/create_subproject.html', context)


@login_required
def connect_existing_project(request, project_id):
    """Connect an existing project as a subproject"""
    parent_project = get_object_or_404(Project, pk=project_id)
    
    if not can_moderate_project(request.user, parent_project):
        messages.error(request, "You don't have permission to connect projects to this project.")
        return redirect('project:project', project_id=parent_project.id)
    
    if request.method == 'POST':
        target_project_id = request.POST.get('project_id')
        note = request.POST.get('note', '')
        
        try:
            target_project = Project.objects.get(pk=target_project_id)
            
            # Check if user can view the target project
            if not target_project.user_can_view(request.user):
                messages.error(request, "You don't have permission to connect to that project.")
                return redirect('project:connect_existing_project', project_id=parent_project.id)
            
            # Check if connection already exists
            if Connection.objects.filter(
                from_project=parent_project,
                to_project=target_project,
                type='child'
            ).exists():
                messages.error(request, "A connection to this project already exists.")
                return redirect('project:connect_existing_project', project_id=parent_project.id)
            
            # Create connection request
            connection = Connection.objects.create(
                from_project=parent_project,
                to_project=target_project,
                type='child',
                status='pending',  # Requires approval from target project
                added_by=request.user,
                note=note
            )
            
            messages.success(request, f"Connection request sent to '{target_project.name}'. Waiting for approval.")
            return redirect('project:subprojects_management', project_id=parent_project.id)
            
        except Project.DoesNotExist:
            messages.error(request, "Selected project not found.")
        except Exception as e:
            logger.error(f"Error creating connection: {str(e)}")
            messages.error(request, "An error occurred while creating the connection.")
    
    context = {
        'parent_project': parent_project,
    }
    return render(request, 'subprojects/connect_existing.html', context)


@login_required  
def disconnect_subproject(request, project_id, connection_id):
    """Disconnect a subproject"""
    parent_project = get_object_or_404(Project, pk=project_id)
    connection = get_object_or_404(Connection, pk=connection_id, from_project=parent_project, type='child')
    
    if not can_moderate_project(request.user, parent_project):
        messages.error(request, "You don't have permission to disconnect subprojects.")
        return redirect('project:subprojects_management', project_id=parent_project.id)
    
    if request.method == 'POST':
        subproject_name = connection.to_project.name
        connection.delete()
        messages.success(request, f"Successfully disconnected '{subproject_name}' from this project.")
    
    return redirect('project:subprojects_management', project_id=parent_project.id)


@login_required
def approve_connection(request, connection_id):
    """Approve a pending connection request"""
    connection = get_object_or_404(Connection, pk=connection_id, status='pending')
    
    # Check if user can moderate the target project (the one being connected to)
    if not can_moderate_project(request.user, connection.to_project):
        messages.error(request, "You don't have permission to approve this connection.")
        return redirect('project:project', project_id=connection.to_project.id)
    
    connection.status = 'approved'
    connection.moderated_by = request.user
    connection.moderated_date = timezone.now()
    connection.save()
    
    messages.success(request, f"Connection approved. '{connection.from_project.name}' is now connected to this project.")
    return redirect('project:subprojects_management', project_id=connection.to_project.id)


@login_required
def reject_connection(request, connection_id):
    """Reject a pending connection request"""
    connection = get_object_or_404(Connection, pk=connection_id, status='pending')
    
    # Check if user can moderate the target project
    if not can_moderate_project(request.user, connection.to_project):
        messages.error(request, "You don't have permission to reject this connection.")
        return redirect('project:project', project_id=connection.to_project.id)
    
    connection.status = 'rejected'
    connection.moderated_by = request.user
    connection.moderated_date = timezone.now()
    connection.save()
    
    messages.success(request, f"Connection rejected. '{connection.from_project.name}' will not be connected to this project.")
    return redirect('project:subprojects_management', project_id=connection.to_project.id)


# API endpoint for project search (for the connect existing project functionality)
@login_required
def api_search_projects(request):
    """API endpoint to search for projects that can be connected"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    # Search for projects the user can view
    if request.user.is_authenticated:
        projects = Project.objects.filter(
            models.Q(name__icontains=query) | models.Q(summary__icontains=query)
        ).filter(
            models.Q(visibility='public') | 
            models.Q(visibility='logged_in') |
            models.Q(membership__user=request.user) |
            models.Q(created_by=request.user)
        ).distinct().select_related('created_by')[:10]
    else:
        projects = Project.objects.filter(
            models.Q(name__icontains=query) | models.Q(summary__icontains=query),
            visibility='public'
        ).select_related('created_by')[:10]
    
    results = []
    for project in projects:
        results.append({
            'id': project.id,
            'name': project.name,
            'summary': project.summary or '',
            'created_by': project.created_by.username if project.created_by else 'Unknown'
        })
    
    return JsonResponse({'results': results})

@login_required
def request_parent_connection(request, project_id):
    """Request connection to a parent project"""
    project = get_object_or_404(Project, pk=project_id)
    
    # Check if user has permission to manage connections for this project
    if not can_moderate_project(request.user, project):
        messages.error(request, "You don't have permission to manage connections for this project.")
        return redirect('project:project', project_id=project.id)
    
    # Check if project already has a parent
    current_parent_connection = Connection.objects.filter(
        to_project=project, 
        type='child', 
        status='approved'
    ).select_related('from_project').first()
    
    # Check if there's already a pending parent request
    pending_parent_request = Connection.objects.filter(
        to_project=project, 
        type='child', 
        status='pending'
    ).select_related('from_project').first()
    
    if request.method == 'POST':
        # Only allow POST if no current parent and no pending request
        if current_parent_connection:
            messages.error(request, "This project already has a parent project. Disconnect first to request a new parent.")
            return redirect('request_parent_connection', project_id=project.id)
            
        if pending_parent_request:
            messages.error(request, "You already have a pending parent connection request. Wait for approval or cancel it first.")
            return redirect('request_parent_connection', project_id=project.id)
        
        parent_project_id = request.POST.get('parent_id')
        note = request.POST.get('note', '')
        
        try:
            parent_project = Project.objects.get(pk=parent_project_id)
            
            # Check if user can view the parent project
            if not parent_project.user_can_view(request.user):
                messages.error(request, "You don't have permission to connect to that project.")
                return redirect('project:request_parent_connection', project_id=project.id)
            
            # Prevent connecting to self
            if parent_project.id == project.id:
                messages.error(request, "A project cannot be its own parent.")
                return redirect('project:request_parent_connection', project_id=project.id)
            
            # Check if connection already exists (any status)
            if Connection.objects.filter(
                from_project=parent_project,
                to_project=project,
                type='child'
            ).exists():
                messages.error(request, "A connection to this project already exists.")
                return redirect('project:request_parent_connection', project_id=project.id)
            
            # Create connection request (parent -> child relationship)
            connection = Connection.objects.create(
                from_project=parent_project,  # Parent project
                to_project=project,           # This project (child)
                type='child',
                status='pending',
                added_by=request.user,
                note=note
            )
            
            messages.success(request, f"Parent connection request sent to '{parent_project.name}'. Waiting for approval from their administrators.")
            return redirect('project:subprojects_management', project_id=project.id)
            
        except Project.DoesNotExist:
            messages.error(request, "Selected project not found.")
        except Exception as e:
            logger.error(f"Error creating parent connection request: {str(e)}")
            messages.error(request, "An error occurred while creating the connection request.")
    
    # GET request - show the form
    context = {
        'project': project,
        'current_parent': current_parent_connection.from_project if current_parent_connection else None,
        'pending_parent_request': pending_parent_request,
    }
    return render(request, 'subprojects/request_parent.html', context)

@user_passes_test(lambda u: u.is_authenticated)
def project_plans_management(request, project_id):
    """Project plans management page"""
    project = get_object_or_404(Project, id=project_id)
    
    if not can_moderate_project(request.user, project):
        messages.error(request, "You don't have permission to manage this project.")
        return redirect('project:project', project_id=project.id)
    
    # Get content types
    project_ct = ContentType.objects.get_for_model(Project)
    task_ct = ContentType.objects.get_for_model(Task)
    need_ct = ContentType.objects.get_for_model(Need)
    
    # Get all plan suggestions for this project and its content
    all_suggestions = PlanSuggestion.objects.filter(
        models.Q(content_type=project_ct, object_id=project.id) |
        models.Q(content_type=task_ct, object_id__in=project.task_set.values_list('id', flat=True)) |
        models.Q(content_type=need_ct, object_id__in=project.need_set.values_list('id', flat=True))
    ).select_related('plan', 'suggested_by', 'reviewed_by').prefetch_related('content_object').order_by('-created_at')
    
    # Separate by status
    pending_suggestions = all_suggestions.filter(status=PlanSuggestionStatus.PENDING)
    approved_suggestions = all_suggestions.filter(status=PlanSuggestionStatus.APPROVED)
    rejected_suggestions = all_suggestions.filter(status=PlanSuggestionStatus.REJECTED)
    
    # Get statistics
    stats = {
        'total_suggestions': all_suggestions.count(),
        'pending_suggestions': pending_suggestions.count(),
        'approved_suggestions': approved_suggestions.count(),
        'rejected_suggestions': rejected_suggestions.count(),
    }
    
    context = {
        'project': project,
        'pending_suggestions': pending_suggestions,
        'approved_suggestions': approved_suggestions,
        'rejected_suggestions': rejected_suggestions,
        'stats': stats,
    }
    
    return render(request, 'moderation/plans.html', context)


@user_passes_test(lambda u: u.is_authenticated)
def moderate_plan_suggestion(request, project_id, suggestion_id):
    """Handle plan suggestion moderation actions"""
    project = get_object_or_404(Project, id=project_id)
    suggestion = get_object_or_404(PlanSuggestion, id=suggestion_id)
    
    if not can_moderate_project(request.user, project):
        messages.error(request, "You don't have permission to moderate this project.")
        return redirect('project:project', project_id=project.id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        review_note = request.POST.get('review_note', '')
        
        try:
            if action == 'approve':
                suggestion.approve(request.user, review_note)
                messages.success(request, f"Plan suggestion '{suggestion.plan.name}' approved successfully.")
                
            elif action == 'reject':
                suggestion.reject(request.user, review_note)
                messages.success(request, f"Plan suggestion '{suggestion.plan.name}' rejected.")
                
            else:
                messages.error(request, "Invalid moderation action.")
                
        except Exception as e:
            logger.error(f"Error in plan suggestion moderation: {str(e)}")
            messages.error(request, "An error occurred while processing the moderation action.")
    
    return redirect('project:plans_management', project_id=project.id)