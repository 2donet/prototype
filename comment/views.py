from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from django.db.models import Count, Prefetch, Q
import json
import logging

from django.contrib.auth import get_user_model
User = get_user_model()

from .models import (
    Comment, CommentReport, ReportStatus, 
    CommentVote, CommentReaction, VoteType, ReactionType
)
from .forms import CommentReportForm, ModeratorReviewForm
from project.models import Project
from task.models import Task
from need.models import Need

logger = logging.getLogger(__name__)

def get_comments_with_reactions(comments, user=None):
    """Enhance comments queryset with reaction counts and user vote status"""
    comments = comments.select_related('user').prefetch_related(
        'reactions', 
        'votes',
        'replies__user',
        # Use Prefetch objects for specific filters
        Prefetch(
            'votes',
            queryset=CommentVote.objects.filter(user=user) if user and user.is_authenticated else CommentVote.objects.none(),
            to_attr='user_votes'
        ),
        Prefetch(
            'reactions',
            queryset=CommentReaction.objects.filter(user=user) if user and user.is_authenticated else CommentReaction.objects.none(),
            to_attr='user_reactions_list'
        )
    )
    
    # More efficient processing of prefetched data
    for comment in comments:
        comment.reaction_counts = {}
        for reaction_type, _ in ReactionType.choices:
            count = sum(1 for r in comment.reactions.all() if r.reaction_type == reaction_type)
            if count > 0:
                comment.reaction_counts[reaction_type] = count
        
        if user and user.is_authenticated:
            comment.user_vote = comment.user_votes[0].vote_type if comment.user_votes else None
            comment.user_reactions = [r.reaction_type for r in comment.user_reactions_list]
    
    return comments

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
    elif object_type == "need":
        comments = Comment.objects.filter(to_need=object_id, parent__isnull=True).select_related(
            "user").prefetch_related("replies__user")
    else:
        return JsonResponse({"error": "Invalid object type"}, status=400)

    # Enhance comments with reaction counts and user vote/reaction status
    comments = get_comments_with_reactions(comments, request.user)
    
    return render(request, "comments.html", {"comments": comments})


