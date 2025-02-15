from django.shortcuts import get_object_or_404, render, redirect
from django.urls import path, reverse
from django.db.models import Prefetch
from django.contrib.auth import authenticate, login, logout
from comment.models import Comment
from decisions.models import Decision
from user.models import Membership, UserProfile, Post
from user.models import Person
from user.signup import SignupForm
from user.signin import SignInForm
from django.contrib.auth import get_user_model

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
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/u/signin')  # Redirect to login or another page after signup
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})

def signin_view(request):
    if request.method == 'POST':
        form = SignInForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('/')
    else:
        form = SignInForm()
    return render(request, 'signin.html', {'form': form})

def custom_logout(request):
    logout(request)  # Log out the user
    return redirect('/')  # Redirect to a specific page (e.g., home page)
