"""
Celery tasks for workflow operations.

This module contains Celery tasks for full workflow execution and management.
"""

from celery import shared_task
from celery.result import AsyncResult
from ..models import WorkFlow
from ..services.docker_service import docker_service
from ..services.workflow_config_service import workflow_config_service


@shared_task(bind=True)
def execute_workflow(self, workflow_config: dict):
    """
    Execute a full workflow in a temporary Docker container.
    This is the original workflow execution task.
    """
    if not docker_service.image_exists():
        print(f"[-] {docker_service.image_name} Image does not exist")
        return

    workflow_id = workflow_config.get("id", None)
    workflow = WorkFlow.objects.get(id=workflow_id)

    if docker_service.container_exists(workflow_id):
        docker_service.kill_and_remove(workflow_id)

    print(f"[+] {workflow_id} Workflow Execution started")
    self.update_state(
        state='STARTED',
        meta={'workflow_id': workflow_id}
    )

    try:
        container = docker_service.create_workflow_container(workflow_id, workflow_config)
        if container:
            print(f"[+] Workflow container {workflow_id} created successfully")
        else:
            print(f"[-] Failed to create workflow container {workflow_id}")
    except Exception as e:
        print(f"[-] Error in workflow execution: {e}")
    finally:
        # Clean up workflow state
        workflow = WorkFlow.objects.get(id=workflow_id)
        workflow.task_id = None
        workflow.save()


@shared_task(bind=True)
def stop_workflow(self, workflow_id: str):
    """
    Stop a running workflow by killing its container and revoking the Celery task.
    """
    try:
        workflow = WorkFlow.objects.get(id=workflow_id)
        
        # Stop the container if it exists
        if docker_service.container_exists(workflow_id):
            docker_service.kill_and_remove(workflow_id)
        
        # Revoke the Celery task if it exists
        if workflow.task_id:
            execution_task = AsyncResult(workflow.task_id)
            execution_task.revoke(terminate=True, signal="SIGKILL")
        
        # Clean up workflow state
        workflow.task_id = None
        workflow.save()
        
        print(f"[+] Workflow {workflow_id} stopped successfully")
        return {"status": "success", "message": f"Workflow {workflow_id} stopped"}
        
    except WorkFlow.DoesNotExist:
        print(f"[-] Workflow {workflow_id} not found")
        return {"status": "error", "error": "Workflow not found"}
    except Exception as e:
        print(f"[-] Error stopping workflow {workflow_id}: {str(e)}")
        return {"status": "error", "error": str(e)}
