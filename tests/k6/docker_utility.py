import sys
import os
import io
import copy
import subprocess
import time
import math
from ruamel.yaml import YAML, representer
from utility import TEST_SERVICE

DOCKER_COMPOSE_FILE_FOLDER = os.path.join(os.path.dirname(__file__), "dockerfiles")

SERVICE_TEMPLATE = {
    "image": "jboss/wildfly:latest",
    "container_name": "{CONTAINER_NAME}",
    "ports":[
        "{HOST_PORT}:8080"
    ],
    "cpuset": '{CPUSET}',
    "environment" : [
        "JAVA_TOOL_OPTIONS=\"-javaagent:/usr/local/opentelemetry-javaagent.jar\"",
        "OTEL_SERVICE_NAME={CONTAINER_NAME}",
        "OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317",
        "OTEL_EXPORTER_OTLP_PROTOCOL=grpc",
        "OTEL_LOGS_EXPORTER=none",
        "OTEL_METRICS_EXPORTER=none"
    ],
    "deploy":{
        "resources":{
            "limits":{
                "cpus": '{CPUS}',
                "memory": '1024M',
            }
        }
    },
    "volumes": [
        "$HOME$/target/ROOT.war:/opt/jboss/wildfly/standalone/deployments/ROOT.war",
        "$HOME$/opentelemetry-javaagent.jar:/usr/local/opentelemetry-javaagent.jar"
    ]
}

SERVICES = [
]

def find_project_root(start_path: os.path, marker=".git"):
    current = os.path.abspath(start_path)
    while True:
        if marker in os.listdir(current):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            raise FileNotFoundError(f"Marker '{marker}' not found.")
        current = parent

def create_docker_compose_file(cpu_list: list):
    docker_file_dict = {
        "services": {} ,
    }

    docker_file_dict["services"]["jaeger"] = {
        "image": "jaegertracing/jaeger:2.5.0",
        "container_name": "jaeger",
        "ports": [
            "5775:5775/udp",
            "6831:6831/udp",
            "6832:6832/udp",
            "5778:5778",
            "16686:16686",
            "5779:5779",
            "14268:14268",
            "14250:14250",
            "14267:14267",
            "4317:4317",
            "4318:4318"
        ]
    }

    num_services = len(cpu_list)
    offset = 0
    project_dir = find_project_root(os.path.dirname(__file__))
    
    for i in range(num_services):
        service = copy.deepcopy(SERVICE_TEMPLATE)

        cpus = [str(cpu + offset) for cpu in range(cpu_list[i])] if cpu_list[i] >= 1 else [str(int(math.ceil(cpu_list[i])))]
        offset += cpu_list[i]

        service["volumes"] = [service["volumes"][i].replace("$HOME$", project_dir) for i in range(len(service["volumes"]))]

        service_name = f"{TEST_SERVICE}_{i}"
        SERVICES.append(service_name)

        service["container_name"] = f"{TEST_SERVICE}_{i}"
        service["ports"] = [f"{8080 + i}:8080"]
        service["cpuset"] = ','.join(cpus)
        service["deploy"]["resources"]["limits"]["cpus"] = f"{cpu_list[i]}"
        service["environment"][1] = service["environment"][1].replace("{CONTAINER_NAME}", f"{service_name}")

        docker_file_dict["services"][service_name] = service
    
    DOCKER_COMPOSE_FILE_PATH = os.path.join(DOCKER_COMPOSE_FILE_FOLDER, f"docker-compose-{TEST_SERVICE}-{cpu_list}.yml")

    with io.open(DOCKER_COMPOSE_FILE_PATH, 'w', encoding='utf8') as outfile:
        representer.RoundTripRepresenter.ignore_aliases = lambda x, y: True
        yaml_docker = YAML()
        yaml_docker.default_flow_style = False
        yaml_docker.allow_unicode = False
        yaml_docker.indent(mapping=2, sequence=4, offset=2)
        yaml_docker.preserve_quotes = False
        yaml_docker.dump(docker_file_dict, stream=outfile)

    return DOCKER_COMPOSE_FILE_PATH

def create_containers(cpu_list: list):
    # create the docker-compose file and save it
    DOCKER_COMPOSE_FILE_PATH = create_docker_compose_file(cpu_list)

    # run the docker-compose up command
    subprocess.run(['docker', 'compose', '-f', DOCKER_COMPOSE_FILE_PATH, 'up', '-d', '--remove-orphans'])
    
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

if __name__ == "__main__":
    cpu_list = [1]
    create_docker_compose_file(cpu_list)