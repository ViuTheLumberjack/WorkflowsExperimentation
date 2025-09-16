import os
import time
import subprocess
import itertools

# from utility import WORKFLOW, CLOSED_LOOP_EXPERIMENTS, OPEN_LOOP_EXPERIMENTS, OPEN_LOOP_PATH, CLOSED_LOOP_PATH, RESULT_FOLDER, get_s
from utility import get_s, plot_times_and_job_sizes, check_law, load_performance_results, load_load_results
from workflow_parser import get_workflow, WorkflowIterator
from test_utility import generate_test
from docker_utility import SERVICES, create_containers, stop_containers
from options_utility import parse_args, get_test_options

WORK_DIR = os.path.join(os.path.dirname(__file__), "work_dir")

def download_results(output_folder: str, start: int, end:int) -> None:
    # Download the results from the Jaeger UI
    start = start // 1000
    end = end // 1000
    
    jaeger_url = f"http://localhost:16686/api/traces?limit=20000&service={{SERVICE_NAME}}&lookback=custom&start={start}&end={end}"

    # only one iteration because w3c trace context is the same for all the services supported
    for service, port in SERVICES:
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

def extract_arg_values(nodes):
    """
    Recursively extract 'arg_values' from a list of objects (forest of trees).
    
    Args:
        nodes (list): List of objects representing the forest of trees.
    
    Returns:
        list: A list of all 'arg_values' found in the leaf nodes.
    """
    arg_values = []
    
    for node in nodes:
        # If 'arg_values' exists in the current node, add it to the result
        if 'arg_values' in node:
            arg_values.append(node['arg_values'][0])
        # If the node has children, recurse into them
        if 'services' in node and isinstance(node['services'], list):
            arg_values.append(extract_arg_values(node['services']))

    return arg_values

def run_test(options: dict, calls: list[str], core_combination: list[int], arg_combination: list[int], l: list[float], test_path: str, iteration: int) -> None:
    cc = [d["core"] for d in core_combination]
    extracted_arg_values = extract_arg_values(arg_combination)
    OUTPUT_FOLDER = os.path.join(options["RESULT_FOLDER"], "test", get_s(cc),  get_s(l), get_s(extracted_arg_values), str(iteration))
    os.makedirs(os.path.join(OUTPUT_FOLDER), exist_ok=True)

    env = os.environ.copy()
    env.clear()
    for i in range(len(calls)):
        env[f"RATE_{i}"] = str(l[i])
    for i in range(len(calls)):
        env[f"API_URL_{i}"] = calls[i]
    
    env["OUTPUT_PATH"] = os.path.join(WORK_DIR)
    env["OUTPUT_NAME"] = f"metrics.json"
    env["K6_WEB_DASHBOARD"] = "false"
    env["K6_WEB_DASHBOARD_EXPORT"] = os.path.join(WORK_DIR, f"report.html")
    env["K6_WEB_DASHBOARD_PERIOD"] = "1s"

    start = time.time_ns()
    subprocess.run(['k6', 'run', test_path], env=env)
    end = time.time_ns()

    print(f"Test {arg_combination} {core_combination} {l} {iteration} completed.")
    move_to(os.path.join(WORK_DIR, "metrics.json"), os.path.join(OUTPUT_FOLDER, "metrics.json"))
    move_to(os.path.join(WORK_DIR, "report.html"), os.path.join(OUTPUT_FOLDER, "report.html"))
    download_results(OUTPUT_FOLDER, start, end)

    
def run_closed_loop_test(mu: list, num_cores: list, concurrent_users: int,  iteration: int) -> None:
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

def run_open_loop_test(mu: list, l: int, num_cores: list, iteration: int) -> None:
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
    args = parse_args()

    os.makedirs(WORK_DIR, exist_ok=True)
    options = get_test_options(args.path)


    # All possible combinations of cores for each node
    core_combinations = [
        [ {"name": d["name"], "core": c} for d, c in zip(options["NODES"], combo) ]
        for combo in itertools.product(*(d["cores"] for d in options["NODES"]))
    ]

    load_combinations = itertools.product(*(d["users"] if "users" in d else d["rate"] for d in options["LOAD"]["loads"]))
    # generate the test template
    test_path = generate_test(options)

    for c in core_combinations:
        create_containers(c, options, args.limit_threads)
        services_dict = {key: value for key, value in SERVICES}
        print(services_dict)

        for l in load_combinations:
            for i in range(options["LOAD"]['start'], options["LOAD"]['end']):
                it = WorkflowIterator(options["WORKFLOW"])
                for arg_comb, calls in it:
                    calls = [f"http://localhost:{services_dict[wf['node_name']]}/service/{c}" for (c, wf) in zip(calls, options["WORKFLOW"])]
                    print(calls)
                    run_test(options, calls, c, arg_comb, l, test_path, i)

        stop_containers(delete_containers=True)
            
    if False: # v1 code. Ignore
        CLOSED_LOOP = args.closed_loop
        OPEN_LOOP = args.open_loop
        if CLOSED_LOOP:
            for key, value in LOADS['closed_loop'].items():
                # Extracting the values from the dictionary
                START = options["LOADS"]["START"]
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
            for key, value in LOADS['open_loop'].items():
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
        