def single_comment_view(request, comment_id):
    """
    Display a single comment and all of its replies in a dedicated view.
    """
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Get replies and enhance with reaction counts and user vote/reaction status
    replies = comment.replies.select_related("user").all()
    replies = get_comments_with_reactions(replies, request.user)
    
    # Also enhance the main comment
    comment.reaction_counts = comment.get_reaction_counts()
    
    # If user is authenticated, get their vote and reactions for the main comment
    if request.user.is_authenticated:
        # User vote
        try:
            vote = CommentVote.objects.get(user=request.user, comment=comment)
            comment.user_vote = vote.vote_type
        except CommentVote.DoesNotExist:
            comment.user_vote = None
            
        # User reactions
        reactions = CommentReaction.objects.filter(
            user=request.user, 
            comment=comment
        ).values_list('reaction_type', flat=True)
        comment.user_reactions = list(reactions)
    
    # Get the context based on what the comment is attached to
    context = {
        "comment": comment,
        "replies": replies,
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
            if is_moderator(request.user):
                return redirect('comments:report_detail', report_id=report.id)
            else:
                return redirect('comments:single_comment', comment_id=comment.id)
    else:
        form = CommentReportForm()
    
    # Add reaction counts and user vote status to the comment
    comment.reaction_counts = comment.get_reaction_counts()
    
    if request.user.is_authenticated:
        try:
            user_vote = CommentVote.objects.get(user=request.user, comment=comment)
            comment.user_vote = user_vote.vote_type
        except CommentVote.DoesNotExist:
            comment.user_vote = None
            
        user_reactions = CommentReaction.objects.filter(
            user=request.user, 
            comment=comment
        ).values_list('reaction_type', flat=True)
        comment.user_reactions = list(user_reactions)
    
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
    
    # Enhance replies with reaction counts and user vote/reaction status
    replies = get_comments_with_reactions(replies, request.user)
    
    reply_data = []
    for reply in replies:
        reply_info = {
            "id": reply.id,
            "content": reply.content,
            "user": reply.user.username if reply.user else "Anonymous",
            "total_replies": reply.total_replies,
            "score": reply.score,
            "reaction_counts": reply.reaction_counts,
        }
        
        if request.user.is_authenticated:
            reply_info["user_vote"] = getattr(reply, 'user_vote', None)
            reply_info["user_reactions"] = getattr(reply, 'user_reactions', [])
            
        reply_data.append(reply_info)
    
    return JsonResponse({"replies": reply_data})


def add_comment(request):
    """
    Add a new comment or reply.
    """
    if request.method == "POST":
        # Check if it's an AJAX request
        is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
        
        content = request.POST.get("content", "").strip()
        parent_id = request.POST.get("parent_id")
        to_project_id = request.POST.get("to_project_id")
        to_task_id = request.POST.get("to_task_id")
        to_need_id = request.POST.get("to_need_id")

        if not content:
            if is_ajax:
                return JsonResponse({"error": "Content is required"}, status=400)
            else:
                messages.error(request, "Content is required")
                return redirect(request.META.get('HTTP_REFERER', '/'))

        parent_comment = None
        to_project = None
        to_task = None
        to_need = None

        # Handle replies
        if parent_id:
            parent_comment = get_object_or_404(Comment, id=parent_id)
            
            # Inherit the parent's associations
            if parent_comment.to_need_id:
                to_need_id = parent_comment.to_need_id
            elif parent_comment.to_task_id:
                to_task_id = parent_comment.to_task_id
            elif parent_comment.to_project_id:
                to_project_id = parent_comment.to_project_id

        # Handle top-level comments - PRIORITIZE NEED over others!
        if to_need_id:
            to_need = get_object_or_404(Need, id=to_need_id)
            to_project = None
            to_task = None
        elif to_task_id:
            to_task = get_object_or_404(Task, id=to_task_id)
            to_project = None
        elif to_project_id:
            to_project = get_object_or_404(Project, id=to_project_id)

        # Allow anonymous users
        user = request.user if request.user.is_authenticated else None

        # Create the comment
        comment = Comment.objects.create(
            user=user,
            content=content,
            parent=parent_comment,
            to_project=to_project,
            to_task=to_task,
            to_need=to_need,
            author_name=request.POST.get("author_name") if not user else None,
            author_email=request.POST.get("author_email") if not user else None,
            ip_address=get_client_ip(request),
        )

        # Return appropriate response based on request type
        if is_ajax:
            return JsonResponse({
                "id": comment.id,
                "content": comment.content,
                "user": comment.user.username if comment.user else "Anonymous",
                "user_id": comment.user.id if comment.user else None,
                "total_replies": comment.total_replies,
                "score": comment.score,
                "to_need_id": comment.to_need_id,
                "to_project_id": comment.to_project_id,
                "to_task_id": comment.to_task_id
            })
        else:
            # For non-AJAX requests, redirect back to the referring page
            messages.success(request, "Comment added successfully!")
            
            # Determine where to redirect based on what the comment is attached to
            if comment.to_task:
                return redirect('task:task_detail', task_id=comment.to_task.id)
            elif comment.to_need:
                return redirect('need:need', need_id=comment.to_need.id)
            elif comment.to_project:
                return redirect('project:project', project_id=comment.to_project.id)
            else:
                return redirect(request.META.get('HTTP_REFERER', '/'))
    
    return JsonResponse({"error": "Method not allowed"}, status=405)
def vote_comment(request, comment_id):
    """
    Vote on a comment (upvote or downvote)
    """
    logger.info(f"Vote request received for comment {comment_id}")
    
    if not request.user.is_authenticated:
        logger.warning("Unauthenticated vote attempt")
        return JsonResponse({"error": "Authentication required"}, status=401)
        
    if request.method != "POST":
        logger.warning(f"Invalid method: {request.method}")
        return JsonResponse({"error": "Invalid request method"}, status=405)
        
    logger.info(f"Content type: {request.content_type}")
    
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Handle both form data and JSON
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            vote_type = data.get("vote_type")
            logger.info(f"JSON data: {data}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON data")
            return JsonResponse({"error": "Invalid JSON"}, status=400)
    else:
        vote_type = request.POST.get("vote_type")
        logger.info(f"Form data - vote_type: {vote_type}")
    
    logger.info(f"Vote type: {vote_type}")
    
    if vote_type not in [VoteType.UPVOTE, VoteType.DOWNVOTE]:
        logger.warning(f"Invalid vote type: {vote_type}")
        return JsonResponse({"error": "Invalid vote type"}, status=400)
        
    # Create or update the vote
    vote, created = CommentVote.objects.update_or_create(
        comment=comment,
        user=request.user,
        defaults={"vote_type": vote_type}
    )
    
    # Manually update comment score to ensure it's current
    upvotes = comment.votes.filter(vote_type=VoteType.UPVOTE).count()
    downvotes = comment.votes.filter(vote_type=VoteType.DOWNVOTE).count()
    comment.score = upvotes - downvotes
    comment.save(update_fields=['score'])
    
    logger.info(f"Vote processed. New score: {comment.score}")
    
    # Return updated comment info
    return JsonResponse({
        "id": comment.id,
        "score": comment.score,
        "vote_type": vote_type
    })


def remove_vote(request, comment_id):
    """
    Remove a vote from a comment
    """
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
        
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)
        
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Delete the vote if it exists
    try:
        vote = CommentVote.objects.get(comment=comment, user=request.user)
        vote.delete()
        
        # Manually update comment score
        upvotes = comment.votes.filter(vote_type=VoteType.UPVOTE).count()
        downvotes = comment.votes.filter(vote_type=VoteType.DOWNVOTE).count()
        comment.score = upvotes - downvotes
        comment.save(update_fields=['score'])
        
        # Return updated comment info
        return JsonResponse({
            "id": comment.id,
            "score": comment.score,
            "vote_removed": True
        })
    except CommentVote.DoesNotExist:
        return JsonResponse({"error": "No vote to remove"}, status=404)


