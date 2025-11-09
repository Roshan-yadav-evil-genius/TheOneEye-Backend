from django.contrib import admin
from django.urls import include, path
from django.conf.urls.static import static

from theoneeye import settings

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/",include("workflow.urls")),
    path("api/", include("browsersession.urls")),
    path("api/auth/", include("authentication.urls")),
    path("api/contact/", include("contact.urls")),
    
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
