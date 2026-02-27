from django.contrib import admin
from apps.browsersession.models import (
    BrowserSession,
    BrowserPool,
    BrowserPoolSession,
    BrowserPoolSessionDomainUsage,
    PoolDomainThrottleRule,
)


@admin.register(BrowserSession)
class BrowserSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'browser_type', 'status', 'created_by', 'created_at', 'updated_at']
    list_filter = ['browser_type', 'status', 'created_at', 'updated_at']
    search_fields = ['name', 'description', 'created_by']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fields = ['id', 'name', 'description', 'browser_type', 'playwright_config', 'status', 'created_by', 'created_at', 'updated_at']
    ordering = ['-created_at']


class BrowserPoolSessionInline(admin.TabularInline):
    model = BrowserPoolSession
    extra = 0


class PoolDomainThrottleRuleInline(admin.TabularInline):
    model = PoolDomainThrottleRule
    extra = 0


@admin.register(BrowserPool)
class BrowserPoolAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'domain_throttle_enabled', 'resource_blocking_enabled', 'created_at', 'updated_at']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [BrowserPoolSessionInline, PoolDomainThrottleRuleInline]
    ordering = ['-created_at']
    fields = ['id', 'name', 'description', 'domain_throttle_enabled', 'resource_blocking_enabled', 'blocked_resource_types', 'created_at', 'updated_at']


@admin.register(PoolDomainThrottleRule)
class PoolDomainThrottleRuleAdmin(admin.ModelAdmin):
    list_display = ['id', 'pool', 'domain', 'delay_seconds', 'enabled', 'created_at']
    list_filter = ['pool', 'enabled']
    search_fields = ['domain']
    ordering = ['pool', 'domain']


@admin.register(BrowserPoolSession)
class BrowserPoolSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'pool', 'session', 'usage_count']
    list_filter = ['pool']
    ordering = ['pool', 'usage_count']


@admin.register(BrowserPoolSessionDomainUsage)
class BrowserPoolSessionDomainUsageAdmin(admin.ModelAdmin):
    list_display = ['id', 'pool', 'session', 'domain', 'usage_count']
    list_filter = ['pool', 'domain']
    ordering = ['pool', 'domain', 'usage_count']
