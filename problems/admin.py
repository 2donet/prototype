from django.contrib import admin

# Register your models here.
from .models import Problem, ProblemActivity
admin.site.register(Problem)
admin.site.register(ProblemActivity)