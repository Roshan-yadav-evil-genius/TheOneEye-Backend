"""
Celery tasks for node operations.

This module contains Celery tasks for single node execution.
Node execution is handled by the core NodeExecutor.
"""

import json
import structlog
from celery import shared_task
from ..models import WorkFlow, Node, Connection
from ..services.dependency_service import dependency_service

logger = structlog.get_logger(__name__)


@shared_task(bind=True)
def execute_single_node(self, workflow_id: str, node_id: str):
    """
    Execute a single node with all its dependencies.
    Uses the dependency service to resolve dependencies and print execution details.
    """
    try:
        # Get workflow and target node
        workflow = WorkFlow.objects.get(id=workflow_id)
        target_node = Node.objects.get(id=node_id, workflow=workflow)
        
        logger.info("Single node execution started", 
                   workflow_id=str(workflow.id), 
                   workflow_name=workflow.name,
                   target_node_id=str(target_node.id),
                   target_node_type=target_node.node_type or 'Unknown')
        
        # Find all dependencies (nodes that connect to this node)
        dependencies = dependency_service.get_node_dependencies(target_node)
        
        if dependencies:
            logger.info("Dependency tree found", 
                       dependency_count=len(dependencies),
                       dependencies=[{"id": str(dep.id), "type": dep.node_type or f"Node {str(dep.id)[:8]}"} for dep in dependencies])
        else:
            logger.info("No dependencies found")
        
        # Log detailed node information
        _log_node_details(target_node)
        
        # Execute dependencies first (in order)
        for dep in dependencies:
            logger.info("Executing dependency", 
                       dependency_id=str(dep.id),
                       dependency_type=dep.node_type or 'Unknown')
            result = _simulate_node_execution(dep)
            dep.config = result
            dep.save()
            logger.debug("Dependency execution result", 
                       dependency_id=str(dep.id),
                       result=result)
        
        # Execute target node
        logger.info("Executing target node", 
                   target_node_id=str(target_node.id),
                   target_node_type=target_node.node_type or 'Unknown')
        result = _simulate_node_execution(target_node)
        target_node.config = result
        target_node.save()
        logger.debug("Target node execution result", 
                   target_node_id=str(target_node.id),
                   result=result)
        
        logger.info("Single node execution completed",
                   workflow_id=str(workflow.id),
                   target_node_id=str(target_node.id))
        
        return {
            "status": "completed",
            "workflow_id": str(workflow.id),
            "target_node_id": str(target_node.id),
            "dependencies_executed": len(dependencies),
            "result": result
        }
        
    except WorkFlow.DoesNotExist:
        logger.error("Workflow not found", workflow_id=workflow_id)
        return {"status": "error", "error": "Workflow not found"}
    except Node.DoesNotExist:
        logger.error("Node not found in workflow", node_id=node_id, workflow_id=workflow_id)
        return {"status": "error", "node_id": node_id, "error": "Node not found in workflow"}
    except Exception as e:
        logger.error("Error executing single node", 
                    workflow_id=workflow_id, 
                    node_id=node_id,
                    error=str(e), 
                    exc_info=True)
        return {"status": "error", "error": str(e)}


def _log_node_details(node: Node):
    """Log comprehensive node details."""
    incoming = Connection.objects.filter(target_node=node).select_related('source_node')
    outgoing = Connection.objects.filter(source_node=node).select_related('target_node')
    
    incoming_connections = [
        {"id": str(conn.source_node.id), "type": conn.source_node.node_type or f"Node {str(conn.source_node.id)[:8]}"}
        for conn in incoming
    ]
    outgoing_connections = [
        {"id": str(conn.target_node.id), "type": conn.target_node.node_type or f"Node {str(conn.target_node.id)[:8]}"}
        for conn in outgoing
    ]
    
    logger.debug("Node details",
                node_id=str(node.id),
                node_type=node.node_type or 'Unknown',
                position={"x": node.x, "y": node.y},
                form_values=node.form_values,
                incoming_connections=incoming_connections,
                outgoing_connections=outgoing_connections)


def _simulate_node_execution(node: Node):
    """
    Simulate node execution and return mock results.
    In a real implementation, this would use the core NodeExecutor.
    """
    from datetime import datetime
    
    result = {
        "node_id": str(node.id),
        "node_type": node.node_type or "unknown",
        "execution_time": datetime.now().isoformat(),
        "status": "success",
        "output_data": {
            "processed_items": 1,
            "result": f"Mock execution result for {node.node_type or 'Unknown'}",
            "form_values_used": node.form_values,
            "configuration": node.config
        }
    }
    
    return result
