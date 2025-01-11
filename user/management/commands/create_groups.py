from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = 'Create predefined groups: Normal and Admin'

    def handle(self, *args, **kwargs):
        # List of group names to ensure exist
        groups = ['Normal', 'Admin']

        for group_name in groups:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Group "{group_name}" created successfully.'))
            else:
                self.stdout.write(self.style.WARNING(f'Group "{group_name}" already exists.'))

        self.stdout.write(self.style.SUCCESS('Predefined groups ensured.'))