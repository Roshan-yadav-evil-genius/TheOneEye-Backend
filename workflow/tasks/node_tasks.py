"""
Celery tasks for node operations.

This module contains Celery tasks for single node execution.
Node execution is handled by the core NodeExecutor.
"""

import json
from celery import shared_task
from ..models import WorkFlow, Node, Connection
from ..services.dependency_service import dependency_service


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
        
        print("=" * 50)
        print("=== Single Node Execution ===")
        print(f"Workflow: {workflow.name} (ID: {workflow.id})")
        print(f"Target Node: {target_node.node_type or 'Unknown'} (ID: {target_node.id})")
        print()
        
        # Find all dependencies (nodes that connect to this node)
        dependencies = dependency_service.get_node_dependencies(target_node)
        
        print("--- Dependency Tree ---")
        if dependencies:
            for i, dep in enumerate(dependencies, 1):
                dep_name = dep.node_type or f"Node {str(dep.id)[:8]}"
                print(f"{i}. {dep_name} (ID: {dep.id})")
        else:
            print("No dependencies found")
        print()
        
        # Print detailed node information
        _print_node_details(target_node)
        
        # Execute dependencies first (in order)
        for dep in dependencies:
            print(f"\n--- Executing Dependency: {dep.node_type or 'Unknown'} ---")
            result = _simulate_node_execution(dep)
            dep.config = result
            dep.save()
            print(f"Result: {json.dumps(result, indent=2)}")
        
        # Execute target node
        print(f"\n--- Executing Target Node: {target_node.node_type or 'Unknown'} ---")
        result = _simulate_node_execution(target_node)
        target_node.config = result
        target_node.save()
        print(f"Result: {json.dumps(result, indent=2)}")
        
        print("=" * 50)
        print("=== Execution Complete ===")
        
        return {
            "status": "completed",
            "workflow_id": str(workflow.id),
            "target_node_id": str(target_node.id),
            "dependencies_executed": len(dependencies),
            "result": result
        }
        
    except WorkFlow.DoesNotExist:
        print(f"[-] Workflow {workflow_id} not found")
        return {"status": "error", "error": "Workflow not found"}
    except Node.DoesNotExist:
        print(f"[-] Node {node_id} not found in workflow {workflow_id}")
        return {"status": "error", "node_id": node_id, "error": "Node not found in workflow"}
    except Exception as e:
        print(f"Error executing single node: {str(e)}")
        return {"status": "error", "error": str(e)}


def _print_node_details(node: Node):
    """Print comprehensive node details."""
    print("--- Node Details ---")
    print(f"ID: {node.id}")
    print(f"Type: {node.node_type or 'Unknown'}")
    print(f"Position: ({node.x}, {node.y})")
    print(f"Form Values: {json.dumps(node.form_values, indent=2)}")
    
    # Print connections
    print("--- Connections ---")
    incoming = Connection.objects.filter(target_node=node).select_related('source_node')
    outgoing = Connection.objects.filter(source_node=node).select_related('target_node')
    
    print("Incoming:")
    for conn in incoming:
        source_name = conn.source_node.node_type or f"Node {str(conn.source_node.id)[:8]}"
        print(f"  - From: {source_name} (ID: {conn.source_node.id})")
    
    print("Outgoing:")
    for conn in outgoing:
        target_name = conn.target_node.node_type or f"Node {str(conn.target_node.id)[:8]}"
        print(f"  - To: {target_name} (ID: {conn.target_node.id})")


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
