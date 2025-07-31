from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, authenticate, login
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import Http404, JsonResponse
from django.db.models import Q, Count, Max
from django.utils import timezone
from django.urls import reverse

from .models import Conversation, Message, ConversationParticipant
from .forms import MessageForm, StartConversationForm
from user.forms import SignInForm, SignupForm

User = get_user_model()


@login_required
def conversation_list(request):
    """List all conversations for the current user"""
    sort_by = request.GET.get('sort_by', 'recent')  # recent, oldest, unread
    
    conversations = Conversation.objects.get_user_conversations(request.user)
    
    # Apply sorting
    if sort_by == 'oldest':
        conversations = conversations.order_by('updated_at')
    elif sort_by == 'unread':
        # Sort by unread count (conversations with unread messages first)
        conversations_with_unread = []
        conversations_without_unread = []
        
        for conv in conversations:
            if conv.get_unread_count(request.user) > 0:
                conversations_with_unread.append(conv)
            else:
                conversations_without_unread.append(conv)
        
        conversations = conversations_with_unread + conversations_without_unread
    # 'recent' is default ordering from the manager
    
    # Pagination
    paginator = Paginator(conversations, 20)  # 20 conversations per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Add unread counts and last message for each conversation
    for conversation in page_obj:
        conversation.unread_count = conversation.get_unread_count(request.user)
        conversation.last_message = conversation.get_last_message()
        conversation.other_user = conversation.get_other_participant(request.user)
        
        # Debug: Print to console (remove this after testing)
    
    
    context = {
        'page_obj': page_obj,
        'sort_by': sort_by,
        'total_conversations': paginator.count,
    }
    
    return render(request, 'messaging/conversation_list.html', context)


@login_required
def conversation_detail(request, username):
    """View and send messages in a conversation with a specific user"""
    # Get the other user
    try:
        other_user = User.objects.get(username=username)
    except User.DoesNotExist:
        messages.error(request, f"User '{username}' does not exist.")
        return redirect('messaging:conversation_list')

    if other_user == request.user:
        messages.error(request, "You cannot message yourself.")
        return redirect('messaging:conversation_list')
    
    # Try to get existing conversation (DON'T create one yet)
    conversation = Conversation.objects.filter(
        participants=request.user
    ).filter(
        participants=other_user
    ).filter(
        conversation_type='direct'
    ).first()
    
    # Handle message sending
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            # NOW create the conversation if it doesn't exist (when first message is sent)
            if not conversation:
                conversation = Conversation.objects.create(conversation_type='direct')
                conversation.participants.add(request.user, other_user)
            
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.save()
            
            # Update conversation timestamp
            conversation.updated_at = timezone.now()
            conversation.save(update_fields=['updated_at'])
            
            messages.success(request, "Message sent!")
            return redirect('messaging:conversation_detail', username=username)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = MessageForm()
    
    # If no conversation exists yet, show empty state
    if not conversation:
        context = {
            'conversation': None,
            'other_user': other_user,
            'page_obj': None,
            'form': form,
            'sort_by': 'recent',
            'total_messages': 0,
            'is_new_conversation': True,
        }
        return render(request, 'messaging/conversation_detail.html', context)
    
    # Get messages with pagination (existing conversation)
    sort_by = request.GET.get('sort_by', 'recent')
    
    conversation_messages = conversation.messages.select_related('sender')
    
    if sort_by == 'oldest':
        conversation_messages = conversation_messages.order_by('timestamp')
    else:  # recent (default)
        conversation_messages = conversation_messages.order_by('-timestamp')
    
    # Pagination
    paginator = Paginator(conversation_messages, 50)  # 50 messages per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # If showing recent messages (default), reverse the order for display
    if sort_by != 'oldest':
        page_obj.object_list = list(reversed(page_obj.object_list))
    
    # Mark conversation as read
    try:
        participant = ConversationParticipant.objects.get(
            conversation=conversation, 
            user=request.user
        )
        participant.mark_as_read()
    except ConversationParticipant.DoesNotExist:
        pass
    
    # Add read status to messages
    for message in page_obj.object_list:
        message.read_status = message.get_read_status(request.user)
    
    context = {
        'conversation': conversation,
        'other_user': other_user,
        'page_obj': page_obj,
        'form': form,
        'sort_by': sort_by,
        'total_messages': paginator.count,
        'is_new_conversation': False,
    }
    
    return render(request, 'messaging/conversation_detail.html', context)

