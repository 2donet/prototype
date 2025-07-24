# comment/views.py
from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Prefetch, Q
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.utils import timezone

User = get_user_model()

from .models import (
    Comment, CommentReport, CommentReportGroup, ReportStatus, 
    CommentVote, VoteType, ModerationAction, ModerationDecision,
    DecisionScope, ReportType, ModeratorLevel
)
from .forms import CommentReportForm, ModerationActionForm, ModeratorReviewForm
from .utils import is_moderator, get_moderator_level, get_client_ip, get_avatar_url

import json
import logging

logger = logging.getLogger(__name__)


def comment_list_view(request, object_type, object_id):
    if object_type == "project":
        comments = Comment.objects.filter(to_project=object_id, parent__isnull=True).select_related("user").prefetch_related("replies__user")
    elif object_type == "task":
        comments = Comment.objects.filter(to_task=object_id, parent__isnull=True).select_related("user").prefetch_related("replies__user")
    elif object_type == "need":
        comments = Comment.objects.filter(to_need=object_id, parent__isnull=True).select_related("user").prefetch_related("replies__user")
    else:
        return JsonResponse({"error": "Invalid object type"}, status=400)
    return render(request, "comments.html", {"comments": comments})


def single_comment_view(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    replies = comment.replies.select_related("user").all()
    context = {
        "comment": comment,
        "replies": replies,
    }
    if comment.parent:
        context["parent_comment"] = comment.parent
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
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Check if user is trying to report their own comment
    if request.user.is_authenticated and comment.user == request.user:
        messages.error(request, "You cannot report your own comment.")
        return redirect('comments:single_comment', comment_id=comment.id)
    
    # Check if this specific user has already reported this comment
    if request.user.is_authenticated:
        existing_report = CommentReport.objects.filter(
            comment=comment,
            reportee=request.user,
            status__in=[ReportStatus.PENDING, ReportStatus.REVIEWED]
        ).first()
        if existing_report:
            messages.info(request, "You have already reported this comment.")
            if is_moderator(request.user):
                return redirect('comments:enhanced_report_detail', comment_id=comment.id)
            else:
                messages.info(request, "Your report is being reviewed by our moderation team.")
                return redirect('comments:single_comment', comment_id=comment.id)
    
    if request.method == 'POST':
        form = CommentReportForm(
            request.POST,
            comment=comment,
            reportee=request.user if request.user.is_authenticated else None
        )
        if form.is_valid():
            try:
                report = form.save()
                messages.success(request, "Thank you for your report. A moderator will review it soon.")
                
                # Update the report group after creating a new report
                CommentReportGroup.update_for_comment(comment)
                
                if is_moderator(request.user):
                    return redirect('comments:enhanced_report_detail', comment_id=comment.id)
                else:
                    return redirect('comments:single_comment', comment_id=comment.id)
            except Exception as e:
                logger.error(f"Error creating report: {str(e)}")
                messages.error(request, "There was an error submitting your report. Please try again.")
        else:
            logger.warning(f"Invalid report form: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = CommentReportForm()
    
    return render(request, 'report_comment.html', {
        'form': form,
        'comment': comment
    })


def add_comment(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "error": "Method not allowed"}, status=405)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    content = request.POST.get("content", "").strip()
    parent_id = request.POST.get("parent_id")
    to_project_id = request.POST.get("to_project_id")
    to_task_id = request.POST.get("to_task_id")
    to_need_id = request.POST.get("to_need_id")
    if not content:
        return JsonResponse({
            "status": "error",
            "error": "Content is required",
            "fields": {"content": "This field cannot be empty"}
        }, status=400)
    try:
        parent_comment = None
        if parent_id:
            parent_comment = get_object_or_404(Comment, id=parent_id)
            to_need_id = to_need_id or parent_comment.to_need_id
            to_task_id = to_task_id or parent_comment.to_task_id
            to_project_id = to_project_id or parent_comment.to_project_id
        comment = Comment.objects.create(
            user=request.user if request.user.is_authenticated else None,
            content=content,
            parent=parent_comment,
            to_project_id=to_project_id,
            to_task_id=to_task_id,
            to_need_id=to_need_id,
            author_name=request.POST.get("author_name") if not request.user.is_authenticated else None,
            author_email=request.POST.get("author_email") if not request.user.is_authenticated else None,
            ip_address=get_client_ip(request),
        )
        
        response_data = {
            "status": "success",
            "comment": {
                "id": comment.id,
                "content": comment.content,
                "user": comment.user.username if comment.user else (comment.author_name or "Anonymous"),
                "user_id": comment.user.id if comment.user else None,
                "author_avatar": get_avatar_url(comment.user),
                "created_at": comment.created_at.isoformat(),
                "total_replies": 0,
                "score": 0,
                "parent_id": parent_id,
                "to_need_id": comment.to_need_id,
                "to_project_id": comment.to_project_id,
                "to_task_id": comment.to_task_id,
                "user_vote": None,
            }
        }
        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": "An error occurred while saving your comment",
            "debug": str(e) if settings.DEBUG else None
        }, status=500)


