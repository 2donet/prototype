from django.contrib import admin

# Register your models here.
from contribution.models import Contribution, Review
admin.site.register(Contribution)
admin.site.register(Review)