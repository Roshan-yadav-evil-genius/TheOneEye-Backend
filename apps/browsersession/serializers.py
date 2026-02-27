from rest_framework import serializers
from apps.browsersession.models import BrowserSession, BrowserPool, BrowserPoolSession, PoolDomainThrottleRule

ALLOWED_RESOURCE_TYPES = frozenset({
    "document", "stylesheet", "image", "media", "font", "script",
    "texttrack", "xhr", "fetch", "eventsource", "websocket", "manifest", "other",
})


class BrowserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrowserSession
        fields = [
            "id", "name", "description", "browser_type",
            "playwright_config", "status", "created_by",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

class BrowserSessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrowserSession
        fields = [
            'name', 'description', 'browser_type', 
            'playwright_config', 'status', 'created_by'
        ]
    
    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Name is required")
        return value.strip()
    
    def validate_description(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Description is required")
        return value.strip()

class BrowserSessionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrowserSession
        fields = [
            "id", "name", "description", "browser_type",
            "playwright_config", "status", "created_by",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Name is required")
        return value.strip()

    def validate_description(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Description is required")
        return value.strip()


class BrowserPoolSerializer(serializers.ModelSerializer):
    session_ids = serializers.SerializerMethodField()

    class Meta:
        model = BrowserPool
        fields = [
            "id", "name", "description", "session_ids",
            "domain_throttle_enabled", "resource_blocking_enabled", "blocked_resource_types",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_session_ids(self, obj):
        return [str(ps.session_id) for ps in obj.pool_sessions.all().order_by("usage_count")]


class BrowserPoolCreateSerializer(serializers.Serializer):
    """Create a pool; at least one session is required."""
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(allow_blank=True, allow_null=True, required=False, default=None)
    session_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    domain_throttle_enabled = serializers.BooleanField(required=False, default=True)
    resource_blocking_enabled = serializers.BooleanField(required=False, default=False)
    blocked_resource_types = serializers.ListField(child=serializers.CharField(), required=False, default=list)

    def validate_blocked_resource_types(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("blocked_resource_types must be a list")
        for item in value:
            if not isinstance(item, str) or item not in ALLOWED_RESOURCE_TYPES:
                raise serializers.ValidationError(
                    f"Each item must be one of: {sorted(ALLOWED_RESOURCE_TYPES)}"
                )
        return value

    def validate_session_ids(self, value):
        if not value or len(value) < 1:
            raise serializers.ValidationError("At least one session is required in the pool.")
        return value

    def create(self, validated_data):
        session_ids = validated_data.pop("session_ids")
        pool = BrowserPool.objects.create(
            name=validated_data["name"],
            description=validated_data.get("description"),
            domain_throttle_enabled=validated_data.get("domain_throttle_enabled", True),
            resource_blocking_enabled=validated_data.get("resource_blocking_enabled", False),
            blocked_resource_types=validated_data.get("blocked_resource_types", []),
        )
        for sid in session_ids:
            BrowserPoolSession.objects.create(pool=pool, session_id=sid)
        return pool


class BrowserPoolUpdateSerializer(serializers.Serializer):
    """Update a pool; when session_ids is provided, at least one session is required."""
    name = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    session_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    domain_throttle_enabled = serializers.BooleanField(required=False)
    resource_blocking_enabled = serializers.BooleanField(required=False)
    blocked_resource_types = serializers.ListField(child=serializers.CharField(), required=False)

    def validate_session_ids(self, value):
        if value is not None and len(value) < 1:
            raise serializers.ValidationError("At least one session is required in the pool.")
        return value

    def validate_blocked_resource_types(self, value):
        if value is None:
            return None
        if not isinstance(value, list):
            raise serializers.ValidationError("blocked_resource_types must be a list")
        for item in value:
            if not isinstance(item, str) or item not in ALLOWED_RESOURCE_TYPES:
                raise serializers.ValidationError(
                    f"Each item must be one of: {sorted(ALLOWED_RESOURCE_TYPES)}"
                )
        return value

    def update(self, instance, validated_data):
        if "name" in validated_data:
            instance.name = validated_data["name"]
        if "description" in validated_data:
            instance.description = validated_data["description"]
        if "session_ids" in validated_data:
            BrowserPoolSession.objects.filter(pool=instance).delete()
            for sid in validated_data["session_ids"]:
                BrowserPoolSession.objects.create(pool=instance, session_id=sid)
        if "domain_throttle_enabled" in validated_data:
            instance.domain_throttle_enabled = validated_data["domain_throttle_enabled"]
        if "resource_blocking_enabled" in validated_data:
            instance.resource_blocking_enabled = validated_data["resource_blocking_enabled"]
        if "blocked_resource_types" in validated_data:
            instance.blocked_resource_types = validated_data["blocked_resource_types"]
        instance.save()
        return instance


class PoolDomainThrottleRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PoolDomainThrottleRule
        fields = ["id", "pool", "domain", "delay_seconds", "enabled", "created_at", "updated_at"]
        read_only_fields = ["id", "pool", "created_at", "updated_at"]

    def validate_domain(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Domain is required")
        return value.strip().lower()

    def validate_delay_seconds(self, value):
        if value is None or value < 0:
            raise serializers.ValidationError("Delay must be >= 0")
        return value


class PoolDomainThrottleRuleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PoolDomainThrottleRule
        fields = ["domain", "delay_seconds", "enabled"]

    def validate_domain(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Domain is required")
        return value.strip().lower()

    def validate_delay_seconds(self, value):
        if value is None or value < 0:
            raise serializers.ValidationError("Delay must be >= 0")
        return value