def load_replies(request, comment_id):
    parent_comment = get_object_or_404(Comment, id=comment_id)
    replies = parent_comment.replies.select_related("user", "user__profile").all()
    
    reply_data = []
    for reply in replies:
        reply_info = {
            "id": reply.id,
            "content": reply.content,
            "user": reply.user.username if reply.user else "Anonymous",
            "user_id": reply.user.id if reply.user else None,
            "author_avatar": get_avatar_url(reply.user),
            "total_replies": reply.total_replies,
            "score": reply.score,
        }
        reply_data.append(reply_info)
    return JsonResponse({"replies": reply_data})


def vote_comment(request, comment_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)
    comment = get_object_or_404(Comment, id=comment_id)
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            vote_type = data.get("vote_type")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
    else:
        vote_type = request.POST.get("vote_type")
    if vote_type not in [VoteType.UPVOTE, VoteType.DOWNVOTE]:
        return JsonResponse({"error": "Invalid vote type"}, status=400)
    vote, created = CommentVote.objects.update_or_create(
        comment=comment,
        user=request.user,
        defaults={"vote_type": vote_type}
    )
    upvotes = comment.votes.filter(vote_type=VoteType.UPVOTE).count()
    downvotes = comment.votes.filter(vote_type=VoteType.DOWNVOTE).count()
    comment.score = upvotes - downvotes
    comment.save(update_fields=['score'])
    return JsonResponse({
        "id": comment.id,
        "score": comment.score,
        "vote_type": vote_type
    })


def remove_vote(request, comment_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)
    comment = get_object_or_404(Comment, id=comment_id)
    try:
        vote = CommentVote.objects.get(comment=comment, user=request.user)
        vote.delete()
        upvotes = comment.votes.filter(vote_type=VoteType.UPVOTE).count()
        downvotes = comment.votes.filter(vote_type=VoteType.DOWNVOTE).count()
        comment.score = upvotes - downvotes
        comment.save(update_fields=['score'])
        return JsonResponse({
            "id": comment.id,
            "score": comment.score,
            "vote_removed": True
        })
    except CommentVote.DoesNotExist:
        return JsonResponse({"error": "No vote to remove"}, status=404)


@user_passes_test(is_moderator)
def delete_comment(request, comment_id):
    """Legacy delete comment function - kept for backwards compatibility"""
    try:
        comment = Comment.objects.get(id=comment_id)
    except Comment.DoesNotExist:
        messages.warning(request, f"Comment #{comment_id} does not exist or was already deleted.")
        report_id = request.GET.get('report_id')
        if report_id:
            try:
                report = CommentReport.objects.get(id=report_id)
                report.status = ReportStatus.RESOLVED
                report.moderator_notes = (report.moderator_notes or "") + "\nComment was not found (already deleted)."
                report.save()
                messages.info(request, "Report has been marked as resolved.")
                return redirect('comments:enhanced_report_list')
            except CommentReport.DoesNotExist:
                pass
        return redirect('comments:enhanced_report_list')
    
    report_id = request.GET.get('report_id')
    comment.delete()
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
    return redirect('comments:enhanced_report_list')


@user_passes_test(is_moderator)
def report_list_view(request):
    all_reports = CommentReport.objects.all().select_related('comment', 'reportee', 'reported', 'reviewed_by')
    pending_count = all_reports.filter(status=ReportStatus.PENDING).count()
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
    report = get_object_or_404(CommentReport, id=report_id)
    comment = report.comment
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
def enhanced_delete_comment(request, comment_id):
    """Enhanced delete comment function that works with the new moderation system"""
    
    try:
        comment = get_object_or_404(Comment, id=comment_id)
    except Comment.DoesNotExist:
        messages.warning(request, f"Comment #{comment_id} does not exist or was already deleted.")
        return redirect('comments:enhanced_report_list')
    
    # Check moderator permissions
    moderator_level = get_moderator_level(request.user)
    if moderator_level == ModeratorLevel.JUNIOR:
        messages.error(request, "You don't have permission to delete comments.")
        return redirect('comments:enhanced_report_detail', comment_id=comment_id)
    
    if request.method == 'POST':
        # Get the reason from the form
        reason = request.POST.get('reason', 'Comment deleted by moderator')
        apply_to_all = request.POST.get('apply_to_all', False)
        
        try:
            # Create moderation action for audit trail
            moderation_action = ModerationAction.objects.create(
                moderator=request.user,
                comment=comment,
                decision=ModerationDecision.REMOVE,
                decision_scope=DecisionScope.ALL_REPORTS if apply_to_all else DecisionScope.SINGLE_REPORT,
                reason=reason,
                notify_reporters=True,
                project=comment.to_project or (comment.to_task.to_project if comment.to_task else None) or (comment.to_need.to_project if comment.to_need else None)
            )
            
            # Apply the decision (this will update comment status and resolve reports)
            moderation_action.apply_decision()
            
            # Actually delete the comment
            comment_content_preview = comment.content[:50] + "..." if len(comment.content) > 50 else comment.content
            comment.delete()
            
            # Update report group (will be deleted if no reports remain)
            CommentReportGroup.update_for_comment(comment)
            
            messages.success(request, f"Comment '{comment_content_preview}' has been deleted successfully.")
            logger.info(f"Comment {comment_id} deleted by moderator {request.user.username}")
            
        except Exception as e:
            logger.error(f"Error deleting comment {comment_id}: {str(e)}")
            messages.error(request, "There was an error deleting the comment. Please try again.")
            return redirect('comments:enhanced_report_detail', comment_id=comment_id)
        
        return redirect('comments:enhanced_report_list')
    
    # GET request - show confirmation form
    context = {
        'comment': comment,
        'reports': comment.reports.all(),
        'report_count': comment.reports.count(),
    }
    return render(request, 'confirm_delete_comment.html', context)


