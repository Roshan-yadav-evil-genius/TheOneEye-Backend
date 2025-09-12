from celery import shared_task
import json
import time


@shared_task(bind=True)
def execute_workflow(self, workflow_config: dict):
    with open("config.json", "w") as file:
        json.dump(workflow_config, file, default=str)
    time.sleep(10)