import json
import docker
from celery import shared_task
from .models import WorkFlow
from celery.result import AsyncResult


client = docker.from_env()
imageName = "theoneeyecore"


def image_exists():
    try:
        client.images.get(imageName)
        print("[+] theoneeyecore Image Found")
        return True
    except docker.errors.ImageNotFound as e:
        print("[-] theoneeyecore Image Not Found")
        return False

def container_exists(name: str) -> bool:
    try:
        client.containers.get(name)
        return True
    except docker.errors.NotFound:
        return False

def kill_and_remove(name: str):
    try:
        container = client.containers.get(name)
        container.remove(force=True)   # remove container
        print(f"{name} killed & removed")
    except docker.errors.NotFound:
        print(f"{name} not found")

@shared_task(bind=True)
def execute_workflow(self, workflow_config: dict):
    if not image_exists():
        print(f"[+] {imageName} Image Not exist")
        return

    workflow_id = workflow_config.get("id", None)
    workflow: WorkFlow = WorkFlow.objects.get(id=workflow_id)

    if container_exists(workflow_id):
        kill_and_remove(workflow_id)

    print(f"[+] {workflow_id} Workflow Execution started")
    self.update_state(
            state='STARTED',
            meta={'workflow_id': workflow_id}
        )

    try:
        container = client.containers.run(
            image=imageName,
            name=workflow_id,
            remove=True,
            environment={
                "CELERY_TASK_ID": workflow.task_id,
                "CONFIG_JSON": json.dumps(workflow_config,default=str)
            },
            command=[
                "sh", "-c",
                """
                # Run main script
                python -u  main.py
                """
            ]
        )
    except Exception as e:
        print("Error: ",e)
    workflow: WorkFlow = WorkFlow.objects.get(id=workflow_id)
    workflow.task_id = None
    workflow.save()


@shared_task(bind=True)
def stop_workflow(self, workflow_id: str):
    workflow: WorkFlow = WorkFlow.objects.get(id=workflow_id)

    if container_exists(workflow_id):
        kill_and_remove(workflow_id)
    
    executionTask:AsyncResult =  AsyncResult(workflow.task_id)

    executionTask.revoke(terminate=True,signal="SIGKILL")
    
    workflow.task_id = None
    workflow.save()