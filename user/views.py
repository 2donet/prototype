# views.py

from django.shortcuts import get_object_or_404, render, redirect
from django.urls import path, reverse
from django.db.models import Prefetch, Count, Q
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from comment.models import Comment, CommentStatus
from decisions.models import Decision
from user.models import Membership, UserProfile, Post
from project.models import Project, Membership as ProjectMembership
from task.models import Task
from need.models import Need
from django.contrib.auth.decorators import login_required
from user.models import Person
from django.core.paginator import Paginator

from .forms import SignInForm, SignupForm, EditProfileForm
from django.contrib.auth import get_user_model
import os

def userprofile(request, user_id):
    User = get_user_model()
    user = get_object_or_404(User, pk=user_id)
    user_profile = getattr(user, 'profile', None)
    
    # Create profile if it doesn't exist
    if user_profile is None:
        user_profile, created = UserProfile.objects.get_or_create(user=user)
    
    # Get user's posts
    posts = Post.objects.filter(author=user_id).order_by('-date')
    
    # ==== PROJECTS DATA ====
    # Get projects user created
    created_projects = Project.objects.filter(created_by=user).select_related(
        'created_by'
    ).prefetch_related(
        'skills',
        'membership_set',
        'task_set',
    ).annotate(
        member_count=Count('membership', distinct=True),
        task_count=Count('task', distinct=True),
        comment_count=Count('comments', distinct=True)
    )
    
    # Get projects user is a member of (but didn't create)
    member_projects = Project.objects.filter(
        membership__user=user
    ).exclude(
        created_by=user
    ).select_related(
        'created_by'
    ).prefetch_related(
        'skills',
        'membership_set',
        'task_set',
        Prefetch(
            'membership_set',
            queryset=ProjectMembership.objects.filter(user=user),
            to_attr='user_membership'
        )
    ).annotate(
        member_count=Count('membership', distinct=True),
        task_count=Count('task', distinct=True),
        comment_count=Count('comments', distinct=True)
    )
    
    # Combine and organize projects
    all_user_projects = []
    
    # Add created projects with role
    for project in created_projects:
        project.user_role = "Project Creator"
        project.user_role_type = "creator"
        all_user_projects.append(project)
    
    # Add member projects with actual role
    for project in member_projects:
        if hasattr(project, 'user_membership') and project.user_membership:
            membership = project.user_membership[0]
            project.user_role = membership.get_role_display()
            project.user_role_type = membership.role.lower()
        else:
            # Fallback if membership not found
            membership = ProjectMembership.objects.filter(project=project, user=user).first()
            if membership:
                project.user_role = membership.get_role_display()
                project.user_role_type = membership.role.lower()
            else:
                project.user_role = "Member"
                project.user_role_type = "member"
        all_user_projects.append(project)
    
    # Sort projects by most recent
    all_user_projects.sort(key=lambda x: x.id, reverse=True)
    
    # ==== COMMENTS DATA ====
    # Get user's approved comments with context
    user_comments = Comment.objects.filter(
        user=user,
        status=CommentStatus.APPROVED  # Only show approved comments
    ).select_related(
        'user',
        'to_project',
        'to_task',
        'to_task__to_project',
        'to_need',
        'to_need__to_project'
    ).order_by('-created_at')
    
    # Add context information to comments
    for comment in user_comments:
        if comment.to_project:
            comment.context_type = "project"
            comment.context_name = comment.to_project.name
            comment.context_url = f"/{comment.to_project.id}/"
        elif comment.to_task:
            comment.context_type = "task"
            comment.context_name = comment.to_task.name
            comment.context_url = f"/t/{comment.to_task.id}/"
            comment.project_name = comment.to_task.to_project.name if comment.to_task.to_project else None
        elif comment.to_need:
            comment.context_type = "need"
            comment.context_name = comment.to_need.name
            comment.context_url = f"/n/{comment.to_need.id}/"
            comment.project_name = comment.to_need.to_project.name if comment.to_need.to_project else None
        else:
            comment.context_type = "unknown"
            comment.context_name = "Unknown"
            comment.context_url = "#"
    
    # Paginate comments (20 per page)
    comments_paginator = Paginator(user_comments, 20)
    comments_page_number = request.GET.get('comments_page')
    comments_page = comments_paginator.get_page(comments_page_number)
    
    # ==== STATISTICS CALCULATION ====
    # Total projects (created + member of)
    total_projects = len(all_user_projects)
    
    # Total tasks in user's projects
    user_project_ids = [p.id for p in all_user_projects]
    total_tasks = Task.objects.filter(to_project_id__in=user_project_ids).count()
    
    # Total comments by user
    total_comments = user_comments.count()
    
    # Member since
    join_date = user.date_joined
    
    context = {
        "user": user,
        "user_profile": user_profile,
        "posts": posts,
        
        # Project data
        "user_projects": all_user_projects,
        "created_projects_count": created_projects.count(),
        "member_projects_count": member_projects.count(),
        
        # Comment data
        "user_comments": comments_page,
        "comments_paginator": comments_paginator,
        
        # Statistics
        "total_projects": total_projects,
        "total_tasks": total_tasks,
        "total_comments": total_comments,
        "join_date": join_date,
        
        # Additional context
        "is_own_profile": request.user == user,
    }
    
    return render(request, "profile.html", context=context)

