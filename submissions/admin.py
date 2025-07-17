from django.contrib import admin

# Register your models here.

from submissions.models import Submission
admin.site.register(Submission)
