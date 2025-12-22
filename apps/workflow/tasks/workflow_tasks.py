"""
Celery tasks for workflow operations.

This module contains Celery tasks for full workflow execution and management.
Workflow execution is delegated to FlowEngineService.
"""

import structlog
from celery import shared_task
from celery.result import AsyncResult
from django.db.models import F
from django.utils import timezone
from ..models import WorkFlow
from ..services.workflow_converter import workflow_converter
from ..services.flow_engine_service import flow_engine_service
from ..services.redis_state_store import redis_state_store

logger = structlog.get_logger(__name__)


@shared_task(bind=True)
def execute_workflow(self, workflow_config: dict):
    """
    Execute a full workflow using the core FlowEngine.
    
    Args:
        workflow_config: Workflow configuration from RawWorkFlawSerializer
        
    Returns:
        Dict with execution status and results
    """
    workflow_id = workflow_config.get("id", None)
    logger.info("Workflow execution started", workflow_id=workflow_id)
    
    if not workflow_id:
        logger.error("No workflow ID provided")
        return {"status": "error", "error": "No workflow ID provided"}
    
    try:
        # Update workflow metrics and status
        # Use atomic update for runs_count to avoid race conditions
        now = timezone.now()
        # #region agent log
        with open('/home/roshan/main/TheOneEye/Attempt3/.cursor/debug.log', 'a') as f:
            import json
            f.write(json.dumps({"location":"workflow_tasks.py:42","message":"Before workflow update","data":{"workflow_id":str(workflow_id),"now":str(now),"hypothesisId":"A"},"timestamp":int(timezone.now().timestamp()*1000),"sessionId":"debug-session","runId":"run1"})+"\n")
        # #endregion
        rows_updated = WorkFlow.objects.filter(id=workflow_id).update(
            last_run=now,
            runs_count=F('runs_count') + 1,
            status='active'
        )
        # #region agent log
        with open('/home/roshan/main/TheOneEye/Attempt3/.cursor/debug.log', 'a') as f:
            import json
            f.write(json.dumps({"location":"workflow_tasks.py:50","message":"After workflow update","data":{"workflow_id":str(workflow_id),"rows_updated":rows_updated,"hypothesisId":"A"},"timestamp":int(timezone.now().timestamp()*1000),"sessionId":"debug-session","runId":"run1"})+"\n")
        # #endregion
        
        # Get workflow for further operations
        workflow = WorkFlow.objects.get(id=workflow_id)
        # #region agent log
        with open('/home/roshan/main/TheOneEye/Attempt3/.cursor/debug.log', 'a') as f:
            import json
            f.write(json.dumps({"location":"workflow_tasks.py:54","message":"Workflow retrieved after update","data":{"workflow_id":str(workflow_id),"last_run":str(workflow.last_run) if workflow.last_run else None,"runs_count":workflow.runs_count,"status":workflow.status,"hypothesisId":"A"},"timestamp":int(timezone.now().timestamp()*1000),"sessionId":"debug-session","runId":"run1"})+"\n")
        # #endregion
        
        logger.info("Workflow execution started", workflow_id=workflow_id, last_run=now)
        self.update_state(
            state='STARTED',
            meta={'workflow_id': workflow_id}
        )
        
        # Validate workflow
        validation = workflow_converter.validate_workflow(workflow_config)
        if not validation["is_valid"]:
            logger.error("Workflow validation failed", errors=validation["errors"])
            workflow.status = 'error'
            workflow.save()
            return {
                "status": "error",
                "error": "Workflow validation failed",
                "details": validation["errors"]
            }
        
        # Convert to FlowEngine format
        flow_engine_config = workflow_converter.convert_to_flow_engine_format(workflow_config)
        
        # Run workflow using FlowEngineService
        result = flow_engine_service.run_workflow(workflow_id, flow_engine_config)
        
        # Update workflow status based on result
        workflow = WorkFlow.objects.get(id=workflow_id)
        workflow.status = 'inactive' if result["status"] == "success" else 'error'
        workflow.save()
        
        return result
        
    except WorkFlow.DoesNotExist:
        logger.error("Workflow not found", workflow_id=workflow_id)
        return {"status": "error", "error": "Workflow not found"}
    except Exception as e:
        logger.exception("Error in workflow execution", workflow_id=workflow_id, error=str(e))
        
        # Update workflow status to error
        _update_workflow_status(workflow_id, 'error')
        
        return {"status": "error", "error": str(e)}
    finally:
        # Clean up workflow task_id
        _clear_workflow_task_id(workflow_id)


@shared_task(bind=True)
def stop_workflow(self, workflow_id: str):
    """
    Stop a running workflow by shutting down FlowEngine and revoking Celery task.
    """
    try:
        workflow = WorkFlow.objects.get(id=workflow_id)
        
        # Force shutdown the FlowEngine if it's running
        flow_engine_service.shutdown_engine(workflow_id)
        
        # Revoke the Celery task if it exists
        if workflow.task_id:
            execution_task = AsyncResult(workflow.task_id)
            execution_task.revoke(terminate=True, signal="SIGKILL")
            logger.info("Celery task revoked", task_id=workflow.task_id)
        
        # Clear Redis execution state to prevent stale data on restart
        redis_state_store.delete_state(workflow_id)
        logger.info("Redis execution state cleared", workflow_id=workflow_id)
        
        # Clean up workflow state
        workflow.task_id = None
        workflow.status = 'inactive'
        workflow.save()
        
        logger.info("Workflow stopped successfully", workflow_id=workflow_id)
        return {"status": "success", "message": f"Workflow {workflow_id} stopped"}
        
    except WorkFlow.DoesNotExist:
        logger.error("Workflow not found", workflow_id=workflow_id)
        return {"status": "error", "error": "Workflow not found"}
    except Exception as e:
        logger.exception("Error stopping workflow", workflow_id=workflow_id, error=str(e))
        return {"status": "error", "error": str(e)}


def _update_workflow_status(workflow_id: str, status: str) -> None:
    """Helper to update workflow status safely."""
    try:
        workflow = WorkFlow.objects.get(id=workflow_id)
        workflow.status = status
        workflow.save()
    except WorkFlow.DoesNotExist:
        pass


def _clear_workflow_task_id(workflow_id: str) -> None:
    """Helper to clear workflow task_id safely."""
    try:
        workflow = WorkFlow.objects.get(id=workflow_id)
        workflow.task_id = None
        workflow.save()
    except WorkFlow.DoesNotExist:
        pass
