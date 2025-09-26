from django.contrib import admin
from django.urls import include, path
from django.conf.urls.static import static

from theoneeye import settings

urlpatterns = [
    path("",include("portal.urls")),
    path("admin/", admin.site.urls),
    path("api/",include("workflow.urls")),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
