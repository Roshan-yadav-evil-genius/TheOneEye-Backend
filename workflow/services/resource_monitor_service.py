"""
Resource monitoring service for Docker containers.

This module handles real-time monitoring of container resource usage
using Docker's stats streaming API.
"""

import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from django.utils import timezone
from ..models import ContainerStats, WorkFlow
from .docker_service import docker_service

logger = logging.getLogger(__name__)


class ResourceMonitorService:
    """Service for monitoring container resource usage."""
    
    def __init__(self):
        self.docker_service = docker_service
    
    def calculate_cpu_percent(self, cpu_stats: Dict, precpu_stats: Dict) -> float:
        """Calculate CPU usage percentage from Docker stats."""
        try:
            cpu_delta = cpu_stats['cpu_usage']['total_usage'] - precpu_stats['cpu_usage']['total_usage']
            system_delta = cpu_stats['system_cpu_usage'] - precpu_stats['system_cpu_usage']
            
            if system_delta > 0 and cpu_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * len(cpu_stats['cpu_usage']['percpu_usage']) * 100.0
                return round(cpu_percent, 2)
            return 0.0
        except (KeyError, ZeroDivisionError, TypeError):
            return 0.0
    
    def calculate_memory_percent(self, memory_stats: Dict) -> float:
        """Calculate memory usage percentage from Docker stats."""
        try:
            usage = memory_stats['usage']
            limit = memory_stats['limit']
            if limit > 0:
                return round((usage / limit) * 100.0, 2)
            return 0.0
        except (KeyError, ZeroDivisionError, TypeError):
            return 0.0
    
    def calculate_network_io(self, networks: Dict) -> tuple[float, float]:
        """Calculate network I/O in KB from Docker stats."""
        try:
            rx_bytes = 0
            tx_bytes = 0
            
            for interface, stats in networks.items():
                rx_bytes += stats.get('rx_bytes', 0)
                tx_bytes += stats.get('tx_bytes', 0)
            
            # Convert bytes to KB
            rx_kb = round(rx_bytes / 1024, 2)
            tx_kb = round(tx_bytes / 1024, 2)
            
            return rx_kb, tx_kb
        except (KeyError, TypeError):
            return 0.0, 0.0
    
    def calculate_disk_io(self, blkio_stats: Dict) -> tuple[float, float]:
        """Calculate disk I/O in MB from Docker stats."""
        try:
            read_bytes = 0
            write_bytes = 0
            
            for stat in blkio_stats.get('io_service_bytes_recursive', []):
                if stat['op'] == 'Read':
                    read_bytes += stat['value']
                elif stat['op'] == 'Write':
                    write_bytes += stat['value']
            
            # Convert bytes to MB
            read_mb = round(read_bytes / (1024 * 1024), 2)
            write_mb = round(write_bytes / (1024 * 1024), 2)
            
            return read_mb, write_mb
        except (KeyError, TypeError):
            return 0.0, 0.0
    
    def parse_container_stats(self, stats_data: Dict) -> Optional[Dict[str, float]]:
        """Parse Docker stats data and extract resource metrics."""
        try:
            # Calculate CPU percentage
            cpu_percent = self.calculate_cpu_percent(
                stats_data['cpu_stats'],
                stats_data['precpu_stats']
            )
            
            # Calculate memory metrics
            memory_stats = stats_data['memory_stats']
            memory_usage_mb = round(memory_stats['usage'] / (1024 * 1024), 2)
            memory_percent = self.calculate_memory_percent(memory_stats)
            
            # Calculate network I/O
            network_in_kb, network_out_kb = self.calculate_network_io(stats_data['networks'])
            
            # Calculate disk I/O
            disk_read_mb, disk_write_mb = self.calculate_disk_io(stats_data['blkio_stats'])
            
            return {
                'cpu_percent': cpu_percent,
                'memory_usage_mb': memory_usage_mb,
                'memory_percent': memory_percent,
                'network_in_kb': network_in_kb,
                'network_out_kb': network_out_kb,
                'disk_read_mb': disk_read_mb,
                'disk_write_mb': disk_write_mb,
            }
        except (KeyError, TypeError) as e:
            logger.error(f"Error parsing container stats: {e}")
            return None
    
    def monitor_container_stats(self, workflow_id: str) -> None:
        """
        Monitor container resource statistics and store them in the database.
        
        Args:
            workflow_id: The workflow ID (also the container name)
        """
        try:
            # Get the workflow object
            workflow = WorkFlow.objects.get(id=workflow_id)
            logger.info(f"Starting resource monitoring for workflow {workflow_id}")
            
            # Get the container
            container = self.docker_service.get_container(workflow_id)
            if not container:
                logger.error(f"Container {workflow_id} not found")
                return
            
            # Check if container is running
            container.reload()
            if container.status != 'running':
                logger.warning(f"Container {workflow_id} is not running (status: {container.status})")
                return
            
            # Start monitoring with Docker stats stream
            stats_stream = container.stats(stream=True, decode=True)
            
            logger.info(f"Started stats stream for container {workflow_id}")
            
            for stats_data in stats_stream:
                try:
                    # Parse the stats data
                    parsed_stats = self.parse_container_stats(stats_data)
                    
                    if parsed_stats:
                        # Create database record
                        ContainerStats.objects.create(
                            workflow=workflow,
                            **parsed_stats
                        )
                        
                        logger.info(f"Recorded stats for {workflow_id}: CPU {parsed_stats['cpu_percent']}%, "
                                   f"Memory {parsed_stats['memory_percent']}%, "
                                   f"Network In {parsed_stats['network_in_kb']}KB, "
                                   f"Network Out {parsed_stats['network_out_kb']}KB, "
                                   f"Disk Read {parsed_stats['disk_read_mb']}MB, "
                                   f"Disk Write {parsed_stats['disk_write_mb']}MB")
                    
                except Exception as e:
                    logger.error(f"Error processing stats for {workflow_id}: {e}")
                    continue
                    
        except WorkFlow.DoesNotExist:
            logger.error(f"Workflow {workflow_id} not found")
        except Exception as e:
            logger.error(f"Error monitoring container {workflow_id}: {e}")
        finally:
            logger.info(f"Resource monitoring ended for workflow {workflow_id}")
    
    def get_workflow_stats(self, workflow_id: str, time_range: str = '24h') -> list[Dict[str, Any]]:
        """
        Get resource statistics for a workflow within a time range.
        
        Args:
            workflow_id: The workflow ID
            time_range: Time range ('1h', '24h', '7d', '30d')
            
        Returns:
            List of stats dictionaries
        """
        try:
            workflow = WorkFlow.objects.get(id=workflow_id)
            
            # Calculate time filter
            now = timezone.now()
            if time_range == '1h':
                start_time = now - timedelta(hours=1)
            elif time_range == '24h':
                start_time = now - timedelta(days=1)
            elif time_range == '7d':
                start_time = now - timedelta(days=7)
            elif time_range == '30d':
                start_time = now - timedelta(days=30)
            else:
                start_time = now - timedelta(days=1)  # Default to 24h
            
            # Query stats
            stats = ContainerStats.objects.filter(
                workflow=workflow,
                timestamp__gte=start_time
            ).order_by('timestamp')
            
            # Convert to list of dictionaries
            return [
                {
                    'id': str(stat.id),
                    'cpu_percent': stat.cpu_percent,
                    'memory_usage_mb': stat.memory_usage_mb,
                    'memory_percent': stat.memory_percent,
                    'network_in_kb': stat.network_in_kb,
                    'network_out_kb': stat.network_out_kb,
                    'disk_read_mb': stat.disk_read_mb,
                    'disk_write_mb': stat.disk_write_mb,
                    'timestamp': stat.timestamp.isoformat(),
                }
                for stat in stats
            ]
            
        except WorkFlow.DoesNotExist:
            logger.error(f"Workflow {workflow_id} not found")
            return []
        except Exception as e:
            logger.error(f"Error getting stats for workflow {workflow_id}: {e}")
            return []


# Global instance
resource_monitor_service = ResourceMonitorService()
