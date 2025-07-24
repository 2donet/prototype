from django.core.management.base import BaseCommand
from comment.models import Comment, CommentReportGroup


class Command(BaseCommand):
    help = 'Update all comment report groups'
    
    def handle(self, *args, **options):
        comments_with_reports = Comment.objects.filter(reports__isnull=False).distinct()
        
        updated_count = 0
        for comment in comments_with_reports:
            group = CommentReportGroup.update_for_comment(comment)
            if group:
                updated_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated {updated_count} report groups'
            )
        )