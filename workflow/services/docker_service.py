"""
Docker container lifecycle management service.

This module handles all Docker operations including container creation,
management, and communication with the command server.
"""

import json
import time
import requests
import docker
from typing import Optional, Dict, Any


class DockerService:
    """Service for managing Docker containers and operations."""
    
    def __init__(self):
        self.client = docker.from_env()
        self.image_name = "theoneeyecore"
    
    def image_exists(self, image_name: Optional[str] = None) -> bool:
        """Check if the Docker image exists."""
        image_name = image_name or self.image_name
        try:
            self.client.images.get(image_name)
            print(f"[+] {image_name} Image Found")
            return True
        except docker.errors.ImageNotFound:
            print(f"[-] {image_name} Image Not Found")
            return False
    
    def container_exists(self, container_name: str) -> bool:
        """Check if a container with the given name exists."""
        try:
            self.client.containers.get(container_name)
            return True
        except docker.errors.NotFound:
            return False
    
    def get_container(self, container_name: str):
        """Get a container by name."""
        try:
            return self.client.containers.get(container_name)
        except docker.errors.NotFound:
            return None
    
    def stop_container(self, container_name: str) -> bool:
        """Stop a running container."""
        try:
            container = self.client.containers.get(container_name)
            container.stop()
            print(f"[+] Container {container_name} stopped")
            return True
        except docker.errors.NotFound:
            print(f"[-] Container {container_name} not found")
            return False
        except Exception as e:
            print(f"[-] Error stopping container {container_name}: {e}")
            return False
    
    def remove_container(self, container_name: str, force: bool = True) -> bool:
        """Remove a container."""
        try:
            container = self.client.containers.get(container_name)
            container.remove(force=force)
            print(f"[+] Container {container_name} removed")
            return True
        except docker.errors.NotFound:
            print(f"[-] Container {container_name} not found")
            return False
        except Exception as e:
            print(f"[-] Error removing container {container_name}: {e}")
            return False
    
    def kill_and_remove(self, container_name: str) -> bool:
        """Kill and remove a container."""
        try:
            container = self.client.containers.get(container_name)
            container.remove(force=True)
            print(f"[+] {container_name} killed & removed")
            return True
        except docker.errors.NotFound:
            print(f"[-] {container_name} not found")
            return False
        except Exception as e:
            print(f"[-] Error killing and removing {container_name}: {e}")
            return False
    
    def create_workflow_container(self, workflow_id: str, workflow_config: Dict[str, Any]) -> Optional[Any]:
        """Create a temporary container for full workflow execution."""
        if not self.image_exists():
            print(f"[-] {self.image_name} Image does not exist")
            return None
        
        # Remove existing container if it exists
        if self.container_exists(workflow_id):
            self.kill_and_remove(workflow_id)
        
        try:
            container = self.client.containers.run(
                image=self.image_name,
                name=workflow_id,
                remove=True,  # Auto-remove when finished
                environment={
                    "CELERY_TASK_ID": workflow_config.get("task_id", ""),
                    "CONFIG_JSON": json.dumps(workflow_config, default=str)
                },
                command=[
                    "sh", "-c",
                    """
                    # Run main script
                    python -u main.py
                    """
                ],
                detach=True
            )
            print(f"[+] Workflow container {workflow_id} created")
            return container
        except Exception as e:
            print(f"[-] Error creating workflow container: {e}")
            return None
    
    def create_dev_container(self, workflow_id: str, workflow_config: Dict[str, Any]) -> Optional[Any]:
        """Create a persistent container for development mode."""
        dev_container_name = f"{workflow_id}-dev"
        
        # Check if dev container already exists and is running
        existing_container = self.get_container(dev_container_name)
        if existing_container:
            if existing_container.status == 'running':
                print(f"[+] Dev container {dev_container_name} already running")
                return existing_container
            else:
                print(f"[+] Dev container {dev_container_name} exists but not running, removing...")
                self.remove_container(dev_container_name, force=True)
        
        try:
            container = self.client.containers.run(
                image=self.image_name,
                name=dev_container_name,
                remove=False,  # Don't auto-remove for dev containers
                environment={
                    "CONFIG_JSON": json.dumps(workflow_config, default=str)
                },
                command=[
                    "sh", "-c",
                    """
                    # Run command server instead of main.py
                    python -u command_server.py
                    """
                ],
                ports={'5000/tcp': None},  # Expose port 5000
                detach=True
            )
            
            # Wait for the server to start
            time.sleep(3)
            print(f"[+] Dev container {dev_container_name} created")
            return container
        except Exception as e:
            print(f"[-] Error creating dev container: {e}")
            return None
    
    def get_container_port(self, container_name: str, internal_port: int = 5000) -> Optional[int]:
        """Get the mapped port for a container."""
        try:
            container = self.client.containers.get(container_name)
            container.reload()
            port_mapping = container.attrs['NetworkSettings']['Ports'].get(f'{internal_port}/tcp')
            if not port_mapping:
                return None
            return int(port_mapping[0]['HostPort'])
        except Exception as e:
            print(f"[-] Error getting container port: {e}")
            return None
    
    def send_command_to_container(self, container_name: str, endpoint: str, data: Dict[str, Any], timeout: int = 30) -> Optional[Dict[str, Any]]:
        """Send HTTP request to container's command server."""
        try:
            port = self.get_container_port(container_name)
            if not port:
                raise Exception(f"Port 5000 not mapped for container {container_name}")
            
            server_url = f"http://localhost:{port}"
            response = requests.post(
                f"{server_url}{endpoint}",
                json=data,
                timeout=timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            print(f"[-] Error sending command to container: {e}")
            return None
    
    def execute_node_in_container(self, container_name: str, node_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute a node in the container's command server."""
        return self.send_command_to_container(
            container_name=container_name,
            endpoint="/execute_node",
            data={
                "node_id": node_id,
                "payload": payload
            }
        )
    
    def health_check_container(self, container_name: str) -> Optional[Dict[str, Any]]:
        """Check if the container's command server is healthy."""
        return self.send_command_to_container(
            container_name=container_name,
            endpoint="/health",
            data={}
        )


# Global instance for backward compatibility
docker_service = DockerService()
