# views.py



from django.shortcuts import get_object_or_404, render, redirect
from django.urls import path, reverse
from django.db.models import Prefetch
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from comment.models import Comment
from decisions.models import Decision
from user.models import Membership, UserProfile, Post
from django.contrib.auth.decorators import login_required
from user.models import Person

from .forms import SignInForm, SignupForm, EditProfileForm
from django.contrib.auth import get_user_model
import os

def userprofile(request, user_id):
    User = get_user_model()
    posts = Post.objects.filter(author=user_id).order_by('-date')
    # Retrieve the User object by its ID
    user = get_object_or_404(User, pk=user_id)
    user_profile = getattr(user, 'profile', None)
    # Render a template with the UserProfile and User information
    if user_profile is None:
        return render(request, "userprofile_not_found.html", {"user": user})
    
    # comments = Comment.objects.filter(to_need=need_id).prefetch_related(
    #     Prefetch("replies", queryset=Comment.objects.select_related("user"))
    # )
    context = {"user": user,
               "user_profile": user_profile,
               "posts": posts
               #"memberships": memberships
    # "comments":comments,
    
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
    return render(request, "profile.html", context=context)
    #return render(request, "profile.html", )
    # when loading template using "details.html" instead of "need/details.html", the project template is loaded (even when)
    # adding more logic to the project's details.html may be used 

def person_memberships(request, person_id):
    person = Person.objects.get(id=person_id)
    memberships = person.membership_set.select_related('group')  # Fetch memberships with group details
    
    context = {
        'person': person,
        'memberships': memberships,
    }
    return render(request, 'person_memberships.html', context)


def membership_details(request, membership_id):
    membership = get_object_or_404(Membership, id=membership_id)
    decisions = membership.decisions.order_by('-date_made')  # Sort decisions by newest
    comments = membership.comments.all()  # Get comments linked to the membership
    
    context = {
        'membership': membership,
        'decisions': decisions,
        'comments': comments,
    }
    return render(request, 'person_membership_details.html', context)

def signup(request):
    """
    Handle user registration with improved form including terms acceptance
    """
    if request.user.is_authenticated:
        return redirect('project:index')  # Redirect if already logged in
    
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                
                # Log the user in immediately after registration
                login(request, user)
                
                # Store newsletter preference (you might want to create a model for this)
                newsletter_opt_in = form.cleaned_data.get('newsletter', False)
                if newsletter_opt_in:
                    # Handle newsletter subscription
                    # This could be a separate model or service
                    pass
                
                messages.success(request, 
                    f'Welcome to 2do.net, {user.username}! Your account has been created successfully.')
                
                return redirect('project:index')  # Redirect to home or dashboard
                
            except Exception as e:
                messages.error(request, 'An error occurred while creating your account. Please try again.')
                # Log the error for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"User registration error: {e}")
        else:
            # Form validation errors will be displayed in the template
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SignupForm()
    
    return render(request, 'signup.html', {'form': form})



def signin(request):
    """
    Handle user sign in with the improved form
    """
    if request.user.is_authenticated:
        return redirect('project:index')  # Redirect if already logged in
    
    if request.method == 'POST':
        form = SignInForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            remember_me = form.cleaned_data.get('remember_me', False)
            
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                
                # Handle remember me functionality (when implemented)
                if not remember_me:
                    request.session.set_expiry(0)  # Session expires on browser close
                
                messages.success(request, f'Welcome back, {user.username}!')
                
                # Redirect to next page or home
                next_page = request.GET.get('next', 'project:index')
                return redirect(next_page)
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            # Form validation errors will be displayed in the template
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SignInForm()
    
    return render(request, 'signin.html', {'form': form})

def custom_logout(request):
    logout(request)  # Log out the user
    return redirect('/')  # Redirect to a specific page (e.g., home page)

@login_required
def edit_profile(request, user_id):
    """
    Handle profile editing for authenticated users including hash-based avatar upload
    """
    User = get_user_model()
    user = get_object_or_404(User, pk=user_id)
    
    # Check if user can edit this profile (own profile or admin)
    if request.user.id != user.id and not request.user.is_staff:
        messages.error(request, "You don't have permission to edit this profile.")
        return redirect('user:userprofile', user_id=user_id)
    
    # Get or create user profile
    user_profile, created = UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        form = EditProfileForm(request.POST, request.FILES, instance=user, user_profile=user_profile)
        if form.is_valid():
            try:
                # Get any hash info before saving
                avatar_hash = form.cleaned_data.get('_avatar_hash')
                
                form.save()
                
                # Show avatar hash info if new avatar was uploaded
                if avatar_hash and user_profile.avatar:
                    # Safely get avatar info
                    try:
                        avatar_filename = os.path.basename(user_profile.avatar.name)
                        hash_part = avatar_filename.split('.')[0]
                        messages.info(request, f'Avatar uploaded successfully! File hash: {hash_part}')
                    except:
                        pass  # Ignore if we can't get hash info
                
                messages.success(request, 'Your profile has been updated successfully!')
                return redirect('user:userprofile', user_id=user.id)
                
            except Exception as e:
                messages.error(request, 'An error occurred while updating your profile. Please try again.')
                # Log the error for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Profile update error: {e}")
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = EditProfileForm(instance=user, user_profile=user_profile)
    
    # Simplified avatar info - just check if avatar exists
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
        'avatar_info': avatar_info,  # Simplified avatar info
    }
    return render(request, 'edit_profile.html', context)
    """
    Handle profile editing for authenticated users including hash-based avatar upload
    """
    User = get_user_model()
    user = get_object_or_404(User, pk=user_id)
    
    # Check if user can edit this profile (own profile or admin)
    if request.user.id != user.id and not request.user.is_staff:
        messages.error(request, "You don't have permission to edit this profile.")
        return redirect('user:userprofile', user_id=user_id)
    
    # Get or create user profile
    user_profile, created = UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        form = EditProfileForm(request.POST, request.FILES, instance=user, user_profile=user_profile)
        if form.is_valid():
            try:
                # Get any hash info before saving
                avatar_hash = form.cleaned_data.get('_avatar_hash')
                
                form.save()
                
                # Add any messages from the form processing
                form_messages = form.get_messages()
                for level, message in form_messages:
                    if level == 'info':
                        messages.info(request, message)
                    elif level == 'success':
                        messages.success(request, message)
                    elif level == 'warning':
                        messages.warning(request, message)
                
                # Show avatar hash info if new avatar was uploaded
                if avatar_hash and user_profile.avatar:
                    avatar_info = user_profile.get_avatar_info()
                    if avatar_info:
                        messages.info(request, 
                            f'Avatar uploaded successfully! File hash: {avatar_info["hash"]}'
                        )
                
                messages.success(request, 'Your profile has been updated successfully!')
                return redirect('user:userprofile', user_id=user.id)
                
            except Exception as e:
                messages.error(request, 'An error occurred while updating your profile. Please try again.')
                # Log the error for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Profile update error: {e}")
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = EditProfileForm(instance=user, user_profile=user_profile)
    
    # Add avatar info to context for debugging/admin use
    avatar_info = user_profile.get_avatar_info() if user_profile.has_avatar() else None
    
    context = {
        'form': form,
        'user': user,
        'user_profile': user_profile,
        'avatar_info': avatar_info,  # For debugging/admin display
    }
    return render(request, 'edit_profile.html', context)