from django.apps import AppConfig


class TrackerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tracker"

    def ready(self):
        """Configure admin site styling on app ready"""
        from django.contrib import admin
        
        # Customize admin site
        admin.site.site_header = "BossIn Finance Tracker"
        admin.site.site_title = "BossIn Admin"
        admin.site.index_title = "Welcome to BossIn Administration"
