from django.shortcuts import render, get_object_or_404
from decisions.models import Decision
from comment.models import Comment

def decision_details(request, decision_id):
    decision = get_object_or_404(Decision, id=decision_id)
    comments = Comment.objects.filter(to_decision=decision).all()  # Comments related to this decision

    context = {
        'decision': decision,
        'comments': comments,
    }
    return render(request, 'decision_details.html', context)
