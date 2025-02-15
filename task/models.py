from django.db import models

# Create your models here.
class Task(models.Model):
    name = models.CharField(max_length=50)
    desc = models.TextField("description")
    priority = models.IntegerField(null=True)
    created_by = models.ForeignKey("user.User", on_delete=models.CASCADE)
    
    contributions = models.JSONField(
        null=True
    ) 

    to_project = models.ForeignKey("project.Project", blank=True, null=True, on_delete=models.CASCADE)
    to_task = models.ForeignKey("task.Task", blank=True, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.name