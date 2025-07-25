from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from submissions.models import Submission
from submissions.forms import SubmissionForm, SubmissionQuickForm
from project.models import Project
from task.models import Task
from need.models import Need
from skills.models import Skill
from messaging.models import Conversation


@login_required
def create_submission(request):
    """
    General submission creation view (not linked to specific content)
    """
    if request.method == 'POST':
        form = SubmissionForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                submission = form.save()
                messages.success(request, 'Your submission has been sent successfully!')
                return redirect('submissions:submission_detail', submission.id)
            except Exception as e:
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
    print(f"DEBUG: create_submission_for_content called with content_type={content_type}, content_id={content_id}")
    
    # Get the content object
    try:
        if content_type == 'project':
            content_object = get_object_or_404(Project, id=content_id)
        elif content_type == 'task':
            content_object = get_object_or_404(Task, id=content_id)
        elif content_type == 'need':
            content_object = get_object_or_404(Need, id=content_id)
        else:
            messages.error(request, 'Invalid content type')
            return redirect('home')
        
        print(f"DEBUG: Found content object: {content_object}")
    except Exception as e:
        print(f"DEBUG: Error getting content object: {e}")
        messages.error(request, f'Content not found: {e}')
        return redirect('home')
    
    # Check if user already submitted (for projects/tasks)
    if content_type in ['project', 'task']:
        try:
            existing_submission = Submission.objects.filter(
                applicant=request.user,
                **{f'to_{content_type}': content_object}
            ).first()
            
            if existing_submission:
                messages.info(request, f'You have already submitted to this {content_type}.')
                return redirect('submissions:submission_detail', existing_submission.id)
        except Exception as e:
            print(f"DEBUG: Error checking existing submission: {e}")
    
    if request.method == 'POST':
        print(f"DEBUG: POST data received: {dict(request.POST)}")
        
        # Get form data
        why_fit = request.POST.get('why_fit', '').strip()
        additional_info = request.POST.get('additional_info', '').strip()
        skills_json = request.POST.get('skills')  # This will be JSON from the chips input
        
        print(f"DEBUG: Form data - why_fit: '{why_fit}', additional_info: '{additional_info}', skills_json: {skills_json}")
        
        try:
            # Create submission directly
            submission = Submission(
                applicant=request.user,
                why_fit=why_fit or None,
                additional_info=additional_info or None
            )
            
            # Set the content object
            if content_type == 'project':
                submission.to_project = content_object
            elif content_type == 'task':
                submission.to_task = content_object
            elif content_type == 'need':
                submission.to_need = content_object
            
            print(f"DEBUG: Created submission object with content assigned")
            
            # Validate and save
            submission.full_clean()
            submission.save()
            
            print(f"DEBUG: Submission saved with ID: {submission.id}")
            
            # Handle skills similar to project creation
            if skills_json:
                try:
                    skill_names = json.loads(skills_json)
                    if skill_names:
                        skills = []
                        for skill_name in skill_names:
                            skill = Skill.get_or_create_skill(skill_name.strip())
                            skills.append(skill)
                        submission.relevant_skills.set(skills)
                        print(f"DEBUG: Added {len(skills)} skills to submission")
                except (json.JSONDecodeError, Exception) as e:
                    print(f"DEBUG: Error processing skills: {e}")
            
            messages.success(request, 'Your application has been submitted successfully!')
            return redirect('submissions:submission_detail', submission.id)
            
        except Exception as e:
            print(f"DEBUG: Error creating submission: {e}")
            import traceback
            traceback.print_exc()
            messages.error(request, f'Error saving submission: {e}')
    
    # For GET request, create a simple form for display
    form_data = {
        'why_fit': '',
        'additional_info': '',
        'skills': []
    }
    
    return render(request, 'submissions/quick_create.html', {
        'content_object': content_object,
        'content_type': content_type,
        'title': f'Apply for {content_object.title if hasattr(content_object, "title") else content_object.name}',
        'form_data': form_data,
    })


def get_content_object_and_submissions(content_type, content_id):
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


