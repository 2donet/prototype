from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from .models import Comment, CommentReport, ReportStatus
from .forms import CommentReportForm, ModeratorReviewForm
from project.models import Project
from task.models import Task


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


def report_comment_view(request, comment_id):
    """
    View for reporting a comment for moderation.
    """
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Check if the user already reported this comment
    if request.user.is_authenticated:
        existing_report = CommentReport.objects.filter(
            comment=comment,
            reportee=request.user,
            status__in=[ReportStatus.PENDING, ReportStatus.REVIEWED]
        ).first()
        
        if existing_report:
            messages.info(request, "You have already reported this comment. Here is your existing report.")
            # If user is a moderator, redirect them to the report detail page
            if is_moderator(request.user):
                return redirect('comments:report_detail', report_id=existing_report.id)
            # For regular users, we'll create a view to show their reports
            else:
                # Since we don't have a user report view yet, let's give them a message and redirect to comment
                messages.info(request, "Your report is being reviewed by our moderation team.")
                return redirect('comments:single_comment', comment_id=comment.id)
    
    # Check if the comment has already been reported by anyone
    existing_reports = CommentReport.objects.filter(
        comment=comment,
        status__in=[ReportStatus.PENDING, ReportStatus.REVIEWED]
    ).exists()
    
    if existing_reports and not is_moderator(request.user):
        messages.info(request, "This comment has already been reported and is being reviewed by our moderation team.")
        return redirect('comments:single_comment', comment_id=comment.id)
    
    if request.method == 'POST':
        form = CommentReportForm(
            request.POST,
            comment=comment,
            reportee=request.user if request.user.is_authenticated else None
        )
        
        if form.is_valid():
            report = form.save()
            messages.success(request, "Thank you for your report. A moderator will review it soon.")
            return redirect('comments:single_comment', comment_id=comment.id)
    else:
        form = CommentReportForm()
    
    return render(request, 'report_comment.html', {
        'form': form,
        'comment': comment
    })


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


def is_moderator(user):
    """Check if user is a moderator"""
    return user.is_authenticated and (user.is_staff or user.is_superuser or getattr(user, 'is_moderator', False))


@user_passes_test(is_moderator)
def report_list_view(request):
    """
    Display a list of all reports for moderators to review.
    """
    all_reports = CommentReport.objects.all().select_related('comment', 'reportee', 'reported', 'reviewed_by')
    
    # Count pending reports for the badge
    pending_count = all_reports.filter(status=ReportStatus.PENDING).count()
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        reports = all_reports.filter(status=status_filter)
    else:
        reports = all_reports
    
    return render(request, 'report_list.html', {
        'reports': reports,
        'statuses': ReportStatus,
        'pending_count': pending_count,
    })


@user_passes_test(is_moderator)
def report_detail_view(request, report_id):
    """
    Detail view for a specific report, allowing moderators to review and update it.
    """
    report = get_object_or_404(CommentReport, id=report_id)
    
    if request.method == 'POST':
        form = ModeratorReviewForm(request.POST, instance=report, moderator=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Report has been marked as {report.get_status_display()}")
            return redirect('comments:report_list')
    else:
        form = ModeratorReviewForm(instance=report)
    
    return render(request, 'report_detail.html', {
        'report': report,
        'form': form,
    })