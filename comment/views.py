from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from .models import Comment

def comment_list_view(request, object_type, object_id):
    """
    Display comments and their first-level replies for a specific object (project, need, etc.).
    """
    comments = Comment.objects.filter(parent__isnull=True).select_related("user")
    return render(request, "comments.html", {"comments": comments})

def load_replies(request, comment_id):
    """
    Fetch replies dynamically when a user clicks "View Replies."
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
    """
    Handle AJAX request to add a new comment or reply.
    """
    if request.method == "POST":
        user = request.user
        content = request.POST.get("content")
        parent_id = request.POST.get("parent_id")
        parent = Comment.objects.filter(id=parent_id).first() if parent_id else None
        comment = Comment.objects.create(user=user, content=content, parent=parent)
        return JsonResponse({
            "id": comment.id,
            "content": comment.content,
            "user": comment.user.username,
            "total_replies": comment.total_replies,
        })
    return JsonResponse({"error": "Invalid request"}, status=400)
