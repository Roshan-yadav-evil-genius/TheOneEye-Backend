from django.contrib import admin
from .models import APIKey


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('name', 'prefix', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'prefix', 'user__username')
    readonly_fields = ('id', 'prefix', 'key_hash', 'created_at')
