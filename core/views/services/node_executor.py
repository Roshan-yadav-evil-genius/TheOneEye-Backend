"""
Node Executor Module
Executes nodes with input and form data.
"""

import asyncio
import traceback
from typing import Any, Dict, Optional

from apps.common.exceptions import FormValidationException, ExecutionTimeoutException
from .node_loader import NodeLoader
from .node_session_store import NodeSessionStore


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
        timeout: Optional[float] = None
    ) -> Dict:
        """
        Execute a node with the given input and form data.
        
        Args:
            node_metadata: Node metadata dict.
            input_data: Input data to pass to the node.
            form_data: Form field values.
            session_id: Session ID for stateful execution (reuses instance).
            timeout: Optional timeout in seconds (default: None, no timeout).
            
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
                node_class, node_metadata, input_data, form_data, session_id, timeout
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
                # Clear session on timeout
                self._session_store.clear(session_id)
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
                    from Node.Core.Form.Core.FormSerializer import FormSerializer
                    serializer = FormSerializer(e.form)
                    form_state = serializer.to_json()
                    
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
        Clear a session and its node instance.
        
        Args:
            session_id: Session ID to clear.
            
        Returns:
            True if session was cleared, False if not found.
        """
        return self._session_store.clear(session_id)
    
    def _run_node(
        self, 
        node_class, 
        node_metadata: Dict, 
        input_data: Dict, 
        form_data: Dict,
        session_id: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> Any:
        """
        Run the node asynchronously and return the result.
        
        If session_id is provided, reuses existing instance or creates new one.
        If timeout is provided, execution will be cancelled after timeout seconds.
        """
        from Node.Core.Node.Core.Data import NodeConfig, NodeConfigData, NodeOutput
        
        # Check if we have an existing instance for this session
        node_instance = None
        is_new_instance = False
        
        if session_id:
            node_instance = self._session_store.get(session_id)
        
        if node_instance is None:
            # Create new instance
            node_config = NodeConfig(
                id=f"exec_{node_metadata.get('identifier')}",
                type=node_metadata.get('identifier'),
                data=NodeConfigData(form=form_data)
            )
            node_instance = node_class(node_config)
            is_new_instance = True
            
            # Store in session if session_id provided
            if session_id:
                self._session_store.set(session_id, node_instance)
        else:
            # Update form data on existing instance
            node_instance.node_config.data.form = form_data
        
        # Create NodeOutput from input data
        node_output = NodeOutput(data=input_data)
        
        # Run the node asynchronously
        async def run_async():
            # Only call init on new instances
            if is_new_instance:
                await node_instance.init()
            result = await node_instance.run(node_output)
            
            # Close browser after single node execution to prevent stale contexts
            try:
                from Node.Nodes.Browser._shared.BrowserManager import BrowserManager
                browser_manager = BrowserManager()
                if browser_manager._initialized:
                    await browser_manager.close()
            except ImportError:
                pass  # BrowserManager not available, skip cleanup
            
            return result
        
        # Execute in asyncio event loop with optional timeout
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = None
        try:
            if timeout is not None and timeout > 0:
                # Create task explicitly so we can cancel it forcefully
                task = loop.create_task(run_async())
                try:
                    # Use wait_for to enforce timeout
                    result = loop.run_until_complete(
                        asyncio.wait_for(task, timeout=timeout)
                    )
                except asyncio.TimeoutError:
                    # Timeout occurred - kill the task immediately
                    # Cancel the main task
                    if task and not task.done():
                        task.cancel()
                    
                    # Cancel ALL pending tasks in the loop immediately
                    try:
                        all_tasks = asyncio.all_tasks(loop)
                        for pending_task in all_tasks:
                            if not pending_task.done():
                                pending_task.cancel()
                    except Exception:
                        pass
                    
                    # Clear session immediately (don't wait for cleanup)
                    if session_id:
                        self._session_store.clear(session_id)
                    
                    # Re-raise as TimeoutError to be caught by execute()
                    # Loop will be closed in finally block
                    raise
            else:
                # No timeout, run normally
                result = loop.run_until_complete(run_async())
        except asyncio.TimeoutError:
            # Clear session on timeout
            if session_id:
                self._session_store.clear(session_id)
            raise
        except asyncio.CancelledError:
            # Handle cancellation (can occur during timeout cleanup)
            # Clear session on cancellation
            if session_id:
                self._session_store.clear(session_id)
            raise asyncio.TimeoutError("Node execution was cancelled due to timeout")
        except Exception:
            raise
        finally:
            # Ensure loop is closed
            try:
                if not loop.is_closed():
                    # Cancel any remaining tasks
                    try:
                        all_tasks = asyncio.all_tasks(loop)
                        for pending_task in all_tasks:
                            if not pending_task.done():
                                pending_task.cancel()
                    except Exception:
                        pass
                    loop.close()
            except Exception:
                # Ignore errors during cleanup
                pass
        
        return result

