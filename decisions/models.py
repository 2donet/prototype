from django.db import models
from user.models import Membership

class Decision(models.Model):
    SOURCE_CHOICES = [
        ('portal', 'Portal Administration'),
        ('administration', 'Administration'),
        ('voting', 'Voting'),
        ('role', 'Role'),
        ('auto', 'Auto'),
    ]
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="decisions")
    title = models.CharField(max_length=128)
    description = models.TextField()
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    date_made = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Decision: {self.title} ({self.get_source_display()})"
