"""
Node Executor Module
Executes nodes with input and form data.
"""

import asyncio
import traceback
from typing import Any, Dict, Optional

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
        session_id: Optional[str] = None
    ) -> Dict:
        """
        Execute a node with the given input and form data.
        
        Args:
            node_metadata: Node metadata dict.
            input_data: Input data to pass to the node.
            form_data: Form field values.
            session_id: Session ID for stateful execution (reuses instance).
            
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
                node_class, node_metadata, input_data, form_data, session_id
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
            
        except Exception as e:
            traceback.print_exc()
            return {
                'success': False,
                'error': 'Execution failed',
                'error_type': type(e).__name__,
                'details': str(e),
                'identifier': node_metadata.get('identifier')
            }
    
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
        session_id: Optional[str] = None
    ) -> Any:
        """
        Run the node asynchronously and return the result.
        
        If session_id is provided, reuses existing instance or creates new one.
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
        
        # Execute in asyncio event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(run_async())
        finally:
            loop.close()
        
        return result

