from django.contrib import admin

# Register your models here.

from project.models import Project, Connection
admin.site.register(Project)
admin.site.register(Connection)