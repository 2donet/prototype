from django.db import models
from django.conf import settings
# Create your models here.
class Report(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, db_index=True
    )
    comment = models.ForeignKey("comment.Comment", blank=True, null=True, on_delete=models.CASCADE)


    def __str__(self):
        return self.name

