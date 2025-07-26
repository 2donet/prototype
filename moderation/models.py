from django.db import models

# Users (including moderation and administration) can report other users' actions and content (e.g., comment)
class Report(models.Model):
    created_by = models.ForeignKey("user.User", on_delete=models.CASCADE)
    comment = models.ForeignKey("comment.Comment", blank=True, null=True, on_delete=models.CASCADE)


    def __str__(self):
        return self.name

