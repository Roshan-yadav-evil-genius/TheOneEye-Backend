from celery import shared_task
import time

from workflow.Serializers.WorkFlow import RawWorkFlawSerializer
from workflow.models import WorkFlow

@shared_task(bind=True)
def execute_workflow(self,workflow_config:dict):
    print(workflow_config)
    time.sleep(10)