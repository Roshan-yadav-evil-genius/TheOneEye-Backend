import json
import docker
from celery import shared_task
from .models import WorkFlow, Node, Connection
from celery.result import AsyncResult


client = docker.from_env()
imageName = "theoneeyecore"


def image_exists():
    try:
        client.images.get(imageName)
        print("[+] theoneeyecore Image Found")
        return True
    except docker.errors.ImageNotFound as e:
        print("[-] theoneeyecore Image Not Found")
        return False

def container_exists(name: str) -> bool:
    try:
        client.containers.get(name)
        return True
    except docker.errors.NotFound:
        return False

def kill_and_remove(name: str):
    try:
        container = client.containers.get(name)
        container.remove(force=True)   # remove container
        print(f"{name} killed & removed")
    except docker.errors.NotFound:
        print(f"{name} not found")

@shared_task(bind=True)
def execute_workflow(self, workflow_config: dict):
    if not image_exists():
        print(f"[+] {imageName} Image Not exist")
        return

    workflow_id = workflow_config.get("id", None)
    workflow: WorkFlow = WorkFlow.objects.get(id=workflow_id)

    if container_exists(workflow_id):
        kill_and_remove(workflow_id)

    print(f"[+] {workflow_id} Workflow Execution started")
    self.update_state(
            state='STARTED',
            meta={'workflow_id': workflow_id}
        )

    try:
        container = client.containers.run(
            image=imageName,
            name=workflow_id,
            remove=True,
            environment={
                "CELERY_TASK_ID": workflow.task_id,
                "CONFIG_JSON": json.dumps(workflow_config,default=str)
            },
            command=[
                "sh", "-c",
                """
                # Run main script
                python -u  main.py
                """
            ]
        )
    except Exception as e:
        print("Error: ",e)
    workflow: WorkFlow = WorkFlow.objects.get(id=workflow_id)
    workflow.task_id = None
    workflow.save()


@shared_task(bind=True)
def stop_workflow(self, workflow_id: str):
    workflow: WorkFlow = WorkFlow.objects.get(id=workflow_id)

    if container_exists(workflow_id):
        kill_and_remove(workflow_id)
    
    executionTask:AsyncResult =  AsyncResult(workflow.task_id)

    executionTask.revoke(terminate=True,signal="SIGKILL")
    
    workflow.task_id = None
    workflow.save()


@shared_task(bind=True)
def execute_single_node(self, workflow_id: str, node_id: str):
    """
    Execute a single node with all its dependencies.
    Prints detailed node information and stores execution results.
    """
    try:
        # Get workflow and target node
        workflow = WorkFlow.objects.get(id=workflow_id)
        target_node = Node.objects.get(id=node_id, workflow=workflow)
        
        print("=" * 50)
        print("=== Single Node Execution ===")
        print(f"Workflow: {workflow.name} (ID: {workflow.id})")
        print(f"Target Node: {target_node.node_type.name if target_node.node_type else 'Unknown'} (ID: {target_node.id})")
        print()
        
        # Find all dependencies (nodes that connect to this node)
        dependencies = find_node_dependencies(target_node)
        
        print("--- Dependency Tree ---")
        if dependencies:
            for i, dep in enumerate(dependencies, 1):
                dep_name = dep.node_type.name if dep.node_type else f"Node {str(dep.id)[:8]}"
                print(f"{i}. {dep_name} (ID: {dep.id})")
        else:
            print("No dependencies found")
        print()
        
        # Print detailed node information
        print_node_details(target_node)
        
        # Execute dependencies first (in order)
        for dep in dependencies:
            print(f"\n--- Executing Dependency: {dep.node_type.name if dep.node_type else 'Unknown'} ---")
            result = simulate_node_execution(dep)
            dep.output = result
            dep.save()
            print(f"Result: {json.dumps(result, indent=2)}")
        
        # Execute target node
        print(f"\n--- Executing Target Node: {target_node.node_type.name if target_node.node_type else 'Unknown'} ---")
        result = simulate_node_execution(target_node)
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


def find_node_dependencies(node: Node):
    """
    Find all nodes that the given node depends on (incoming connections).
    Returns a list of nodes in execution order (dependencies first).
    """
    dependencies = []
    visited = set()
    
    def collect_dependencies(current_node):
        if current_node.id in visited:
            return
        visited.add(current_node.id)
        
        # Find all incoming connections (nodes that connect TO this node)
        incoming_connections = Connection.objects.filter(
            target_node=current_node
        ).select_related('source_node')
        
        for connection in incoming_connections:
            source_node = connection.source_node
            collect_dependencies(source_node)
            if source_node not in dependencies:
                dependencies.append(source_node)
    
    collect_dependencies(node)
    return dependencies


def print_node_details(node: Node):
    """Print comprehensive node details"""
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


def simulate_node_execution(node: Node):
    """
    Simulate node execution and return mock results.
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