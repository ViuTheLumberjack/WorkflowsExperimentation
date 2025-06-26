import os
import time
import subprocess
from utility import WORKFLOW, CLOSED_LOOP_EXPERIMENTS, OPEN_LOOP_EXPERIMENTS, OPEN_LOOP_PATH, CLOSED_LOOP_PATH, RESULT_FOLDER, get_s
from utility import plot_times_and_job_sizes, check_law, load_performance_results, load_load_results
from workflow_parser import get_workflow
from docker_utility import SERVICES, create_containers, stop_containers

WORK_DIR = os.path.join(os.path.dirname(__file__), "work_dir")

def download_results(output_folder: str, start: int, end:int) -> None:
    # Download the results from the Jaeger UI
    start = start // 1000
    end = end // 1000
    
    jaeger_url = f"http://localhost:16686/api/traces?limit=20000&service={{SERVICE_NAME}}&lookback=custom&start={start}&end={end}"

    # only one iteration because w3c trace context is the same for all the services supported
    for service in SERVICES:
        jaeger_service_url = jaeger_url.replace("{SERVICE_NAME}", service)

        response = subprocess.run(['curl', '-X', 'GET', jaeger_service_url], capture_output=True)
        if response.returncode == 0:
            with open(os.path.join(output_folder, f'jaeger.json'), 'wb') as f:
                f.write(response.stdout)
        
        break

def move_to(source: str, dest: str) -> None:
    """
    Move the file from source to destination
    """
    if os.path.exists(source):
        subprocess.run(['mv', source, dest])

def run_closed_loop_test(mu: list, num_cores: list, concurrent_users: int,  iteration: int):
    OUTPUT_FOLDER = os.path.join(RESULT_FOLDER, "performance", f"{get_s(num_cores)}_core", str(get_s(mu)), f"{str(concurrent_users)}_users", str(iteration))
    os.makedirs(os.path.join(OUTPUT_FOLDER), exist_ok=True)

    env = os.environ.copy()
    env.clear()
    env["CONCURRENT_USERS"] = str(concurrent_users)
    env["PARAM"] = get_workflow(WORKFLOW, mu)
    env["OUTPUT_PATH"] = os.path.join(WORK_DIR)
    env["OUTPUT_NAME"] = f"metrics.json"
    env["K6_WEB_DASHBOARD"] = "true"
    env["K6_WEB_DASHBOARD_EXPORT"] = os.path.join(WORK_DIR, f"report.html")
    env["K6_WEB_DASHBOARD_PERIOD"] = "1s"

    start = time.time_ns()
    subprocess.run(['k6', 'run', CLOSED_LOOP_PATH], env=env)
    end = time.time_ns()

    print(f"Test {mu} {num_cores} {concurrent_users} {iteration} completed.")
    move_to(os.path.join(WORK_DIR, "metrics.json"), os.path.join(OUTPUT_FOLDER, "metrics.json"))
    move_to(os.path.join(WORK_DIR, "report.html"), os.path.join(OUTPUT_FOLDER, "report.html"))
    download_results(OUTPUT_FOLDER, start, end)

def run_open_loop_test(mu: list, l: int, num_cores: list, iteration: int):
    OUTPUT_FOLDER = os.path.join(RESULT_FOLDER, "load", f"{get_s(num_cores)}_core", str(get_s(mu)), str(l), str(iteration))
    os.makedirs(os.path.join(OUTPUT_FOLDER), exist_ok=True)

    env = os.environ.copy()
    env.clear()
    env["RATE"] = str(l)
    env["PARAM"] = get_workflow(WORKFLOW, mu)
    env["OUTPUT_PATH"] = os.path.join(WORK_DIR)
    env["OUTPUT_NAME"] = f"metrics.json"

    csv_file = os.path.join(WORK_DIR, f"report.csv")
    env["K6_OUT"] = f"csv={csv_file}"
    env["K6_CSV_TIME_FORMAT"] = "unix_micro"
    env["K6_WEB_DASHBOARD"] = "true"
    env["K6_WEB_DASHBOARD_EXPORT"] = os.path.join(WORK_DIR, f"report.html")
    env["K6_WEB_DASHBOARD_PERIOD"] = "1s"

    start = time.time_ns()
    subprocess.run(['k6', 'run', OPEN_LOOP_PATH], env=env)
    end = time.time_ns()

    print(f"Test {mu} {l} {num_cores} {iteration} completed.")
    move_to(os.path.join(WORK_DIR, "metrics.json"), os.path.join(OUTPUT_FOLDER, "metrics.json"))
    move_to(os.path.join(WORK_DIR, "report.csv"), os.path.join(OUTPUT_FOLDER, "report.csv"))
    move_to(os.path.join(WORK_DIR, "report.html"), os.path.join(OUTPUT_FOLDER, "report.html"))
    download_results(OUTPUT_FOLDER, start, end)

if __name__ == '__main__':
    CLOSED_LOOP = False
    OPEN_LOOP = True

    os.makedirs(WORK_DIR, exist_ok=True)

    if CLOSED_LOOP:
        for key, value in CLOSED_LOOP_EXPERIMENTS.items():
            # Extracting the values from the dictionary
            START = value["START"]
            TESTS = value["END"]
            NUM_CORES = value["NUM_COREs"]
            MUs = value["MUs"]
            USERs = value["USERs"]

            for core in NUM_CORES:
                create_containers(core)
                for mu in MUs:
                    for users in USERs:
                        for i in range(START, TESTS):
                            run_closed_loop_test(mu=mu, num_cores=core, iteration=i, concurrent_users=users)

                stop_containers(delete_containers=True)
        
            plot_times_and_job_sizes()
    
    if OPEN_LOOP:
        for key, value in OPEN_LOOP_EXPERIMENTS.items():
            START = value["START"]
            TESTS = value["END"]
            MUs = value["MUs"]
            NUM_COREs = value["NUM_COREs"]
            LAMBDAs = value["LAMBDAs"]

            for core in NUM_COREs:
                create_containers(core)
                for mu in MUs:
                    for l in LAMBDAs:
                        for i in range(START, TESTS):
                            run_open_loop_test(mu=mu, l=l, num_cores=core, iteration=i)
                
                stop_containers(delete_containers=True)

            performance_results = load_performance_results()
            if CLOSED_LOOP or not performance_results.empty():
                check_law(df_performance=performance_results)