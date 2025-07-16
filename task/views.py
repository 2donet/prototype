from django.shortcuts import get_object_or_404, render
from django.db.models import Prefetch
from comment.models import Comment, CommentVote, CommentReaction, ReactionType
from task.models import Task

def task_detail(request, task_id):
    """
    Display details of a specific task, including its comments and replies.
    """
    task = get_object_or_404(Task, pk=task_id)
    
    # Fetch top-level comments with all necessary relations
    comments = Comment.objects.filter(
        to_task=task_id, 
        parent__isnull=True
    ).select_related('user').prefetch_related(
        Prefetch('replies', queryset=Comment.objects.select_related('user')),
        'votes',
        'reactions'
    )
    
    # Add reaction counts and user vote/reaction status to comments
    for comment in comments:
        # Get reaction counts
        comment.reaction_counts = comment.get_reaction_counts()
        
        # If user is authenticated, get their vote and reactions
        if request.user.is_authenticated:
            # Check for user vote
            user_vote = comment.votes.filter(user=request.user).first()
            comment.user_vote = user_vote.vote_type if user_vote else None
            
            # Get user reactions
            user_reactions = comment.reactions.filter(user=request.user).values_list('reaction_type', flat=True)
            comment.user_reactions = list(user_reactions)
        else:
            comment.user_vote = None
            comment.user_reactions = []
        
        # Also process replies
        for reply in comment.replies.all():
            reply.reaction_counts = reply.get_reaction_counts()
            
            if request.user.is_authenticated:
                reply_vote = reply.votes.filter(user=request.user).first()
                reply.user_vote = reply_vote.vote_type if reply_vote else None
                
                reply_reactions = reply.reactions.filter(user=request.user).values_list('reaction_type', flat=True)
                reply.user_reactions = list(reply_reactions)
            else:
                reply.user_vote = None
                reply.user_reactions = []
    
    context = {
        "task": task,
        "comments": comments,
    }
    return render(request, "task_detail.html", context=context)

def task_list(request):
    """
    Display a list of all tasks.
    """
    tasks = Task.objects.all().select_related('created_by', 'to_project')
    context = {
        "tasks": tasks,
    }
    return render(request, "task_list.html", context=context)