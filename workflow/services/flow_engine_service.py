"""
FlowEngine orchestration service.

This module handles FlowEngine lifecycle management and execution.
Follows Single Responsibility Principle - only handles FlowEngine operations.
"""

import sys
import asyncio
import structlog
from datetime import datetime
from typing import Dict, Any, Optional

# Add core to path for imports
sys.path.insert(0, '/home/roshan/main/TheOneEye/Attempt3/core')

from .websocket_broadcaster import websocket_broadcaster
from .redis_state_store import redis_state_store

logger = structlog.get_logger(__name__)

# Global reference to track running engines for shutdown
_running_engines: Dict[str, Any] = {}


class FlowEngineService:
    """Service for managing FlowEngine lifecycle and execution."""
    
    @staticmethod
    def run_workflow(workflow_id: str, flow_engine_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a workflow using the FlowEngine.
        
        Args:
            workflow_id: The workflow UUID as string
            flow_engine_config: Configuration in FlowEngine format
            
        Returns:
            Dict with execution status and results
        """
        from Workflow.flow_engine import FlowEngine
        from Workflow.events import WorkflowEventEmitter
        
        engine = FlowEngine(workflow_id=workflow_id)
        _running_engines[workflow_id] = engine
        
        try:
            # Load the workflow
            logger.info("Loading workflow into FlowEngine", workflow_id=workflow_id)
            engine.load_workflow(flow_engine_config)
            logger.info("Workflow loaded into FlowEngine", workflow_id=workflow_id)
            
            # Initialize state in Redis (cross-process accessible)
            total_nodes = len(engine.flow_graph.node_map)
            redis_state_store.start_workflow(workflow_id, total_nodes)
            
            # Subscribe to events for WebSocket broadcasting AND Redis state updates
            FlowEngineService._subscribe_to_events(workflow_id, engine.events)
            
            # Run the workflow in production mode
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(engine.run_production())
                logger.info("Workflow execution completed successfully", workflow_id=workflow_id)
                
                # Mark workflow as completed in Redis
                redis_state_store.complete_workflow(workflow_id, "completed")
                
                # Broadcast workflow completed
                state = redis_state_store.get_state(workflow_id)
                duration = state.get("total_duration_seconds", 0.0) if state else 0.0
                websocket_broadcaster.broadcast_workflow_completed(
                    workflow_id, "success", duration
                )
                
                return {
                    "status": "success",
                    "workflow_id": workflow_id,
                    "message": "Workflow execution completed successfully"
                }
            except Exception as e:
                # Mark workflow as failed in Redis
                redis_state_store.fail_workflow(workflow_id, str(e))
                # Broadcast workflow failed
                websocket_broadcaster.broadcast_workflow_failed(workflow_id, str(e))
                raise
            finally:
                # Clean up browser resources
                FlowEngineService._cleanup_browser_resources(loop, workflow_id)
                loop.close()
                
        finally:
            # Clean up engine references
            FlowEngineService._unregister_engine(workflow_id)
    
    @staticmethod
    def shutdown_engine(workflow_id: str) -> bool:
        """
        Force shutdown a running FlowEngine.
        
        Args:
            workflow_id: The workflow UUID as string
            
        Returns:
            True if engine was found and shut down, False otherwise
        """
        if workflow_id not in _running_engines:
            return False
        
        engine = _running_engines[workflow_id]
        logger.info("Force shutting down FlowEngine", workflow_id=workflow_id)
        engine.force_shutdown()
        FlowEngineService._unregister_engine(workflow_id)
        
        # Clean up browser resources in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            FlowEngineService._cleanup_browser_resources(loop, workflow_id, on_stop=True)
        finally:
            loop.close()
        
        return True
    
    @staticmethod
    def is_engine_running(workflow_id: str) -> bool:
        """
        Check if a FlowEngine is currently running for a workflow.
        
        Args:
            workflow_id: The workflow UUID as string
            
        Returns:
            True if engine is running, False otherwise
        """
        return workflow_id in _running_engines
    
    @staticmethod
    def _cleanup_browser_resources(loop: asyncio.AbstractEventLoop, workflow_id: str, on_stop: bool = False) -> None:
        """
        Clean up browser resources after workflow execution.
        
        Args:
            loop: The event loop to use for async cleanup
            workflow_id: The workflow UUID for logging
            on_stop: Whether cleanup is happening due to stop command
        """
        try:
            from Node.Nodes.Browser.BrowserManager import BrowserManager
            browser_manager = BrowserManager()
            loop.run_until_complete(browser_manager.close())
            
            if on_stop:
                logger.info("Browser resources cleaned up on stop", workflow_id=workflow_id)
            else:
                logger.info("Browser resources cleaned up", workflow_id=workflow_id)
        except Exception as browser_cleanup_error:
            if on_stop:
                logger.warning("Error cleaning up browser resources on stop", error=str(browser_cleanup_error))
            else:
                logger.warning("Error cleaning up browser resources", error=str(browser_cleanup_error))
    
    @staticmethod
    def _subscribe_to_events(workflow_id: str, events) -> None:
        """
        Subscribe to FlowEngine events for Redis state updates and WebSocket broadcasting.
        
        Args:
            workflow_id: The workflow ID
            events: The WorkflowEventEmitter instance
        """
        from Workflow.events import WorkflowEventEmitter
        
        # Subscribe to node_started events
        def on_node_started(data: Dict[str, Any]):
            node_id = data.get("node_id")
            node_type = data.get("node_type")
            
            # Update Redis state
            redis_state_store.update_node_started(workflow_id, node_id, node_type)
            
            # Broadcast via WebSocket
            websocket_broadcaster.broadcast_node_started(
                workflow_id=workflow_id,
                node_id=node_id,
                node_type=node_type,
                started_at=datetime.utcnow().isoformat() + "Z"
            )
        events.subscribe(WorkflowEventEmitter.NODE_STARTED, on_node_started)
        
        # Subscribe to node_completed events
        def on_node_completed(data: Dict[str, Any]):
            node_id = data.get("node_id")
            node_type = data.get("node_type")
            route = data.get("route")
            
            # Update Redis state and get duration
            duration = redis_state_store.update_node_completed(
                workflow_id, node_id, node_type, route
            )
            
            # Broadcast via WebSocket
            websocket_broadcaster.broadcast_node_completed(
                workflow_id=workflow_id,
                node_id=node_id,
                node_type=node_type,
                duration=duration,
                route=route,
                output_data=data.get("output_data")
            )
        events.subscribe(WorkflowEventEmitter.NODE_COMPLETED, on_node_completed)
        
        # Subscribe to node_failed events
        def on_node_failed(data: Dict[str, Any]):
            node_id = data.get("node_id")
            node_type = data.get("node_type")
            error = data.get("error")
            
            # Update Redis state
            redis_state_store.update_node_failed(workflow_id, node_id, node_type, error)
            
            # Broadcast via WebSocket
            websocket_broadcaster.broadcast_node_failed(
                workflow_id=workflow_id,
                node_id=node_id,
                node_type=node_type,
                error=error
            )
        events.subscribe(WorkflowEventEmitter.NODE_FAILED, on_node_failed)
        
        logger.info("Subscribed to FlowEngine events", workflow_id=workflow_id)
    
    @staticmethod
    def _unregister_engine(workflow_id: str) -> None:
        """Remove engine from the running engines registry."""
        if workflow_id in _running_engines:
            del _running_engines[workflow_id]


# Global instance for convenience
flow_engine_service = FlowEngineService()

