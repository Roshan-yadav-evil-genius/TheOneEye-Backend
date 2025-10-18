"""
Celery tasks for node operations.

This module contains Celery tasks for single node execution and development mode.
"""

import json
from celery import shared_task
from ..models import WorkFlow, Node
from ..services.docker_service import docker_service
from ..services.workflow_config_service import workflow_config_service
from ..services.node_execution_service import node_execution_service


@shared_task(bind=True)
def execute_single_node_incremental(self, workflow_id: str, node_id: str):
    """
    Execute a single node using persistent container with stateful node instances.
    This is the new incremental execution task for development mode.
    """
    try:
        # Get workflow and target node
        workflow = WorkFlow.objects.get(id=workflow_id)
        target_node = Node.objects.get(id=node_id, workflow=workflow)
        
        print(f"[+] Starting incremental execution of node {target_node.node_type.name if target_node.node_type else 'Unknown'}")
        
        # Build workflow config
        workflow_config = workflow_config_service.build_workflow_config(workflow)
        
        # Create or get dev container
        dev_container_name = f"{workflow_id}-dev"
        container = docker_service.get_container(dev_container_name)
        
        if not container or container.status != 'running':
            print(f"[+] Creating persistent dev container: {dev_container_name}")
            container = docker_service.create_dev_container(workflow_id, workflow_config)
            
            if not container:
                return {
                    "status": "error",
                    "node_id": node_id,
                    "error": "Failed to create dev container"
                }
        
        # Execute the node using the orchestration service
        result = node_execution_service.execute_node_with_dependencies(workflow_id, node_id)
        
        if result.get("status") == "success":
            print(f"[+] Node execution successful: {result.get('result')}")
        else:
            print(f"[-] Node execution failed: {result.get('error')}")
        
        return result
        
    except WorkFlow.DoesNotExist:
        print(f"[-] Workflow {workflow_id} not found")
        return {
            "status": "error",
            "node_id": node_id,
            "error": "Workflow not found"
        }
    except Node.DoesNotExist:
        print(f"[-] Node {node_id} not found in workflow {workflow_id}")
        return {
            "status": "error",
            "node_id": node_id,
            "error": "Node not found in workflow"
        }
    except Exception as e:
        print(f"[-] Error in incremental execution: {str(e)}")
        return {
            "status": "error",
            "node_id": node_id,
            "error": str(e)
        }


@shared_task(bind=True)
def stop_dev_container(self, workflow_id: str):
    """
    Stop and remove the persistent dev container for a workflow.
    """
    try:
        dev_container_name = f"{workflow_id}-dev"
        
        if docker_service.container_exists(dev_container_name):
            print(f"[+] Stopping dev container: {dev_container_name}")
            success = docker_service.kill_and_remove(dev_container_name)
            if success:
                print(f"[+] Dev container {dev_container_name} stopped and removed")
                return {"status": "success", "message": f"Dev container {dev_container_name} stopped"}
            else:
                return {"status": "error", "error": f"Failed to stop dev container {dev_container_name}"}
        else:
            print(f"[+] Dev container {dev_container_name} not found")
            return {"status": "success", "message": f"Dev container {dev_container_name} not found"}
            
    except Exception as e:
        print(f"[-] Error stopping dev container: {str(e)}")
        return {"status": "error", "error": str(e)}


