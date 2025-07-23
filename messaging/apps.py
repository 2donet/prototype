from django.apps import AppConfig


class MessagesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'messaging'
    verbose_name = 'messaging'
    
    def ready(self):
        # Import signals if you add any in the future
        pass
