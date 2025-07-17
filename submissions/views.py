# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from submissions.models import Submission
from submissions.forms import SubmissionForm, SubmissionQuickForm
from project.models import Project
from task.models import Task
from need.models import Need


@login_required
def create_submission(request):
    """
    General submission creation view
    """
    if request.method == 'POST':
        print(f"DEBUG: POST data received: {request.POST}")  # Debug line
        form = SubmissionForm(request.POST, user=request.user)
        
        print(f"DEBUG: Form is valid: {form.is_valid()}")  # Debug line
        if not form.is_valid():
            print(f"DEBUG: Form errors: {form.errors}")  # Debug line
            print(f"DEBUG: Form non-field errors: {form.non_field_errors()}")  # Debug line
        
        if form.is_valid():
            try:
                submission = form.save()
                print(f"DEBUG: Submission created with ID: {submission.id}")  # Debug line
                messages.success(request, 'Your submission has been sent successfully!')
                return redirect('submissions:submission_detail', submission.id)
            except Exception as e:
                print(f"DEBUG: Error saving submission: {e}")  # Debug line
                messages.error(request, f'Error saving submission: {e}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SubmissionForm(user=request.user)
    
    return render(request, 'submissions/create.html', {
        'form': form,
        'title': 'Submit Application'
    })


@login_required
def create_submission_for_content(request, content_type, content_id):
    """
    Quick submission for specific content (project/task/need)
    """
    # Get the content object
    if content_type == 'project':
        content_object = get_object_or_404(Project, id=content_id)
    elif content_type == 'task':
        content_object = get_object_or_404(Task, id=content_id)
    elif content_type == 'need':
        content_object = get_object_or_404(Need, id=content_id)
    else:
        messages.error(request, 'Invalid content type')
        return redirect('home')
    
    # Check if user already submitted (for projects/tasks)
    if content_type in ['project', 'task']:
        existing_submission = Submission.objects.filter(
            applicant=request.user,
            **{f'to_{content_type}': content_object}
        ).first()
        
        if existing_submission:
            messages.info(request, f'You have already submitted to this {content_type}.')
            return redirect('submissions:submission_detail', existing_submission.id)
    
    if request.method == 'POST':
        print(f"DEBUG: POST data received: {request.POST}")  # Debug line
        form = SubmissionQuickForm(
            request.POST, 
            user=request.user, 
            content_object=content_object
        )
        
        print(f"DEBUG: Form is valid: {form.is_valid()}")  # Debug line
        if not form.is_valid():
            print(f"DEBUG: Form errors: {form.errors}")  # Debug line
            print(f"DEBUG: Form non-field errors: {form.non_field_errors()}")  # Debug line
        
        if form.is_valid():
            try:
                submission = form.save()
                print(f"DEBUG: Submission created with ID: {submission.id}")  # Debug line
                messages.success(request, 'Your application has been submitted successfully!')
                return redirect('submissions:submission_detail', submission.id)
            except Exception as e:
                print(f"DEBUG: Error saving submission: {e}")  # Debug line
                messages.error(request, f'Error saving submission: {e}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SubmissionQuickForm(user=request.user, content_object=content_object)
    
    return render(request, 'submissions/quick_create.html', {
        'form': form,
        'content_object': content_object,
        'content_type': content_type,
        'title': f'Apply for {content_object.title if hasattr(content_object, "title") else content_object.name}'
    })


def get_content_object_and_submissions(content_type, content_id):
    """
    Helper function to get content object and its related submissions
    Returns: (content_object, submissions_queryset, content_type_name)
    """
    if content_type == 'project':
        content_object = get_object_or_404(Project, id=content_id)
        submissions = Submission.objects.filter(to_project=content_object)
        content_type_name = 'Project'
    elif content_type == 'task':
        content_object = get_object_or_404(Task, id=content_id)
        submissions = Submission.objects.filter(to_task=content_object)
        content_type_name = 'Task'
    elif content_type == 'need':
        content_object = get_object_or_404(Need, id=content_id)
        submissions = Submission.objects.filter(to_need=content_object)
        content_type_name = 'Need'
    else:
        raise ValueError(f"Invalid content type: {content_type}")
    
    return content_object, submissions, content_type_name


@login_required
def submission_list(request, content_type, content_id):
    """
    Display list of submissions for a specific content (project/task/need)
    """
    try:
        content_object, submissions, content_type_name = get_content_object_and_submissions(
            content_type, content_id
        )
    except ValueError as e:
        messages.error(request, str(e))
        return render(request, 'submissions/error.html', {'error': str(e)})
    
    # Check permissions - only content owner or staff can view submissions
    if not (request.user == getattr(content_object, 'creator', None) or 
            request.user == getattr(content_object, 'owner', None) or
            request.user.is_staff):
        messages.error(request, _('You do not have permission to view these submissions.'))
        return render(request, 'submissions/error.html', {'error': 'Permission denied'})
    
    # Get query parameters for filtering
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', '-submitted_at')
    
    # Apply filters
    if status_filter:
        submissions = submissions.filter(status=status_filter)
    
    if search_query:
        submissions = submissions.filter(
            Q(applicant__username__icontains=search_query) |
            Q(applicant__first_name__icontains=search_query) |
            Q(applicant__last_name__icontains=search_query) |
            Q(why_fit__icontains=search_query) |
            Q(additional_info__icontains=search_query)
        )
    
    # Apply sorting
    valid_sort_fields = ['submitted_at', '-submitted_at', 'status', '-status', 
                        'applicant__username', '-applicant__username']
    if sort_by in valid_sort_fields:
        submissions = submissions.order_by(sort_by)
    else:
        submissions = submissions.order_by('-submitted_at')
    
    # Optimize queries
    submissions = submissions.select_related('applicant').prefetch_related('relevant_skills')
    
    # Pagination
    paginator = Paginator(submissions, 10)  # Show 10 submissions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get submission statistics
    stats = {
        'total': submissions.count(),
        'pending': submissions.filter(status='PENDING').count(),
        'reviewed': submissions.filter(status='REVIEWED').count(),
        'accepted': submissions.filter(status='ACCEPTED').count(),
        'rejected': submissions.filter(status='REJECTED').count(),
        'archived': submissions.filter(status='ARCHIVED').count(),
    }
    
    context = {
        'content_object': content_object,
        'content_type': content_type,
        'content_type_name': content_type_name,
        'submissions': page_obj,
        'stats': stats,
        'status_choices': Submission.STATUS_CHOICES,
        'current_status_filter': status_filter,
        'current_search': search_query,
        'current_sort': sort_by,
    }
    
    return render(request, 'submissions/list.html', context)


@login_required
def update_submission_status(request, submission_id):
    """
    AJAX endpoint to update submission status
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    submission = get_object_or_404(Submission, id=submission_id)
    new_status = request.POST.get('status')
    
    # Check permissions
    content_object = submission.to_project or submission.to_task or submission.to_need
    if not (request.user == getattr(content_object, 'creator', None) or 
            request.user == getattr(content_object, 'owner', None) or
            request.user.is_staff):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Validate status
    valid_statuses = [choice[0] for choice in Submission.STATUS_CHOICES]
    if new_status not in valid_statuses:
        return JsonResponse({'error': 'Invalid status'}, status=400)
    
    # Update status
    old_status = submission.status
    submission.status = new_status
    submission.save()
    
    return JsonResponse({
        'success': True,
        'old_status': old_status,
        'new_status': new_status,
        'message': f'Status updated to {new_status}'
    })


@login_required
def submission_detail(request, submission_id):
    """
    Enhanced submission detail view with more information
    """
    submission = get_object_or_404(
        Submission.objects.select_related('applicant').prefetch_related('relevant_skills'),
        id=submission_id
    )
    
    # Check permissions
    content_object = submission.to_project or submission.to_task or submission.to_need
    if not (request.user == getattr(content_object, 'creator', None) or 
            request.user == getattr(content_object, 'owner', None) or
            request.user.is_staff or
            request.user == submission.applicant):
        messages.error(request, _('You do not have permission to view this submission.'))
        return render(request, 'submissions/error.html', {'error': 'Permission denied'})
    
    # Determine content type for context
    if submission.to_project:
        content_type = 'project'
        content_type_name = 'Project'
    elif submission.to_task:
        content_type = 'task'
        content_type_name = 'Task'
    else:
        content_type = 'need'
        content_type_name = 'Need'
    
    context = {
        'submission': submission,
        'content_object': content_object,
        'content_type': content_type,
        'content_type_name': content_type_name,
        'status_choices': Submission.STATUS_CHOICES,
        'can_edit': request.user == getattr(content_object, 'creator', None) or 
                   request.user == getattr(content_object, 'owner', None) or
                   request.user.is_staff,
    }
    
    return render(request, 'submissions/detail.html', context)