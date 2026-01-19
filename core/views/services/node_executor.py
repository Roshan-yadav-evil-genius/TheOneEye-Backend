"""
Node Executor Module
Executes nodes with input and form data.
"""

import traceback
import threading
from typing import Any, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from apps.common.exceptions import FormValidationException, ExecutionTimeoutException
from .node_loader import NodeLoader
from .node_session_store import NodeSessionStore


class NodeExecutor:
    """
    Executes nodes synchronously with input and form data.
    
    Responsibilities:
    - Create or reuse node instances with configuration
    - Execute nodes with input data
    - Handle synchronous execution
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
            
        except FuturesTimeoutError:
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
        Run the node synchronously and return the result.
        
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
        
        def run_sync():
            """Synchronous node execution."""
            # Only call init on new instances
            if is_new_instance:
                node_instance.init()
            result = node_instance.run(node_output)
            
            # Close browser after single node execution to prevent stale contexts
            try:
                from Node.Nodes.Browser._shared.BrowserManager import BrowserManager
                browser_manager = BrowserManager()
                if browser_manager._initialized:
                    browser_manager.close()
            except ImportError:
                pass  # BrowserManager not available, skip cleanup
            
            return result
        
        # Execute with optional timeout using ThreadPoolExecutor
        if timeout is not None and timeout > 0:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_sync)
                try:
                    result = future.result(timeout=timeout)
                except FuturesTimeoutError:
                    # Timeout occurred - clean up
                    if session_id:
                        self._session_store.clear(session_id)
                    raise
        else:
            # No timeout, run directly
            result = run_sync()
        
        return result
