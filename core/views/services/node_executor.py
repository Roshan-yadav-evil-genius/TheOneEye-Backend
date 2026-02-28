"""
Node Executor Module
Executes nodes with input and form data.
Uses a shared event loop so browser contexts can be reused across requests.
"""

import asyncio
import traceback
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any, Dict, Optional

import structlog

from apps.common.exceptions import FormValidationException, ExecutionTimeoutException
from .node_loader import NodeLoader
from .node_session_store import NodeSessionStore
from .shared_browser_loop import get_shared_loop

logger = structlog.get_logger(__name__)


class NodeExecutor:
    """
    Executes nodes asynchronously with input and form data.
    
    Responsibilities:
    - Create or reuse node instances with configuration
    - Execute nodes with input data
    - Handle async execution
    - Manage stateful sessions via NodeSessionStore
    """
    
    def __init__(self, node_loader: NodeLoader):
        """
        Initialize NodeExecutor.
        
        Args:
            node_loader: NodeLoader for loading node classes.
        """
        self._node_loader = node_loader
        self._session_store = NodeSessionStore()
    
    def execute(
        self,
        node_metadata: Dict,
        input_data: Dict,
        form_data: Dict,
        session_id: Optional[str] = None,
        timeout: Optional[float] = None,
        node_id: Optional[str] = None,
        workflow_env: Optional[Dict[str, Any]] = None,
    ) -> Dict:
        """
        Execute a node with the given input and form data.

        Args:
            node_metadata: Node metadata dict.
            input_data: Input data to pass to the node.
            form_data: Form field values.
            session_id: Session ID for stateful execution (reuses instance per session+instance_key).
            timeout: Optional timeout in seconds (default: None, no timeout).
            node_id: Optional workflow node UUID; when set, instance is keyed by (session_id, node_id).
            workflow_env: Optional workflow-level env for Jinja (workflowenv.<key>). Pass when running in workflow context.

        Returns:
            Dict with execution result or error information.
        """
        node_class = self._node_loader.load_class(node_metadata)

        if node_class is None:
            return {
                'success': False,
                'error': 'Failed to load node class',
                'identifier': node_metadata.get('identifier'),
                'file_path': node_metadata.get('file_path')
            }

        try:
            result = self._run_node(
                node_class, node_metadata, input_data, form_data, session_id, timeout, node_id, workflow_env
            )
            
            return {
                'success': True,
                'node': {
                    'name': node_metadata.get('name'),
                    'identifier': node_metadata.get('identifier'),
                },
                'input': input_data,
                'form_data': form_data,
                'session_id': session_id,
                'output': result.model_dump() if hasattr(result, 'model_dump') else result
            }
            
        except asyncio.TimeoutError:
            # Handle timeout - clean up and raise ExecutionTimeoutException
            if session_id:
                self._session_store.clear_session(session_id)
            raise ExecutionTimeoutException(
                timeout=timeout or 0,
                detail=f'Node execution exceeded timeout of {timeout} seconds'
            )
        except ExecutionTimeoutException:
            # Re-raise ExecutionTimeoutException
            raise
        except Exception as e:
            # Check if it's a FormValidationError by type name and attributes (module path may differ)
            # Use type name check instead of isinstance due to module path differences
            is_form_validation_error = (
                type(e).__name__ == 'FormValidationError' and
                hasattr(e, 'form') and
                hasattr(e, 'message')
            )
            
            if is_form_validation_error:
                try:
                    form_state = e.form.get_form_schema()
                    
                    # Raise FormValidationException instead of returning error response
                    # Use actual error message instead of hardcoded string
                    raise FormValidationException(
                        message=e.message,  # Use actual error message (e.g., "Invalid JSON: ...")
                        form_data=form_state,
                        detail=e.message
                    )
                except FormValidationException:
                    # Re-raise FormValidationException
                    raise
                except Exception:
                    # If serialization fails, raise the original exception
                    raise
            
            # For other exceptions, re-raise them (let DRF exception handler deal with them)
            traceback.print_exc()
            raise
    
    def clear_session(self, session_id: str) -> bool:
        """
        Clear all node instances for this session.

        Args:
            session_id: Session ID to clear.

        Returns:
            True if any instance was cleared, False otherwise.
        """
        return self._session_store.clear_session(session_id) > 0
    
    def _run_node(
        self,
        node_class,
        node_metadata: Dict,
        input_data: Dict,
        form_data: Dict,
        session_id: Optional[str] = None,
        timeout: Optional[float] = None,
        node_id: Optional[str] = None,
        workflow_env: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Run the node asynchronously and return the result.

        If session_id is provided, reuses existing instance for (session_id, instance_key).
        instance_key is node_id when provided (workflow), else node type identifier (direct API).
        If workflow_env is provided (e.g. when running from workflow canvas), Jinja can use workflowenv.<key>.
        """
        from ...Node.Core.Node.Core.Data import NodeConfig, NodeConfigData, NodeOutput

        instance_key = node_id if node_id is not None else node_metadata.get("identifier", "")
        node_instance = None
        is_new_instance = False

        if session_id and instance_key:
            node_instance = self._session_store.get(session_id, instance_key)

        if node_instance is None:
            node_config = NodeConfig(
                id=f"exec_{node_metadata.get('identifier')}",
                type=node_metadata.get('identifier'),
                data=NodeConfigData(form=form_data)
            )
            node_instance = node_class(node_config)
            is_new_instance = True

            if session_id and instance_key:
                self._session_store.set(session_id, instance_key, node_instance)
        else:
            # Update form data on existing instance
            node_instance.node_config.data.form = form_data

        env = workflow_env if workflow_env is not None else {}
        # Create NodeOutput from input data; include workflow env for Jinja (workflowenv.<key>)
        node_output = NodeOutput(data=input_data, metadata={"workflow_env": env})
        
        # Run the node asynchronously on the shared loop (browser context is reused)
        async def run_async():
            if is_new_instance:
                await node_instance.init()
            return await node_instance.run(node_output)

        loop = get_shared_loop()
        timeout_seconds = timeout if (timeout is not None and timeout > 0) else None
        future = asyncio.run_coroutine_threadsafe(run_async(), loop)
        try:
            result = future.result(timeout=timeout_seconds)
        except FuturesTimeoutError:
            future.cancel()
            if session_id:
                self._session_store.clear_session(session_id)
            raise asyncio.TimeoutError(
                f"Node execution exceeded timeout of {timeout or 0} seconds"
            )
        except Exception:
            raise

        # Close idle browser contexts on shared loop (e.g. when all pages processed)
        try:
            from ...Node.Nodes.Browser._shared.BrowserManager import BrowserManager
            cleanup_future = asyncio.run_coroutine_threadsafe(
                BrowserManager().close_idle_contexts(),
                loop,
            )
            cleanup_future.result(timeout=10)
        except FuturesTimeoutError:
            logger.warning(
                "Browser idle-context cleanup timed out after node execution",
                identifier=node_metadata.get("identifier"),
            )
        except Exception as e:
            logger.warning(
                "Browser idle-context cleanup failed after node execution",
                error=str(e),
                identifier=node_metadata.get("identifier"),
            )

        return result

