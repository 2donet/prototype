from django.db import models
from django.conf import settings
# Create your models here.
class Intro(models.Model):
    name = models.CharField(max_length=200)
    summary = models.CharField(max_length=500)
    desc = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    to_task = models.ForeignKey(
        'task.Task', 
        on_delete=models.CASCADE, 
        related_name='intros', 
        null=True, 
        blank=True
    )
    to_project = models.ForeignKey(
        'project.Project', 
        on_delete=models.CASCADE, 
        related_name='intros', 
        null=True,
        blank=True
    )
    to_need = models.ForeignKey(
        'need.Need', 
        on_delete=models.CASCADE, 
        related_name='intros', 
        null=True, 
        blank=True
    )
    to_problem = models.ForeignKey(
        'problems.Problem', 
        on_delete=models.CASCADE, 
        related_name='intros', 
        null=True, 
        blank=True
    )
    to_plan = models.ForeignKey(
        'plans.Plan', 
        on_delete=models.CASCADE, 
        related_name='intros', 
        null=True, 
        blank=True
    )
    by_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class StatusChoices(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        REJECTED = 'rejected', 'Rejected'
        PUBLISHED = 'published', 'Published'
        ARCHIVED = 'archived', 'Archived'
    status = models.CharField(
        max_length=10,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
        help_text="Status of the intro"
    )
    main_project = models.ForeignKey(
        'project.Project', 
        on_delete=models.CASCADE, 
        related_name='related_intros', 
        null=True, 
        blank=True
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Intro"
        verbose_name_plural = "Intros"
        ordering = ['-created_at']  # Order by creation date, newest first