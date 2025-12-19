"""
FlowEngine orchestration service.

This module handles FlowEngine lifecycle management and execution.
Follows Single Responsibility Principle - only handles FlowEngine operations.
"""

import sys
import asyncio
import structlog
from typing import Dict, Any, Optional

# Add core to path for imports
sys.path.insert(0, '/home/roshan/main/TheOneEye/Attempt3/core')

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
        
        engine = FlowEngine()
        _running_engines[workflow_id] = engine
        
        try:
            # Load the workflow
            logger.info("Loading workflow into FlowEngine", workflow_id=workflow_id)
            engine.load_workflow(flow_engine_config)
            logger.info("Workflow loaded into FlowEngine", workflow_id=workflow_id)
            
            # Run the workflow in production mode
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(engine.run_production())
                logger.info("Workflow execution completed successfully", workflow_id=workflow_id)
                
                return {
                    "status": "success",
                    "workflow_id": workflow_id,
                    "message": "Workflow execution completed successfully"
                }
            finally:
                # Clean up browser resources
                FlowEngineService._cleanup_browser_resources(loop, workflow_id)
                loop.close()
                
        finally:
            # Clean up engine reference
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
    def _unregister_engine(workflow_id: str) -> None:
        """Remove engine from the running engines registry."""
        if workflow_id in _running_engines:
            del _running_engines[workflow_id]


# Global instance for convenience
flow_engine_service = FlowEngineService()

