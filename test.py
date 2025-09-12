import docker
from docker.client import DockerClient
from docker.models.containers import Container
import json

client = docker.from_env()


def TheOneEyeCoreImageExist(client: DockerClient):
    try:
        client.images.get("theoneeyecore")
        print("[+] theoneeyecore Image Found")
        return True
    except docker.errors.ImageNotFound as e:
        print("[-] theoneeyecore Image Not Found")
        return False


def buildTheOneEyeCoreImage(client: DockerClient):
    print("[+] Building theoneeyecore Image")
    client.images.build(
        path="/home/roshan/main/TheOneEye/core",
        tag="theoneeyecore"
    )


def initiateTheOneEyeCoreContainer(client: DockerClient, task_id: str, config: str)->Container:
    print("[+] Executing theoneeyecore Image")

    container = client.containers.run(
        image="theoneeyecore",
        detach=True,
        environment={
            "CELERY_TASK_ID": task_id,
            "CONFIG_JSON": config  # pass JSON safely as env variable
        },
        # remove=True,
        command=[
            "sh", "-c",
            """
            # Run main script
            python -u  main.py
            """
        ]
    )
    return container

def moniotorUsage(container: Container):
    stats_stream = container.stats(stream=True)
    for stat in stats_stream:
        data = json.loads(stat)
        cpu = data["cpu_stats"]["cpu_usage"]["total_usage"]
        mem = data["memory_stats"]["usage"]
        net = data["networks"]["eth0"]["rx_bytes"] + data["networks"]["eth0"]["tx_bytes"]

        print(f"CPU: {cpu}, MEM: {mem}, NET: {net}")

with open("config.json","r") as file:
    config=file.read()

if TheOneEyeCoreImageExist(client):
    container = initiateTheOneEyeCoreContainer(client,"4567890",config)
    moniotorUsage(container)

