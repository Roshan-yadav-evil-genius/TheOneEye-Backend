from django.contrib import admin
from browsersession.models import BrowserSession


@admin.register(BrowserSession)
class BrowserSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'browser_type', 'status', 'created_by', 'created_at', 'updated_at']
    list_filter = ['browser_type', 'status', 'created_at', 'updated_at']
    search_fields = ['name', 'description', 'created_by']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fields = ['id', 'name', 'description', 'browser_type', 'playwright_config', 'status', 'created_by', 'created_at', 'updated_at']
    ordering = ['-created_at']