def user_can_manage_submissions(user, content_object):
    """Check if user can manage submissions for the given content object"""
    if user.is_superuser or user.is_staff:
        return True
    
    # Check if user is the creator/owner of the content
    if hasattr(content_object, 'created_by') and content_object.created_by == user:
        return True
    if hasattr(content_object, 'creator') and content_object.creator == user:
        return True
    if hasattr(content_object, 'owner') and content_object.owner == user:
        return True
    
    # For projects, check if user is admin or moderator
    if hasattr(content_object, 'membership_set'):
        from project.models import Membership
        return Membership.objects.filter(
            project=content_object,
            user=user,
            is_administrator=True
        ).exists() or Membership.objects.filter(
            project=content_object,
            user=user,
            is_moderator=True
        ).exists()
    
    return False


@login_required
def submission_list(request, content_type, content_id):
    try:
        content_object, submissions, content_type_name = get_content_object_and_submissions(content_type, content_id)
    except ValueError as e:
        messages.error(request, str(e))
        return render(request, 'submissions/error.html', {'error': str(e)})

    # Check permissions using the new function
    if not user_can_manage_submissions(request.user, content_object):
        messages.error(request, _('You do not have permission to view these submissions.'))
        return render(request, 'submissions/error.html', {'error': 'Permission denied'})

    # Filtering and sorting
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', '-submitted_at')

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

    valid_sort_fields = ['submitted_at', '-submitted_at', 'status', '-status',
                         'applicant__username', '-applicant__username']
    if sort_by in valid_sort_fields:
        submissions = submissions.order_by(sort_by)
    else:
        submissions = submissions.order_by('-submitted_at')

    submissions = submissions.select_related('applicant').prefetch_related('relevant_skills', 'conversations')

    paginator = Paginator(submissions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Add conversation info for each submission
    for submission in page_obj:
        # Get the submission conversation (there should only be one per submission)
        conversation = submission.conversations.first()
        submission.conversation = conversation
        
        # Check if current user can access this conversation
        if conversation:
            # For admins: show conversation even if not a participant yet
            # For participants: show if they're a participant
            if user_can_manage_submissions(request.user, submission.to_project or submission.to_task or submission.to_need):
                # Admin can see conversation
                if conversation.participants.filter(id=request.user.id).exists():
                    submission.unread_count = conversation.get_unread_count(request.user)
                else:
                    submission.unread_count = 0  # Admin can see but no unread count if not participant
            elif conversation.participants.filter(id=request.user.id).exists():
                # User is a participant (submitee)
                submission.unread_count = conversation.get_unread_count(request.user)
            else:
                # User cannot access this conversation
                submission.conversation = None
                submission.unread_count = 0
        else:
            submission.unread_count = 0

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
@require_http_methods(["POST"])
@csrf_exempt  # We'll handle CSRF manually in the AJAX request
def update_submission_status(request, submission_id):
    """AJAX endpoint for updating submission status"""
    try:
        submission = get_object_or_404(Submission, id=submission_id)
        content_object = submission.to_project or submission.to_task or submission.to_need
        
        # Check permissions
        if not user_can_manage_submissions(request.user, content_object):
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

        # Get new status from request
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            new_status = data.get('status')
        else:
            new_status = request.POST.get('status')

        if not new_status:
            return JsonResponse({'success': False, 'error': 'Status is required'}, status=400)

        # Validate status
        valid_statuses = [choice[0] for choice in Submission.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)

        # Update the status
        old_status = submission.status
        submission.status = new_status
        submission.save(update_fields=['status'])

        # Log the change
        print(f"Status updated for submission {submission_id}: {old_status} -> {new_status}")

        return JsonResponse({
            'success': True,
            'old_status': old_status,
            'new_status': new_status,
            'status_display': submission.get_status_display(),
            'message': f'Status updated to {submission.get_status_display()}'
        })

    except Exception as e:
        print(f"Error updating submission status: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
@login_required
def submission_detail(request, submission_id):
    submission = get_object_or_404(
        Submission.objects.select_related('applicant').prefetch_related('relevant_skills', 'conversations'),
        id=submission_id
    )

    content_object = submission.to_project or submission.to_task or submission.to_need
    
    # Check if user can view this submission
    can_manage = user_can_manage_submissions(request.user, content_object)
    is_applicant = request.user == submission.applicant
    
    if not (can_manage or is_applicant):
        # Don't show error message on submission detail - redirect to appropriate page
        if is_applicant:
            return redirect('messaging:conversation_list')
        else:
            return redirect('submissions:submission_list', content_type, content_object.id)

    if submission.to_project:
        content_type = 'project'
        content_type_name = 'Project'
    elif submission.to_task:
        content_type = 'task'
        content_type_name = 'Task'
    else:
        content_type = 'need'
        content_type_name = 'Need'

    # Get conversation info - find submission conversation
    conversation = submission.conversations.first()  # There should only be one per submission
    
    # Check if current user should have access to the conversation
    user_can_access_conversation = False
    user_is_participant = False
    if conversation:
        user_is_participant = conversation.participants.filter(id=request.user.id).exists()
        if is_applicant or can_manage:
            # Both submitees and admins can access conversations
            user_can_access_conversation = True
    else:
        # If no conversation exists yet, both submitees and admins should be able to start one
        if is_applicant or can_manage:
            user_can_access_conversation = True
    
    unread_count = 0
    if conversation and user_is_participant:
        unread_count = conversation.get_unread_count(request.user)

    # Handle message sending
    from messaging.forms import MessageForm
    message_form = MessageForm()
    
    if request.method == 'POST' and request.POST.get('action') == 'send_message':
        message_form = MessageForm(request.POST)
        if message_form.is_valid():
            # Check if user has permission to participate
            if not (can_manage or is_applicant):
                messages.error(request, "You don't have permission to send messages for this submission.")
                return redirect('submissions:submission_detail', submission_id)
            
            # For admins, verify they still have permission to manage this submission
            if can_manage and not user_can_manage_submissions(request.user, content_object):
                messages.error(request, "You no longer have permission to manage this submission.")
                return redirect('submissions:submission_detail', submission_id)
            
            try:
                # Create or get conversation
                if not conversation:
                    from messaging.models import Conversation
                    if can_manage:
                        # Admin starting conversation
                        conversation = Conversation.objects.get_or_create_submission_conversation(
                            request.user, submission.applicant, submission
                        )
                        user_is_participant = True
                    elif is_applicant:
                        # Submitee starting conversation - find appropriate admin to message
                        admin_user = None
                        
                        if submission.to_project:
                            # For project submissions, find project admins/moderators
                            from project.models import Membership
                            project_admin = Membership.objects.filter(
                                project=submission.to_project,
                                is_administrator=True
                            ).select_related('user').first()
                            
                            admin_user = project_admin.user if project_admin else submission.to_project.created_by
                            
                        elif submission.to_task and hasattr(submission.to_task, 'to_project') and submission.to_task.to_project:
                            # For task submissions, message project admin or task creator
                            from project.models import Membership
                            project_admin = Membership.objects.filter(
                                project=submission.to_task.to_project,
                                is_administrator=True
                            ).select_related('user').first()
                            
                            admin_user = project_admin.user if project_admin else submission.to_task.to_project.created_by
                            
                        elif submission.to_need and hasattr(submission.to_need, 'to_project') and submission.to_need.to_project:
                            # For need submissions, message project admin or need creator
                            from project.models import Membership
                            project_admin = Membership.objects.filter(
                                project=submission.to_need.to_project,
                                is_administrator=True
                            ).select_related('user').first()
                            
                            admin_user = project_admin.user if project_admin else submission.to_need.to_project.created_by
                        else:
                            # Fallback to content creator
                            admin_user = (submission.to_task.created_by if submission.to_task 
                                        else submission.to_need.created_by if submission.to_need
                                        else submission.to_project.created_by if submission.to_project
                                        else None)
                        
                        if not admin_user:
                            messages.error(request, "Unable to find an administrator to message. Please try again later.")
                            return redirect('submissions:submission_detail', submission_id)
                        
                        conversation = Conversation.objects.get_or_create_submission_conversation(
                            admin_user, submission.applicant, submission
                        )
                        user_is_participant = True
                    else:
                        messages.error(request, "You don't have permission to start a conversation for this submission.")
                        return redirect('submissions:submission_detail', submission_id)
                else:
                    # For existing conversation, ensure user is a participant
                    if can_manage and not user_is_participant:
                        # Add admin as participant if they have permissions
                        if user_can_manage_submissions(request.user, content_object):
                            conversation.participants.add(request.user)
                            user_is_participant = True
                            
                            # Create ConversationParticipant record
                            from messaging.models import ConversationParticipant
                            from django.utils import timezone
                            ConversationParticipant.objects.get_or_create(
                                conversation=conversation,
                                user=request.user,
                                defaults={'joined_at': timezone.now()}
                            )
                        else:
                            messages.error(request, "You don't have permission to join this conversation.")
                            return redirect('submissions:submission_detail', submission_id)
                    elif not user_is_participant:
                        messages.error(request, "You're not a participant in this conversation.")
                        return redirect('submissions:submission_detail', submission_id)
                
                # Create message
                from messaging.models import Message
                message = message_form.save(commit=False)
                message.conversation = conversation
                message.sender = request.user
                message.save()
                
                # Update conversation timestamp
                from django.utils import timezone
                conversation.updated_at = timezone.now()
                conversation.save(update_fields=['updated_at'])
                
                messages.success(request, "Message sent successfully!")
                return redirect('submissions:submission_detail', submission_id)
                
            except Exception as e:
                print(f"DEBUG: Error sending message: {e}")
                import traceback
                traceback.print_exc()
                messages.error(request, "There was an error sending your message. Please try again.")
                return redirect('submissions:submission_detail', submission_id)
        # Don't show error messages for form validation - just let the form show the errors

    # Get messages with pagination - show to all who can access
    conversation_messages = None
    if conversation and user_can_access_conversation:
        sort_by = request.GET.get('sort_by', 'recent')
        
        conversation_messages = conversation.messages.select_related('sender')
        
        if sort_by == 'oldest':
            conversation_messages = conversation_messages.order_by('timestamp')
        else:  # recent (default)
            conversation_messages = conversation_messages.order_by('-timestamp')
        
        # Pagination
        from django.core.paginator import Paginator
        paginator = Paginator(conversation_messages, 20)  # 20 messages per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # If showing recent messages (default), reverse the order for display
        if sort_by != 'oldest':
            page_obj.object_list = list(reversed(page_obj.object_list))
        
        # Add message type info for template
        for message in page_obj.object_list:
            message.is_from_current_user = (message.sender == request.user)
            message.is_from_applicant = (message.sender == submission.applicant)
            message.is_from_other_admin = (not message.is_from_current_user and not message.is_from_applicant)
        
        conversation_messages = page_obj
        
        # Mark conversation as read (only if user is a participant)
        if user_is_participant:
            try:
                from messaging.models import ConversationParticipant
                participant = ConversationParticipant.objects.get(
                    conversation=conversation, 
                    user=request.user
                )
                participant.mark_as_read()
                unread_count = 0  # Reset since we just marked as read
            except ConversationParticipant.DoesNotExist:
                pass

    context = {
        'submission': submission,
        'content_object': content_object,
        'content_type': content_type,
        'content_type_name': content_type_name,
        'status_choices': Submission.STATUS_CHOICES,
        'can_edit': can_manage,
        'can_manage': can_manage,
        'is_applicant': is_applicant,
        'conversation': conversation,
        'unread_count': unread_count,
        'messages': conversation_messages,
        'message_form': message_form,
        'sort_by': request.GET.get('sort_by', 'recent'),
        'user_can_access_conversation': user_can_access_conversation,
        'user_is_participant': user_is_participant,
    }

    return render(request, 'submissions/detail.html', context)