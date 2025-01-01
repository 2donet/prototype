from django.contrib import admin

# Register your models here.
from task.models import Task
admin.site.register(Task)