@user_passes_test(is_moderator)
def ban_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    report_id = request.GET.get('report_id')
    messages.success(request, f"User {user.username} has been banned.")
    if report_id:
        return redirect('comments:enhanced_report_detail', comment_id=report_id)
    return redirect('comments:enhanced_report_list')


@login_required
def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if not comment.can_edit(request.user):
        messages.error(request, "You don't have permission to edit this comment.")
        return redirect('comments:single_comment', comment_id=comment.id)
    if request.method == 'POST':
        new_content = request.POST.get('content', '').strip()
        if not new_content:
            messages.error(request, "Comment content cannot be empty.")
            return redirect('comments:edit_comment', comment_id=comment.id)
        comment.edit(new_content, editor=request.user)
        messages.success(request, "Comment updated successfully.")
        return redirect('comments:single_comment', comment_id=comment.id)
    return render(request, 'edit_comment.html', {'comment': comment})


@user_passes_test(is_moderator)
def enhanced_report_list_view(request):
    """Enhanced report list showing grouped reports"""
    
    # Get all report groups
    report_groups = CommentReportGroup.objects.select_related('comment', 'comment__user').all()
    
    # Filtering
    status_filter = request.GET.get('status')
    if status_filter:
        report_groups = report_groups.filter(status=status_filter)
    
    report_type_filter = request.GET.get('report_type')
    if report_type_filter:
        report_groups = report_groups.filter(
            report_types_summary__has_key=report_type_filter
        )
    
    project_filter = request.GET.get('project')
    if project_filter:
        report_groups = report_groups.filter(comment__to_project_id=project_filter)
    
    # Sorting
    sort_by = request.GET.get('sort', '-last_reported_at')
    valid_sorts = ['total_reports', '-total_reports', 'first_reported_at', '-first_reported_at', 
                   'last_reported_at', '-last_reported_at']
    if sort_by in valid_sorts:
        report_groups = report_groups.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(report_groups, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    stats = {
        'total_groups': report_groups.count(),
        'pending_groups': report_groups.filter(status=ReportStatus.PENDING).count(),
        'high_priority': report_groups.filter(total_reports__gte=3).count(),
    }
    
    context = {
        'report_groups': page_obj,
        'stats': stats,
        'statuses': ReportStatus,
        'report_types': ReportType,
        'current_filters': {
            'status': status_filter,
            'report_type': report_type_filter,
            'project': project_filter,
            'sort': sort_by,
        }
    }
    
    return render(request, 'enhanced_report_list.html', context)


@user_passes_test(is_moderator)
def enhanced_report_detail_view(request, comment_id):
    """Enhanced report detail showing all reports for a comment"""
    
    comment = get_object_or_404(Comment, id=comment_id)
    reports = comment.reports.select_related('reportee', 'reported', 'reviewed_by').order_by('-created_at')
    report_group = CommentReportGroup.objects.filter(comment=comment).first()
    
    # Get moderation history
    moderation_history = comment.moderation_actions.select_related('moderator').order_by('-created_at')
    
    if request.method == 'POST':
        form = ModerationActionForm(request.POST, comment=comment, moderator=request.user)
        if form.is_valid():
            action = form.save(commit=False)
            action.moderator = request.user
            action.comment = comment
            
            # Set project context
            if comment.to_project:
                action.project = comment.to_project
            elif comment.to_task and comment.to_task.to_project:
                action.project = comment.to_task.to_project
            elif comment.to_need and comment.to_need.to_project:
                action.project = comment.to_need.to_project
            
            action.save()
            
            # Apply the decision
            try:
                action.apply_decision()
                messages.success(request, f"Moderation action '{action.get_decision_display()}' applied successfully.")
                
                # Update report group
                CommentReportGroup.update_for_comment(comment)
                
                return redirect('comments:enhanced_report_list')
                
            except Exception as e:
                logger.error(f"Error applying moderation decision: {str(e)}")
                messages.error(request, "Error applying moderation decision. Please try again.")
                
    else:
        form = ModerationActionForm(comment=comment, moderator=request.user)
    
    context = {
        'comment': comment,
        'reports': reports,
        'report_group': report_group,
        'moderation_history': moderation_history,
        'form': form,
        'moderator_level': get_moderator_level(request.user),
    }
    
    return render(request, 'enhanced_report_detail.html', context)