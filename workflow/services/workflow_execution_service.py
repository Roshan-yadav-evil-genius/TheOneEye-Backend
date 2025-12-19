"""
Workflow execution service.

This module handles workflow execution orchestration via Celery tasks.
Follows Single Responsibility Principle - only handles workflow execution management.
"""

from typing import Dict, Any, Optional
from celery.result import AsyncResult
from ..models import WorkFlow


class WorkflowExecutionService:
    """Service for managing workflow execution via Celery tasks."""
    
    @staticmethod
    def start_execution(workflow: WorkFlow, workflow_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start workflow execution as a Celery task.
        
        Args:
            workflow: The WorkFlow model instance
            workflow_config: Serialized workflow configuration
            
        Returns:
            Dict with task_id and initial status
        """
        from workflow.tasks import execute_workflow
        
        task: AsyncResult = execute_workflow.delay(workflow_config)
        
        # Save task ID to workflow
        workflow.task_id = task.id
        workflow.save()
        
        return {
            "task_id": task.id,
            "status": task.status
        }
    
    @staticmethod
    def stop_execution(workflow: WorkFlow, timeout: int = 5) -> Dict[str, Any]:
        """
        Stop a running workflow execution.
        
        Args:
            workflow: The WorkFlow model instance
            timeout: Timeout in seconds to wait for task completion
            
        Returns:
            Dict with task_id and final status
        """
        from workflow.tasks import stop_workflow
        
        task: AsyncResult = stop_workflow.delay(str(workflow.id))
        task.get(timeout)
        
        return {
            "task_id": task.id,
            "status": task.status
        }
    
    @staticmethod
    def get_task_status(workflow: WorkFlow) -> Optional[Dict[str, Any]]:
        """
        Get the current status of a workflow's execution task.
        
        Args:
            workflow: The WorkFlow model instance
            
        Returns:
            Dict with task_id and status, or None if no task exists
        """
        task_id = workflow.task_id
        
        if not task_id:
            return None
        
        result: AsyncResult = AsyncResult(task_id)
        
        return {
            "task_id": task_id,
            "status": result.status
        }
    
    @staticmethod
    def has_active_task(workflow: WorkFlow) -> bool:
        """
        Check if the workflow has an active Celery task.
        
        Args:
            workflow: The WorkFlow model instance
            
        Returns:
            True if an active task exists, False otherwise
        """
        if not workflow.task_id:
            return False
        
        result: AsyncResult = AsyncResult(workflow.task_id)
        return result.status in ['PENDING', 'STARTED', 'PROGRESS']


# Global instance for convenience
workflow_execution_service = WorkflowExecutionService()

