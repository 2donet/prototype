from django.shortcuts import render
from submissions.models import Submission

# Create your views here.
def submission_detail(request, submission_id):
    # Logic to retrieve and display submission details
    submission = Submission.objects.get(id=submission_id)
    return render(request, 'submissions/submission_detail.html', {'submission': submission})