def toggle_reaction(request, comment_id):
    """
    Toggle a reaction on a comment
    """
    logger.info(f"Reaction toggle request received for comment {comment_id}")
    
    if not request.user.is_authenticated:
        logger.warning("Unauthenticated reaction attempt")
        return JsonResponse({"error": "Authentication required"}, status=401)
        
    if request.method != "POST":
        logger.warning(f"Invalid method: {request.method}")
        return JsonResponse({"error": "Invalid request method"}, status=405)
    
    logger.info(f"Content type: {request.content_type}")
    
    comment = get_object_or_404(Comment, id=comment_id)
    logger.info(f"Comment found: {comment.id}")
    
    # Handle both form data and JSON
    if request.content_type == 'application/json':
        try:
            body = request.body.decode('utf-8')
            logger.info(f"Raw JSON: {body}")
            data = json.loads(body)
            reaction_type = data.get("reaction_type")
            logger.info(f"JSON data: {data}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON data: {e}")
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            logger.error(f"Error parsing JSON: {str(e)}")
            return JsonResponse({"error": f"Error: {str(e)}"}, status=400)
    else:
        reaction_type = request.POST.get("reaction_type")
        logger.info(f"Form data - reaction_type: {reaction_type}")
    
    logger.info(f"Reaction type: {reaction_type}")
    
    # Make sure ReactionType.choices is properly defined
    all_choices = dict(ReactionType.choices)
    logger.info(f"Available reaction types: {all_choices}")
    
    if reaction_type not in all_choices:
        logger.warning(f"Invalid reaction type: {reaction_type}")
        return JsonResponse({"error": f"Invalid reaction type. Must be one of: {list(all_choices.keys())}"}, status=400)
    
    try:    
        # Try to get the existing reaction
        try:
            reaction = CommentReaction.objects.get(
                comment=comment,
                user=request.user,
                reaction_type=reaction_type
            )
            # If it exists, delete it (toggle off)
            logger.info(f"Removing existing reaction {reaction.id}")
            reaction.delete()
            action = "removed"
        except CommentReaction.DoesNotExist:
            # If it doesn't exist, create it
            logger.info(f"Creating new reaction")
            CommentReaction.objects.create(
                comment=comment,
                user=request.user,
                reaction_type=reaction_type
            )
            action = "added"
        
        # Get updated reaction counts
        reaction_counts = comment.get_reaction_counts()
        logger.info(f"Updated reaction counts: {reaction_counts}")
        
        # Return updated comment info
        response_data = {
            "id": comment.id,
            "action": action,
            "reaction_type": reaction_type,
            "reaction_counts": reaction_counts
        }
        logger.info(f"Sending response: {response_data}")
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in toggle_reaction: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({"error": f"Server error: {str(e)}"}, status=500)


