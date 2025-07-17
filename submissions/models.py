from django.db import models
from django.conf import settings
from skills.models import Skill
from project.models import Project
from task.models import Task
from need.models import Need
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone


class Submission(models.Model):
    applicant = models.ForeignKey(
        'auth.User', on_delete=models.CASCADE, related_name='submissions'
    )
    to_project = models.ForeignKey(
        'project.Project', null=True, blank=True, on_delete=models.CASCADE
    )
    to_task = models.ForeignKey(
        'task.Task', null=True, blank=True, on_delete=models.CASCADE
    )
    to_need = models.ForeignKey(
        'need.Need', null=True, blank=True, on_delete=models.CASCADE
    )
    why_fit = models.TextField(blank=True, null=True)
    relevant_skills = models.ManyToManyField('skills.Skill', blank=True)
    additional_info = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('REVIEWED', 'Reviewed'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('ARCHIVED', 'Archived'),
    ]
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')

    class Meta:
        unique_together = (('applicant', 'to_project'), ('applicant', 'to_task'))

    def clean(self):
        if not self.to_project and not self.to_task and not self.to_need:
            raise ValidationError('A submission must be linked to either a project, task or need.')
        # TBD: should submission to a project, task, or need be mutually exclusive?
        if self.to_project and self.to_task:
            raise ValidationError('A submission cannot be linked to both a project and a task.')
    def __str__(self):
        return f"{self.applicant.username} - {self.to_project or self.to_task}"
