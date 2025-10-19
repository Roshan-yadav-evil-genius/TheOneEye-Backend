"""
Serializer for ContainerStats model.

This module provides serialization for container resource statistics.
"""

from rest_framework import serializers
from workflow.models import ContainerStats


class ContainerStatsSerializer(serializers.ModelSerializer):
    """Serializer for ContainerStats model."""
    
    class Meta:
        model = ContainerStats
        fields = [
            'id',
            'workflow',
            'cpu_percent',
            'memory_usage_mb',
            'memory_percent',
            'network_in_kb',
            'network_out_kb',
            'disk_read_mb',
            'disk_write_mb',
            'timestamp',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'timestamp']


class ContainerStatsListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing container stats."""
    
    class Meta:
        model = ContainerStats
        fields = [
            'id',
            'cpu_percent',
            'memory_usage_mb',
            'memory_percent',
            'network_in_kb',
            'network_out_kb',
            'disk_read_mb',
            'disk_write_mb',
            'timestamp'
        ]
