"""
API Execution Service.

This module handles synchronous API workflow execution.
Follows Single Responsibility Principle - only handles API workflow execution orchestration.
"""

import sys
import os
import asyncio
import time
import structlog
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Dict, Any, Optional
from pathlib import Path

# Add core to path for imports
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
CORE_PATH = BASE_DIR / 'core'
if str(CORE_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_PATH))

# Ensure Django is set up before importing Workflow (needed for model access)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'theoneeye.settings')
import django
django.setup()

from ..models import WorkFlow, WorkflowType
from .workflow_converter import workflow_converter
from ..Serializers.WorkFlow import RawWorkFlawSerializer

logger = structlog.get_logger(__name__)


class APIExecutionService:
    """
    Service for synchronous API workflow execution.
    
    This service handles the orchestration of API workflow execution:
    - Validates workflow exists and is of type 'api'
    - Validates workflow starts with WebhookProducer node
    - Converts workflow to FlowEngine format
    - Executes workflow synchronously with timeout
    - Returns formatted response
    """
    
    @staticmethod
    def execute_workflow(
        workflow_id: str,
        input_data: Dict[str, Any],
        timeout: int = 300,
        request_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute an API workflow synchronously.
        
        Args:
            workflow_id: UUID of the workflow to execute
            input_data: Data from HTTP request body to pass to the workflow
            timeout: Maximum execution time in seconds (default: 300)
            request_context: Optional HTTP request context containing:
                - headers: Dict of HTTP headers
                - query_params: Dict of URL query parameters
                - method: HTTP method (GET, POST, etc.)
            
        Returns:
            Dict with execution result:
            - success: bool indicating if execution succeeded
            - workflow_id: The workflow UUID
            - output: The output data from the last node (on success)
            - execution_time_ms: Time taken in milliseconds
            - error: Error message (on failure)
            
        Raises:
            WorkFlow.DoesNotExist: If workflow not found
        """
        from core.Workflow.flow_engine import FlowEngine
        
        start_time = time.time()
        
        try:
            # Get and validate workflow
            workflow = WorkFlow.objects.get(id=workflow_id)
            
            # Validate workflow type
            if workflow.workflow_type != WorkflowType.API:
                logger.warning(
                    "Attempted to execute non-API workflow via API endpoint",
                    workflow_id=workflow_id,
                    workflow_type=workflow.workflow_type
                )
                return {
                    'success': False,
                    'error': f"Workflow '{workflow.name}' is not an API workflow. "
                             f"Current type: {workflow.workflow_type}. "
                             f"Only API workflows can be executed via this endpoint.",
                    'workflow_id': str(workflow_id),
                    'execution_time_ms': int((time.time() - start_time) * 1000)
                }
            
            # Validate workflow is active (accepting requests)
            if workflow.status != 'active':
                logger.warning(
                    "Attempted to execute inactive API workflow",
                    workflow_id=workflow_id,
                    workflow_status=workflow.status
                )
                return {
                    'success': False,
                    'error': f"Workflow '{workflow.name}' is not active. "
                             f"Activate it first via the /activate/ endpoint before sending requests.",
                    'workflow_id': str(workflow_id),
                    'execution_time_ms': int((time.time() - start_time) * 1000)
                }
            
            # Update workflow metrics (runs_count, last_run) for each API execution
            from django.db.models import F
            from django.utils import timezone
            
            WorkFlow.objects.filter(id=workflow_id).update(
                last_run=timezone.now(),
                runs_count=F('runs_count') + 1
            )
            
            logger.info(
                "Starting API workflow execution",
                workflow_id=workflow_id,
                workflow_name=workflow.name,
                timeout=timeout
            )
            
            # Convert to FlowEngine format
            workflow_config = RawWorkFlawSerializer(workflow).data
            
            # Validate workflow has nodes
            validation = workflow_converter.validate_workflow(workflow_config)
            if not validation["is_valid"]:
                logger.error(
                    "Workflow validation failed",
                    workflow_id=workflow_id,
                    errors=validation["errors"]
                )
                return {
                    'success': False,
                    'error': f"Workflow validation failed: {', '.join(validation['errors'])}",
                    'workflow_id': str(workflow_id),
                    'execution_time_ms': int((time.time() - start_time) * 1000)
                }
            
            flow_engine_config = workflow_converter.convert_to_flow_engine_format(workflow_config)
            
            # Create and load engine
            engine = FlowEngine(workflow_id=str(workflow_id))
            engine.load_workflow(flow_engine_config)
            
            # Execute on shared browser loop (reuse contexts; no per-request cleanup)
            from core.views.services.shared_browser_loop import get_shared_loop
            shared_loop = get_shared_loop()
            future = asyncio.run_coroutine_threadsafe(
                engine.run_api(input_data, timeout, request_context=request_context),
                shared_loop
            )
            timeout_with_buffer = timeout + 5

            try:
                result = future.result(timeout=timeout_with_buffer)
                execution_time_ms = int((time.time() - start_time) * 1000)
                logger.info(
                    "API workflow execution completed successfully",
                    workflow_id=workflow_id,
                    execution_time_ms=execution_time_ms
                )
                return {
                    'success': True,
                    'workflow_id': str(workflow_id),
                    'output': result.data if result else {},
                    'execution_time_ms': execution_time_ms
                }
            except FuturesTimeoutError:
                execution_time_ms = int((time.time() - start_time) * 1000)
                logger.error(
                    "API workflow execution timeout (future.result)",
                    workflow_id=workflow_id,
                    timeout=timeout,
                    execution_time_ms=execution_time_ms
                )
                return {
                    'success': False,
                    'error': f'Execution timeout after {timeout} seconds',
                    'workflow_id': str(workflow_id),
                    'execution_time_ms': execution_time_ms
                }
            except asyncio.TimeoutError:
                execution_time_ms = int((time.time() - start_time) * 1000)
                logger.error(
                    "API workflow execution timeout",
                    workflow_id=workflow_id,
                    timeout=timeout,
                    execution_time_ms=execution_time_ms
                )
                return {
                    'success': False,
                    'error': f'Execution timeout after {timeout} seconds',
                    'workflow_id': str(workflow_id),
                    'execution_time_ms': execution_time_ms
                }
            except ValueError as e:
                execution_time_ms = int((time.time() - start_time) * 1000)
                logger.error(
                    "API workflow validation error",
                    workflow_id=workflow_id,
                    error=str(e),
                    execution_time_ms=execution_time_ms
                )
                return {
                    'success': False,
                    'error': str(e),
                    'workflow_id': str(workflow_id),
                    'execution_time_ms': execution_time_ms
                }
                
        except WorkFlow.DoesNotExist:
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.error("Workflow not found", workflow_id=workflow_id)
            return {
                'success': False,
                'error': f'Workflow not found: {workflow_id}',
                'workflow_id': str(workflow_id),
                'execution_time_ms': execution_time_ms
            }
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.exception(
                "Unexpected error during API workflow execution",
                workflow_id=workflow_id,
                error=str(e)
            )
            return {
                'success': False,
                'error': f'Execution failed: {str(e)}',
                'workflow_id': str(workflow_id),
                'execution_time_ms': execution_time_ms
            }


# Global instance for convenience
api_execution_service = APIExecutionService()
