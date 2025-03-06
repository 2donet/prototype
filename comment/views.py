from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from .models import Comment
from project.models import Project
from task.models import Task
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required


def comment_list_view(request, object_type, object_id):
    """
    Display comments and their first-level replies for a specific object (project, task, etc.).
    """
    if object_type == "project":
        comments = Comment.objects.filter(to_project=object_id, parent__isnull=True).select_related(
            "user").prefetch_related("replies__user")
    elif object_type == "task":
        comments = Comment.objects.filter(to_task=object_id, parent__isnull=True).select_related(
            "user").prefetch_related("replies__user")
    else:
        return JsonResponse({"error": "Invalid object type"}, status=400)

    return render(request, "comments.html", {"comments": comments})


def single_comment_view(request, comment_id):
    """
    Display a single comment and all of its replies in a dedicated view.
    """
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Get the context based on what the comment is attached to
    context = {
        "comment": comment,
        "replies": comment.replies.select_related("user").all(),
    }
    
    # Add the parent object to context if this is a reply
    if comment.parent:
        context["parent_comment"] = comment.parent
    
    # Add the associated object (project, task, etc.) to context
    if comment.to_project:
        context["object_type"] = "project"
        context["object"] = comment.to_project
    elif comment.to_task:
        context["object_type"] = "task"
        context["object"] = comment.to_task
    elif comment.to_need:
        context["object_type"] = "need"
        context["object"] = comment.to_need
    elif comment.to_decision:
        context["object_type"] = "decision"
        context["object"] = comment.to_decision
    elif comment.to_membership:
        context["object_type"] = "membership"
        context["object"] = comment.to_membership
    elif comment.to_report:
        context["object_type"] = "report"
        context["object"] = comment.to_report
    
    return render(request, "single_comment.html", context)


def load_replies(request, comment_id):
    """
    Fetch replies dynamically for a specific comment.
    """
    parent_comment = get_object_or_404(Comment, id=comment_id)
    replies = parent_comment.replies.select_related("user").all()
    return JsonResponse({
        "replies": [
            {
                "id": reply.id,
                "content": reply.content,
                "user": reply.user.username,
                "total_replies": reply.total_replies,
            }
            for reply in replies
        ]
    })


def add_comment(request):
    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        parent_id = request.POST.get("parent_id")
        to_project_id = request.POST.get("to_project_id")

        if not content:
            return JsonResponse({"error": "Content is required"}, status=400)

        parent_comment = None
        to_project = None

        # Handle replies
        if parent_id:
            parent_comment = get_object_or_404(Comment, id=parent_id)

        # Handle top-level comments
        if to_project_id:
            to_project = get_object_or_404(Project, id=to_project_id)

        # Allow anonymous users
        user = request.user if request.user.is_authenticated else None

        # Create the comment
        comment = Comment.objects.create(
            user=user,
            content=content,
            parent=parent_comment,
            to_project=to_project,
        )

        return JsonResponse({
            "id": comment.id,
            "content": comment.content,
            "user": comment.user.username if comment.user else "Anonymous",
            "total_replies": comment.total_replies,
        })

    return JsonResponse({"error": "Invalid request method"}, status=405)