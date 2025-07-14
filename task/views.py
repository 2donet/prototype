from django.shortcuts import get_object_or_404, render
from comment.models import Comment
from task.models import Task

def task_detail(request, task_id):
    """
    Display details of a specific task, including its comments and replies.
    """
    task = get_object_or_404(Task, pk=task_id)
    # Fetch top-level comments and their replies for the task
    comments = Comment.objects.filter(to_task=task_id, parent__isnull=True).prefetch_related('replies__user')
    context = {
        "task": task,
        "comments": comments,
    }
    return render(request, "task_detail.html", context=context)

def task_list(request):
    """
    Display a list of all tasks.
    """
    tasks = Task.objects.all()
    context = {
        "tasks": tasks,
    }
    return render(request, "task_list.html", context=context)