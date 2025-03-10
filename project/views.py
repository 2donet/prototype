from django.shortcuts import render

# Functions used to generate project related pages (remember to declare them in urls.py)

from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from project.models import Project, Connection, Membership, ProjectPermissionGroup
from comment.models import Comment
from task.models import Task
from need.models import Need
from django.urls import path, reverse
from django.db.models import Prefetch
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
import json

from skills.models import Skill

from django.contrib.auth import get_user_model
User = get_user_model()
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
    
    # Get all memberships for this project
    memberships = Membership.objects.filter(project=project).select_related('user')
    
    # Organize users by role
    admin_users = []
    moderator_users = []
    contributor_users = []
    member_users = []
    
    for membership in memberships:
        user = membership.user
        # Add date_joined field from membership to the user object
        user.date_joined = membership.date_joined
        user.membership_id = membership.id
        
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
        'project': project,
        'admin_users': admin_users,
        'moderator_users': moderator_users,
        'contributor_users': contributor_users,
        'member_users': member_users,
        'can_manage_members': can_manage_members,
        'role_choices': ProjectPermissionGroup.choices,
    }
    
    return render(request, 'members.html', context)


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
    
    # Get parent projects
    parent_connections = Connection.objects.filter(
        to_project=content, 
        type='child', 
        status='approved'
    ).select_related('from_project')
    parent_projects = [connection.from_project for connection in parent_connections]
    
    # Get project members for the member list
    memberships = Membership.objects.filter(project=content).select_related('user')
    
    # Organize users by role
    admin_users = []
    moderator_users = []
    contributor_users = []
    member_users = []
    
    for membership in memberships:
        user = membership.user
        # Add date_joined field from membership to the user object
        user.date_joined = membership.date_joined
        
        if membership.is_administrator:
            admin_users.append(user)
        elif membership.is_moderator:
            moderator_users.append(user)
        elif membership.is_contributor:
            contributor_users.append(user)
        else:
            member_users.append(user)
    
    # Check if current user is a member of this project
    is_member = False
    can_manage_members = False
    if request.user.is_authenticated:
        is_member = Membership.objects.filter(project=content, user=request.user).exists()
        
        # Check if user can manage members
        if request.user == content.created_by:
            can_manage_members = True
        else:
            user_membership = Membership.objects.filter(project=content, user=request.user).first()
            if user_membership and (user_membership.is_administrator or user_membership.is_moderator):
                can_manage_members = True

    context = {
        "content": content,
        "child_projects": child_projects,
        "parent_projects": parent_projects,
        "comments": comments,
        "tasks": tasks,
        "needs": needs,
        "admin_users": admin_users,
        "moderator_users": moderator_users,
        "contributor_users": contributor_users,
        "member_users": member_users,
        "is_member": is_member,
        "can_manage_members": can_manage_members,
    }
    return render(request, "details.html", context=context)



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



@login_required
def member_detail(request, project_id, user_id):
    """View to display and edit a specific member's role and permissions"""
    project = get_object_or_404(Project, pk=project_id)
    user = get_object_or_404(User, pk=user_id)
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
        'user_profile': user,
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
            user_to_add = User.objects.get(username=username)
            
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
    user = get_object_or_404(User, pk=user_id)
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