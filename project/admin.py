from django.contrib import admin

# Register your models here.

from project.models import Project, Connection, Membership, Localization
admin.site.register(Project)
admin.site.register(Connection)
admin.site.register(Membership)
admin.site.register(Localization)