@login_required
def start_conversation(request):
    """Start a new conversation with a user"""
    if request.method == 'POST':
        form = StartConversationForm(request.POST)
        if form.is_valid():
            recipient = form.cleaned_data['recipient_username']
            initial_message_content = form.cleaned_data['initial_message']
            
            # Prevent messaging oneself
            if recipient == request.user:
                messages.error(request, "You cannot message yourself.")
                return render(request, 'messaging/start_conversation.html', {'form': form})
            
            # Check if conversation already exists
            existing_conversation = Conversation.objects.filter(
                participants=request.user
            ).filter(
                participants=recipient
            ).filter(
                conversation_type='direct'
            ).first()
            
            # Create conversation only when sending the first message
            if not existing_conversation:
                conversation = Conversation.objects.create(conversation_type='direct')
                conversation.participants.add(request.user, recipient)
            else:
                conversation = existing_conversation
            
            # Create the initial message
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=initial_message_content
            )
            
            # Update conversation timestamp
            conversation.updated_at = timezone.now()
            conversation.save(update_fields=['updated_at'])
            
            messages.success(request, f"Message sent to {recipient.username}!")
            return redirect('messaging:conversation_detail', username=recipient.username)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # Pre-fill recipient if provided in URL
        initial_username = request.GET.get('to', '')
        form = StartConversationForm(initial={'recipient_username': initial_username})
    
    context = {
        'form': form,
    }
    
    return render(request, 'messaging/start_conversation.html', context)


def message_with_user(request, username):
    """
    Handle the /messages/<username>/ URL from profile pages.
    For logged-in users: Redirects to conversation detail.
    For anonymous users: Redirects to auth page.
    """
    try:
        other_user = User.objects.get(username=username)
    except User.DoesNotExist:
        messages.error(request, f"User '{username}' does not exist.")
        if request.user.is_authenticated:
            return redirect('messaging:conversation_list')
        else:
            return redirect('/')
    
    # For anonymous users, redirect to auth page
    if not request.user.is_authenticated:
        return redirect('messaging:auth_required', username=username)
    
    # Prevent messaging oneself
    if other_user == request.user:
        messages.error(request, "You cannot message yourself.")
        return redirect('messaging:conversation_list')
    
    # For logged-in users, go directly to conversation
    return redirect('messaging:conversation_detail', username=username)


def auth_required(request, username):
    """
    Show combined login/register page for messaging a specific user.
    Handle both signin and signup forms on the same page.
    """
    try:
        target_user = User.objects.get(username=username)
    except User.DoesNotExist:
        messages.error(request, f"User '{username}' does not exist.")
        return redirect('/')
    
    # If user is already logged in, redirect to conversation
    if request.user.is_authenticated:
        return redirect('messaging:conversation_detail', username=username)
    
    signin_form = SignInForm()
    signup_form = SignupForm()
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'signin':
            signin_form = SignInForm(request, data=request.POST)
            if signin_form.is_valid():
                username_input = signin_form.cleaned_data.get('username')
                password = signin_form.cleaned_data.get('password')
                
                user = authenticate(username=username_input, password=password)
                if user is not None:
                    login(request, user)
                    
                    # Prevent messaging oneself after login
                    if user == target_user:
                        messages.error(request, "You cannot message yourself.")
                        return redirect('messaging:conversation_list')
                    
                    messages.success(request, f'Welcome back, {user.username}!')
                    return redirect('messaging:conversation_detail', username=target_user.username)
                else:
                    messages.error(request, 'Invalid username or password.')
        
        elif form_type == 'signup':
            signup_form = SignupForm(request.POST)
            if signup_form.is_valid():
                try:
                    user = signup_form.save()
                    login(request, user)
                    
                    # Prevent messaging oneself after signup
                    if user == target_user:
                        messages.error(request, "You cannot message yourself.")
                        return redirect('messaging:conversation_list')
                    
                    messages.success(request, 
                        f'Welcome to 2do.net, {user.username}! Account created successfully.')
                    return redirect('messaging:conversation_detail', username=target_user.username)
                    
                except Exception as e:
                    messages.error(request, 'An error occurred while creating your account. Please try again.')
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"User registration error: {e}")
            else:
                messages.error(request, 'Please correct the errors below.')
    
    context = {
        'target_user': target_user,
        'signin_form': signin_form,
        'signup_form': signup_form,
    }
    
    return render(request, 'messaging/auth_required.html', context)


@login_required
def ajax_mark_read(request, conversation_id):
    """AJAX endpoint to mark conversation as read"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Verify user is participant
        if not conversation.participants.filter(id=request.user.id).exists():
            return JsonResponse({'error': 'Not authorized'}, status=403)
        
        # Mark as read
        participant = ConversationParticipant.objects.get(
            conversation=conversation,
            user=request.user
        )
        participant.mark_as_read()
        
        return JsonResponse({'success': True, 'unread_count': 0})
        
    except ConversationParticipant.DoesNotExist:
        return JsonResponse({'error': 'Participant not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required 
def get_unread_count(request):
    """AJAX endpoint to get total unread message count for navbar"""
    total_unread = 0
    conversations = Conversation.objects.get_user_conversations(request.user)
    
    for conversation in conversations:
        total_unread += conversation.get_unread_count(request.user)
    
    return JsonResponse({'unread_count': total_unread})