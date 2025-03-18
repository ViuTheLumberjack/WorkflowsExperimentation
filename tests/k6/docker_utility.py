import os
import io
import yaml
import subprocess
import time
from utility import TEST_SERVICE

DOCKER_COMPOSE_FILE_FOLDER = os.path.join(os.path.dirname(__file__), "dockerfiles")

SERVICE_TEMPLATE = {
    "image": "jboss/wildfly:latest",
    "container_name": "{CONTAINER_NAME}",
    "ports":[
        "{HOST_PORT}:8080"
    ],
    "cpuset": '{CPUSET}',
    "deploy":{
        "resources":{
            "limits":{
                "cpus": '{CPUS}',
                "memory": '1024M',
            }
        }
    },
    "volumes": [
        "../../../target/ROOT.war:/opt/jboss/wildfly/standalone/deployments/ROOT.war"
    ]
}

def create_containers(cpu_list: list, n: int = 1):
    # create the docker-compose file and save it
    service_containers = {
        "exponentialop": 1,
        "exponential": 1,
        "erlang": 1,
        "sum": 1,
        "uniform": 1,
        "sequential": n
    }

    docker_file_dict = {
        "services": {} ,
    }

    num_services = service_containers[TEST_SERVICE]


    for i in range(num_services):
        service = SERVICE_TEMPLATE.copy()

        service["container_name"] = f"{TEST_SERVICE}_{i}"
        service["ports"] = [f"{8080 + i}:8080"]
        service["cpuset"] = f"{i}"
        service["deploy"]["resources"]["limits"]["cpus"] = f"{cpu_list[i]}"

        docker_file_dict["services"][f"service_{i}"] = service

    DOCKER_COMPOSE_FILE_PATH = os.path.join(DOCKER_COMPOSE_FILE_FOLDER, f"docker-compose-{TEST_SERVICE}-{cpu_list}.yml")

    with io.open(DOCKER_COMPOSE_FILE_PATH, 'w', encoding='utf8') as outfile:
        yaml.dump(docker_file_dict, outfile, default_flow_style=False, allow_unicode=True)

    # run the docker-compose up command
    subprocess.run(['docker', 'compose', '-f', DOCKER_COMPOSE_FILE_PATH, 'up', '-d'])
    
    # wait for the services to start
    while True:
        try:
            subprocess.run(['curl', f'http://localhost:{8080}'], check=True)
            break
        except subprocess.CalledProcessError:
            print("Waiting for the services to start")
            time.sleep(10)


def stop_containers(delete_containers: bool = True):
    if delete_containers:
        # run the docker-compose down command
        subprocess.run(['docker', 'compose', 'down'])
    else:
        # run the docker-compose stop command
        subprocess.run(['docker', 'compose', 'stop'])