@shared_task(bind=True)
def execute_single_node(self, workflow_id: str, node_id: str):
    """
    Execute a single node with all its dependencies (legacy mock version).
    This is kept for backward compatibility but uses mock execution.
    """
    try:
        # Get workflow and target node
        workflow = WorkFlow.objects.get(id=workflow_id)
        target_node = Node.objects.get(id=node_id, workflow=workflow)
        
        print("=" * 50)
        print("=== Single Node Execution (Legacy Mock) ===")
        print(f"Workflow: {workflow.name} (ID: {workflow.id})")
        print(f"Target Node: {target_node.node_type.name if target_node.node_type else 'Unknown'} (ID: {target_node.id})")
        print()
        
        # Find all dependencies (nodes that connect to this node)
        dependencies = node_execution_service.dependency_service.get_node_dependencies(target_node)
        
        print("--- Dependency Tree ---")
        if dependencies:
            for i, dep in enumerate(dependencies, 1):
                dep_name = dep.node_type.name if dep.node_type else f"Node {str(dep.id)[:8]}"
                print(f"{i}. {dep_name} (ID: {dep.id})")
        else:
            print("No dependencies found")
        print()
        
        # Print detailed node information
        _print_node_details(target_node)
        
        # Execute dependencies first (in order) - MOCK EXECUTION
        for dep in dependencies:
            print(f"\n--- Executing Dependency: {dep.node_type.name if dep.node_type else 'Unknown'} ---")
            result = _simulate_node_execution(dep)
            dep.output = result
            dep.save()
            print(f"Result: {json.dumps(result, indent=2)}")
        
        # Execute target node - MOCK EXECUTION
        print(f"\n--- Executing Target Node: {target_node.node_type.name if target_node.node_type else 'Unknown'} ---")
        result = _simulate_node_execution(target_node)
        target_node.output = result
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
        
    except Exception as e:
        print(f"Error executing single node: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


def _print_node_details(node: Node):
    """Print comprehensive node details (legacy function)."""
    print("--- Node Details ---")
    print(f"ID: {node.id}")
    print(f"Type: {node.node_type.type if node.node_type else 'Unknown'}")
    print(f"Name: {node.node_type.name if node.node_type else 'Unknown'}")
    print(f"Position: ({node.x}, {node.y})")
    print(f"Form Values: {json.dumps(node.form_values, indent=2)}")
    
    if node.node_type:
        print(f"StandaloneNode Template:")
        print(f"  - ID: {node.node_type.id}")
        print(f"  - Description: {node.node_type.description}")
        print(f"  - Version: {node.node_type.version}")
        print(f"  - Form Configuration: {json.dumps(node.node_type.form_configuration, indent=2)}")
        print(f"  - Tags: {json.dumps(node.node_type.tags, indent=2)}")
    
    # Print connections
    print("--- Connections ---")
    from ..models import Connection
    incoming = Connection.objects.filter(target_node=node).select_related('source_node')
    outgoing = Connection.objects.filter(source_node=node).select_related('target_node')
    
    print("Incoming:")
    for conn in incoming:
        source_name = conn.source_node.node_type.name if conn.source_node.node_type else f"Node {str(conn.source_node.id)[:8]}"
        print(f"  - From: {source_name} (ID: {conn.source_node.id})")
    
    print("Outgoing:")
    for conn in outgoing:
        target_name = conn.target_node.node_type.name if conn.target_node.node_type else f"Node {str(conn.target_node.id)[:8]}"
        print(f"  - To: {target_name} (ID: {conn.target_node.id})")


def _simulate_node_execution(node: Node):
    """
    Simulate node execution and return mock results (legacy function).
    In a real implementation, this would execute the actual node logic.
    """
    # Mock execution result based on node type and configuration
    result = {
        "node_id": str(node.id),
        "node_name": node.node_type.name if node.node_type else "Unknown",
        "node_type": node.node_type.type if node.node_type else "unknown",
        "execution_time": "2024-01-01T12:00:00Z",  # Mock timestamp
        "status": "success",
        "output_data": {
            "processed_items": 1,
            "result": f"Mock execution result for {node.node_type.name if node.node_type else 'Unknown'}",
            "form_values_used": node.form_values,
            "configuration": node.data
        }
    }
    
    # Add type-specific mock data
    if node.node_type and node.node_type.type == "trigger":
        result["output_data"]["triggered"] = True
        result["output_data"]["event_data"] = {"source": "mock_trigger"}
    elif node.node_type and node.node_type.type == "action":
        result["output_data"]["action_performed"] = True
        result["output_data"]["action_result"] = "Mock action completed"
    elif node.node_type and node.node_type.type == "logic":
        result["output_data"]["logic_result"] = True
        result["output_data"]["condition_met"] = True
    
    return result

