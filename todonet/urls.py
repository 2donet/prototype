from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from plans.views import project_plans  # Import for project-specific plans view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("submissions/", include("submissions.urls")),
    path("comments/", include("comment.urls")),
    path("u/", include("user.urls")),
    path("d/", include("decisions.urls")),
    path("t/", include("task.urls")),
    path("n/", include("need.urls")),
    path("c/", include("contribution.urls")),
    path('', include('skills.urls')),  
    path("plans/", include("plans.urls")),  # Plans app URLs - IMPORTANT: This must be BEFORE project.urls
    path("", include("project.urls")),
    
    # Project-specific plans view (without /p/ prefix as requested)
    path('<int:project_id>/plans/', project_plans, name='project_plans'),
    path("plans/", include("plans.urls")),  # Plans app URLs - IMPORTANT: This must be BEFORE project.urls
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'favicon.ico', permanent=True)),
    path("messages/", include("messaging.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)