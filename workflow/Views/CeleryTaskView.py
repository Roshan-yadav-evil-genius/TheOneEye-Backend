from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from celery.result import AsyncResult
import logging

logger = logging.getLogger(__name__)

class CeleryTaskStatusView(APIView):
    """
    API view to get the status of a Celery task by task ID
    """
    
    def get(self, request, task_id):
        """
        Get the status of a Celery task
        
        Args:
            task_id: The Celery task ID
            
        Returns:
            JSON response with task status, result, and error information
        """
        try:
            # Get the task result using AsyncResult
            task_result = AsyncResult(task_id)
            
            # Get task state
            task_state = task_result.state
            
            # Prepare response data
            response_data = {
                'state': task_state,
                'task_id': task_id
            }
            
            # Add result if task is successful
            if task_state == 'SUCCESS':
                response_data['result'] = task_result.result
            elif task_state == 'FAILURE':
                # Get error information
                response_data['error'] = str(task_result.result)
                response_data['traceback'] = task_result.traceback
            elif task_state == 'PENDING':
                response_data['result'] = None
            elif task_state == 'STARTED':
                response_data['result'] = None
            elif task_state == 'RETRY':
                response_data['result'] = None
            elif task_state == 'REVOKED':
                response_data['error'] = 'Task was revoked'
            
            # Add progress if available
            if hasattr(task_result, 'info') and task_result.info:
                if isinstance(task_result.info, dict) and 'progress' in task_result.info:
                    response_data['progress'] = task_result.info['progress']
            
            logger.info(f"Task {task_id} status: {task_state}")
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting task status for {task_id}: {str(e)}")
            return Response({
                'error': f'Failed to get task status: {str(e)}',
                'task_id': task_id,
                'state': 'UNKNOWN'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
