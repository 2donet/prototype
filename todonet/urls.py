"""
URL configuration for todonet project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
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
    path("", include("project.urls")),
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'favicon.ico', permanent=True)),
    path("messages/", include("messaging.urls")),
    # path("project_constructor/", include("project_constructor.urls")),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)