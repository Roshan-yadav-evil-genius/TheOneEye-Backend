from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.http import FileResponse, Http404

# Serve node icons - defined BEFORE main urlpatterns to ensure it takes priority
NODES_STATIC_ROOT = settings.BASE_DIR.parent / 'core' / 'Node' / 'Nodes'

def serve_node_icon(request, icon_path):
    """Serve node icon files from core/Node/Nodes directory."""
    file_path = NODES_STATIC_ROOT / icon_path
    if file_path.exists() and file_path.is_file():
        # Determine content type based on extension
        suffix = file_path.suffix.lower()
        content_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
        }
        content_type = content_types.get(suffix, 'application/octet-stream')
        return FileResponse(open(file_path, 'rb'), content_type=content_type)
    raise Http404(f"Icon not found: {icon_path}")

urlpatterns = [
    # Node icons FIRST - use 'node-icons' path to avoid conflict with Django's static handling
    path("node-icons/<path:icon_path>", serve_node_icon, name='node-icon'),
    path("admin/", admin.site.urls),
    path("api/",include("workflow.urls")),
    path("api/", include("browsersession.urls")),
    path("api/auth/", include("authentication.urls")),
    path("api/contact/", include("contact.urls")),
    path("api/nodes/", include("nodes.urls")),
    
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