# Keep all other existing functions unchanged
def person_memberships(request, person_id):
    person = Person.objects.get(id=person_id)
    memberships = person.membership_set.select_related('group')
    
    context = {
        'person': person,
        'memberships': memberships,
    }
    return render(request, 'person_memberships.html', context)

def membership_details(request, membership_id):
    membership = get_object_or_404(Membership, id=membership_id)
    decisions = membership.decisions.order_by('-date_made')
    comments = membership.comments.all()
    
    context = {
        'membership': membership,
        'decisions': decisions,
        'comments': comments,
    }
    return render(request, 'person_membership_details.html', context)

def signup(request):
    """Handle user registration with improved form including terms acceptance"""
    if request.user.is_authenticated:
        return redirect('project:index')
    
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user)
                
                newsletter_opt_in = form.cleaned_data.get('newsletter', False)
                if newsletter_opt_in:
                    pass
                
                messages.success(request, 
                    f'Welcome to 2do.net, {user.username}! Your account has been created successfully.')
                
                return redirect('project:index')
                
            except Exception as e:
                messages.error(request, 'An error occurred while creating your account. Please try again.')
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"User registration error: {e}")
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SignupForm()
    
    return render(request, 'signup.html', {'form': form})

def signin(request):
    """Handle user sign in with the improved form"""
    if request.user.is_authenticated:
        return redirect('project:index')
    
    if request.method == 'POST':
        form = SignInForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            remember_me = form.cleaned_data.get('remember_me', False)
            
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                
                if not remember_me:
                    request.session.set_expiry(0)
                
                messages.success(request, f'Welcome back, {user.username}!')
                
                next_page = request.GET.get('next', 'project:index')
                return redirect(next_page)
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SignInForm()
    
    return render(request, 'signin.html', {'form': form})

def custom_logout(request):
    logout(request)
    return redirect('/')

@login_required
def edit_profile(request, user_id):
    """Handle profile editing for authenticated users including hash-based avatar upload"""
    User = get_user_model()
    user = get_object_or_404(User, pk=user_id)
    
    if request.user.id != user.id and not request.user.is_staff:
        messages.error(request, "You don't have permission to edit this profile.")
        return redirect('user:userprofile', user_id=user_id)
    
    user_profile, created = UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        form = EditProfileForm(request.POST, request.FILES, instance=user, user_profile=user_profile)
        if form.is_valid():
            try:
                avatar_hash = form.cleaned_data.get('_avatar_hash')
                form.save()
                
                if avatar_hash and user_profile.avatar:
                    try:
                        avatar_filename = os.path.basename(user_profile.avatar.name)
                        hash_part = avatar_filename.split('.')[0]
                        messages.info(request, f'Avatar uploaded successfully! File hash: {hash_part}')
                    except:
                        pass
                
                messages.success(request, 'Your profile has been updated successfully!')
                return redirect('user:userprofile', user_id=user.id)
                
            except Exception as e:
                messages.error(request, 'An error occurred while updating your profile. Please try again.')
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Profile update error: {e}")
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = EditProfileForm(instance=user, user_profile=user_profile)
    
    avatar_info = None
    if user_profile.avatar and user_profile.avatar.name:
        try:
            avatar_info = {
                'filename': os.path.basename(user_profile.avatar.name),
                'hash': os.path.basename(user_profile.avatar.name).split('.')[0],
                'exists': True
            }
        except:
            avatar_info = {'exists': False}
    
    context = {
        'form': form,
        'user': user,
        'user_profile': user_profile,
        'avatar_info': avatar_info,
    }
    return render(request, 'edit_profile.html', context)