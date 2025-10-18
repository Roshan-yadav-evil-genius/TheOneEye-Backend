"""
Backward compatibility module for workflow tasks.

This module re-exports all tasks from the refactored task modules
to maintain backward compatibility with existing imports.
"""

# Re-export all tasks for backward compatibility
from .task_modules.workflow_tasks import execute_workflow, stop_workflow
from .task_modules.node_tasks import (
    execute_single_node,
    execute_single_node_incremental,
    stop_dev_container
)

# Re-export services for direct access if needed
from .services.docker_service import docker_service
from .services.workflow_config_service import workflow_config_service
from .services.dependency_service import dependency_service
from .services.node_execution_service import node_execution_service

__all__ = [
    # Celery tasks
    'execute_workflow',
    'stop_workflow',
    'execute_single_node',
    'execute_single_node_incremental',
    'stop_dev_container',
    
    # Services (for advanced usage)
    'docker_service',
    'workflow_config_service',
    'dependency_service',
    'node_execution_service',
]