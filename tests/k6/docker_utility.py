import sys
import os
import io
import copy
import subprocess
import time
import math
from ruamel.yaml import YAML, representer
# from utility import TEST_SERVICE

# DOCKER_COMPOSE_FILE_FOLDER = os.path.join(os.path.dirname(__file__), "dockerfiles")
# LIMIT_THREADS = True

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
        "MAX_THREADS={THREADS}",
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
        "$HOME$/opentelemetry-javaagent.jar:/usr/local/opentelemetry-javaagent.jar",
        "$HOME$/standalone.xml:/opt/jboss/wildfly/standalone/configuration/standalone.xml"
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

def create_docker_compose_file(workflow_config: dict, options: dict = None, limit_threads: bool = None) -> str:
    DOCKER_COMPOSE_FILE_FOLDER = os.path.join(options["RESULT_FOLDER"] if options and "RESULT_FOLDER" in options else ".", "dockerfiles")
    LIMIT_THREADS = limit_threads if limit_threads is not None else False
    TEST_SERVICE = options["TEST_SERVICE"] if options and "TEST_SERVICE" in options else "test_service"
    
    if not os.path.exists(DOCKER_COMPOSE_FILE_FOLDER):
        os.makedirs(DOCKER_COMPOSE_FILE_FOLDER, exist_ok=True)

    cpu_list = workflow_config if isinstance(workflow_config[0], list) else [entry["core"] for entry in workflow_config]


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

        service_name = f"{TEST_SERVICE}_{i}" if workflow_config is None or isinstance(workflow_config[0], list) else workflow_config[i]["name"]
        SERVICES.append((service_name, 8080 + i))

        service["container_name"] = service_name
        service["ports"] = [f"{8080 + i}:8080"]
        service["cpuset"] = ','.join(cpus)
        service["deploy"]["resources"]["limits"]["cpus"] = f"{cpu_list[i]}"
        service["environment"][1] = service["environment"][1].replace("{CONTAINER_NAME}", f"{service_name}")
        service["environment"][2] = service["environment"][2].replace("{THREADS}", f"{cpu_list[i] if LIMIT_THREADS else cpu_list[i]*16}")

        docker_file_dict["services"][service_name] = service
    
    DOCKER_COMPOSE_FILE_PATH = os.path.join(DOCKER_COMPOSE_FILE_FOLDER, f"docker-compose-{cpu_list}.yml")

    with io.open(DOCKER_COMPOSE_FILE_PATH, 'w', encoding='utf8') as outfile:
        representer.RoundTripRepresenter.ignore_aliases = lambda x, y: True
        yaml_docker = YAML()
        yaml_docker.default_flow_style = False
        yaml_docker.allow_unicode = False
        yaml_docker.indent(mapping=2, sequence=4, offset=2)
        yaml_docker.preserve_quotes = False
        yaml_docker.dump(docker_file_dict, stream=outfile)

    return DOCKER_COMPOSE_FILE_PATH

def create_containers(cpu_list: list, options: dict = None, limit_threads: bool = None) -> None:
    # create the docker-compose file and save it
    DOCKER_COMPOSE_FILE_PATH = create_docker_compose_file(cpu_list, options, limit_threads)

    # run the docker-compose up command
    subprocess.run(['docker', 'compose', '-f', DOCKER_COMPOSE_FILE_PATH, 'up', '-d', '--remove-orphans'])
    
    # wait for the services to start
    while True:
        try:
            for service_name, port in SERVICES:
                subprocess.run(['curl', f'http://localhost:{port}'], check=True)
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
    cpu_list = [4]
    print(create_docker_compose_file(cpu_list))