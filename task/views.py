from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Prefetch
from django.urls import reverse
from django.contrib import messages
from django.views.generic import CreateView, UpdateView
from .models import Task
from .forms import TaskForm
from comment.models import Comment, CommentVote
from skills.models import Skill

def task_detail(request, task_id):
    """
    Display details of a specific task, including its comments, replies, and skills.
    """
    task = get_object_or_404(Task, pk=task_id)
    
    # Fetch top-level comments with all necessary relations
    comments = Comment.objects.filter(
        to_task=task_id, 
        parent__isnull=True
    ).select_related('user').prefetch_related(
        Prefetch('replies', queryset=Comment.objects.select_related('user')),
        'votes')
    
    # Add user vote status to comments
    for comment in comments:
        
        if request.user.is_authenticated:
            user_vote = comment.votes.filter(user=request.user).first()
            comment.user_vote = user_vote.vote_type if user_vote else None
            
        else:
            comment.user_vote = None

        
        for reply in comment.replies.all():

            
            if request.user.is_authenticated:
                reply_vote = reply.votes.filter(user=request.user).first()
                reply.user_vote = reply_vote.vote_type if reply_vote else None
            else:
                reply.user_vote = None

    
    context = {
        "task": task,
        "comments": comments,
    }
    return render(request, "task_detail.html", context=context)

def add_skill_to_task(request, task_id):
    """Handle adding skills to tasks"""
    if request.method == 'POST':
        task = get_object_or_404(Task, pk=task_id)
        if request.user != task.created_by:
            messages.error(request, "You can only add skills to tasks you created")
            return redirect('task:task_detail', task_id=task_id)
            
        skill_name = request.POST.get('skill_name', '').strip()
        if skill_name:
            try:
                task.add_skill(skill_name)
                messages.success(request, f"Added skill: {skill_name}")
            except ValueError as e:
                messages.error(request, str(e))
        
    return redirect('task:task_detail', task_id=task_id)
def task_list(request):
    """
    Display a list of all tasks.
    """
    tasks = Task.objects.all().select_related('created_by', 'to_project')
    context = {
        "tasks": tasks,
    }
    return render(request, "task_list.html", context=context)



class CreateTaskView(CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'task_form.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        # Save the many-to-many skills relationship
        self.object.skills.set(form.cleaned_data['skills'])
        messages.success(self.request, "Task created successfully!")
        return response

    def get_success_url(self):
        return reverse('task:task_detail', kwargs={'task_id': self.object.id})

class UpdateTaskView(UpdateView):
    model = Task
    form_class = TaskForm
    template_name = 'task_form.html'
    pk_url_kwarg = 'task_id'

    def get_queryset(self):
        # Only allow task creator to edit
        return super().get_queryset().filter(created_by=self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        # Update the many-to-many skills relationship
        self.object.skills.set(form.cleaned_data['skills'])
        messages.success(self.request, "Task updated successfully!")
        return response

    def get_success_url(self):
        return reverse('task:task_detail', kwargs={'task_id': self.object.id})