from django.shortcuts import render

# Create your views here.
from django.contrib.auth.decorators import login_required

from django.urls import path, reverse
from django.db.models import Prefetch


from django.contrib.auth import get_user_model

def review(request):
    """
        
        Review sample page

    """
    return render(request, "review.html")