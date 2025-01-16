from django.contrib import admin

# Register your models here.
from user.models import User, Person, Group, Membership, UserProfile
admin.site.register(User)
admin.site.register(Person)
admin.site.register(Group)
admin.site.register(Membership)

admin.site.register(UserProfile)
