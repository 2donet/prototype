from django.db import models

# Create your models here.
class Report(models.Model):
    created_by = models.ForeignKey("user.User", on_delete=models.CASCADE)
    comment = models.ForeignKey("comment.Comment", blank=True, null=True, on_delete=models.CASCADE)


    def __str__(self):
        return self.name

