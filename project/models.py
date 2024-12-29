from django.db import models

# Create your models here.
class Project(models.Model):
    name = models.CharField(max_length=50)
    summary = models.TextField("summary", blank=True)
    desc = models.TextField("description", blank=True)
    created_by = models.ForeignKey("user.User", on_delete=models.CASCADE)
    # comment = models.ForeignKey("comment.Comment", blank=True, null=True, on_delete=models.CASCADE)


    def __str__(self):
        return self.name