def get_reactions_summary(request, comment_id):
    """
    Get a summary of all reactions on a comment
    """
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Count reactions by type
    reaction_counts = CommentReaction.objects.filter(comment=comment) \
        .values('reaction_type') \
        .annotate(count=Count('reaction_type')) \
        .order_by('-count')
    
    return JsonResponse(list(reaction_counts), safe=False)


def get_client_ip(request):
    """Get the client IP address from the request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


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
@user_passes_test(is_moderator)
def report_detail_view(request, report_id):
    """
    Detail view for a specific report, allowing moderators to review and update it.
    """
    report = get_object_or_404(CommentReport, id=report_id)
    
    
    comment = report.comment
    
    # Manually add reaction counts
    comment.reaction_counts = comment.get_reaction_counts()
    
    # If user is authenticated, get their vote and reactions
    if request.user.is_authenticated:
        try:
            vote = CommentVote.objects.get(user=request.user, comment=comment)
            comment.user_vote = vote.vote_type
        except CommentVote.DoesNotExist:
            comment.user_vote = None
            
        reactions = CommentReaction.objects.filter(
            user=request.user, 
            comment=comment
        ).values_list('reaction_type', flat=True)
        comment.user_reactions = list(reactions)
    
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

@user_passes_test(is_moderator)
def delete_comment(request, comment_id):
    """Delete a reported comment and update the report status"""
    try:
        comment = Comment.objects.get(id=comment_id)
    except Comment.DoesNotExist:
        messages.warning(request, f"Comment #{comment_id} does not exist or was already deleted.")
        
        # If there's a report ID, update it to resolved since the comment is gone
        report_id = request.GET.get('report_id')
        if report_id:
            try:
                report = CommentReport.objects.get(id=report_id)
                report.status = ReportStatus.RESOLVED
                report.moderator_notes = (report.moderator_notes or "") + "\nComment was not found (already deleted)."
                report.save()
                messages.info(request, "Report has been marked as resolved.")
                return redirect('comments:report_list')
            except CommentReport.DoesNotExist:
                pass
                
        return redirect('comments:report_list')
    
    # Store report_id before deleting the comment
    report_id = request.GET.get('report_id')
    
    # Delete the comment
    comment.delete()
    
    # If we have a report ID, update its status
    if report_id:
        try:
            report = CommentReport.objects.get(id=report_id)
            report.status = ReportStatus.RESOLVED
            report.moderator_notes = (report.moderator_notes or "") + "\nComment was deleted by moderator."
            report.save()
            messages.success(request, "Comment has been deleted and report resolved.")
        except CommentReport.DoesNotExist:
            messages.success(request, "Comment has been deleted but report was not found.")
    else:
        messages.success(request, "Comment has been deleted.")
        
    return redirect('comments:report_list')

@user_passes_test(is_moderator)
def ban_user(request, user_id):
    """Ban a user from commenting"""
    user = get_object_or_404(User, id=user_id)
    report_id = request.GET.get('report_id')
    
    # Add your user banning logic here
    # You might want to set a field on your User model like is_banned=True
    # Or create a BannedUser model to track reasons and duration
    
    messages.success(request, f"User {user.username} has been banned.")
    
    # Redirect back to the report detail if applicable
    if report_id:
        return redirect('comments:report_detail', report_id=report_id)
    return redirect('comments:report_list')

@login_required
def edit_comment(request, comment_id):
    """Edit a comment and preserve history"""
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Check if user has permission to edit
    if not comment.can_edit(request.user):
        messages.error(request, "You don't have permission to edit this comment.")
        return redirect('comments:single_comment', comment_id=comment.id)
    
    if request.method == 'POST':
        new_content = request.POST.get('content', '').strip()
        if not new_content:
            messages.error(request, "Comment content cannot be empty.")
            return redirect('comments:edit_comment', comment_id=comment.id)
        
        # Update comment with history tracking
        comment.edit(new_content, editor=request.user)
        messages.success(request, "Comment updated successfully.")
        return redirect('comments:single_comment', comment_id=comment.id)
    
    return render(request, 'edit_comment.html', {'comment': comment})