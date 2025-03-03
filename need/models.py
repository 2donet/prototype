from django.db import models

# Create your models here.
class Need(models.Model):
    name = models.CharField(max_length=50)
    desc = models.TextField("description")
    priority = models.IntegerField(default=0, null=False, blank=True)
    created_by = models.ForeignKey("user.User", on_delete=models.CASCADE)

    to_project = models.ForeignKey("project.Project", blank=True, null=True, on_delete=models.CASCADE)
    to_task = models.ForeignKey("task.Task", blank=True, null=True, on_delete=models.CASCADE)



    def __str__(self):
        return self.name

