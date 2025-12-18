"""
Celery tasks for workflow operations.

This module contains Celery tasks for full workflow execution and management.
Workflow execution is handled by the core FlowEngine.
"""

import sys
import os
import json
import asyncio
import structlog
from datetime import datetime
from celery import shared_task
from celery.result import AsyncResult
from ..models import WorkFlow
from ..services.workflow_converter import workflow_converter

# Add core to path for imports
sys.path.insert(0, '/home/roshan/main/TheOneEye/Attempt3/core')

logger = structlog.get_logger(__name__)

# Directory to save workflow configs for debugging
BIN_DIR = '/home/roshan/main/TheOneEye/Attempt3/backend/bin'

# Global reference to track running engines for shutdown
_running_engines = {}


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
    print(f"Execution started for Workflow ID: {workflow_id}")
    if not workflow_id:
        logger.error("No workflow ID provided")
        return {"status": "error", "error": "No workflow ID provided"}
    
    try:
        # Update workflow status to running
        workflow = WorkFlow.objects.get(id=workflow_id)
        workflow.status = 'active'
        workflow.save()
        
        logger.info("Workflow execution started", workflow_id=workflow_id)
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
        
    
        # Import and run FlowEngine
        from Workflow.flow_engine import FlowEngine
        engine = FlowEngine()
        _running_engines[workflow_id] = engine
        
        try:
            # Load the workflow
            logger.info("Loading workflow into FlowEngine", workflow_id=workflow_id)
            engine.load_workflow(flow_engine_config)
            logger.info("Workflow loaded into FlowEngine", workflow_id=workflow_id)
            
            # Run the workflow in production mode
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(engine.run_production())
                logger.info("Workflow execution completed successfully", workflow_id=workflow_id)
                
                # Update workflow status
                workflow = WorkFlow.objects.get(id=workflow_id)
                workflow.status = 'inactive'
                workflow.save()
                
                return {
                    "status": "success",
                    "workflow_id": workflow_id,
                    "message": "Workflow execution completed successfully"
                }
            finally:
                # Clean up browser resources
                try:
                    from Node.Nodes.Browser.BrowserManager import BrowserManager
                    browser_manager = BrowserManager()
                    loop.run_until_complete(browser_manager.close())
                    logger.info("Browser resources cleaned up", workflow_id=workflow_id)
                except Exception as browser_cleanup_error:
                    logger.warning("Error cleaning up browser resources", error=str(browser_cleanup_error))
                
                loop.close()
                
        finally:
            # Clean up engine reference
            if workflow_id in _running_engines:
                del _running_engines[workflow_id]
        
    except WorkFlow.DoesNotExist:
        logger.error("Workflow not found", workflow_id=workflow_id)
        return {"status": "error", "error": "Workflow not found"}
    except Exception as e:
        logger.exception("Error in workflow execution", workflow_id=workflow_id, error=str(e))
        
        # Update workflow status to error
        try:
            workflow = WorkFlow.objects.get(id=workflow_id)
            workflow.status = 'error'
            workflow.save()
        except WorkFlow.DoesNotExist:
            pass
        
        return {"status": "error", "error": str(e)}
    finally:
        # Clean up workflow task_id
        try:
            workflow = WorkFlow.objects.get(id=workflow_id)
            workflow.task_id = None
            workflow.save()
        except WorkFlow.DoesNotExist:
            pass


@shared_task(bind=True)
def stop_workflow(self, workflow_id: str):
    """
    Stop a running workflow by shutting down FlowEngine and revoking Celery task.
    """
    try:
        workflow = WorkFlow.objects.get(id=workflow_id)
        
        # Force shutdown the FlowEngine if it's running
        if workflow_id in _running_engines:
            engine = _running_engines[workflow_id]
            logger.info("Force shutting down FlowEngine", workflow_id=workflow_id)
            engine.force_shutdown()
            del _running_engines[workflow_id]
        
        # Clean up browser resources
        try:
            from Node.Nodes.Browser.BrowserManager import BrowserManager
            browser_manager = BrowserManager()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(browser_manager.close())
                logger.info("Browser resources cleaned up on stop", workflow_id=workflow_id)
            finally:
                loop.close()
        except Exception as browser_cleanup_error:
            logger.warning("Error cleaning up browser resources on stop", error=str(browser_cleanup_error))
        
        # Revoke the Celery task if it exists
        if workflow.task_id:
            execution_task = AsyncResult(workflow.task_id)
            execution_task.revoke(terminate=True, signal="SIGKILL")
            logger.info("Celery task revoked", task_id=workflow.task_id)
        
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
