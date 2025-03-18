import os
import subprocess
import pandas as pd
import numpy as np
from utility import CLOSED_LOOP_EXPERIMENTS, OPEN_LOOP_EXPERIMENTS, TESTS, OPEN_LOOP_PATH, CLOSED_LOOP_PATH, RESULT_FOLDER
#from utility import load_results, plot_results, plot_results_core, plot_results_mu, plot_job_sizes
from docker_utility import create_containers, stop_containers

def run_closed_loop_test(mu: int, num_cores: float, concurrent_users: int,  iteration: int):
    OUTPUT_FOLDER = os.path.join(RESULT_FOLDER, "performance", f"{num_cores}_core", str(mu), f"{str(concurrent_users)}_users", str(iteration))
    os.makedirs(os.path.join(OUTPUT_FOLDER), exist_ok=True)

    env = os.environ.copy()
    env["CONCURRENT_USERS"] = str(concurrent_users)
    env["PARAM"] = str(mu)
    env["OUTPUT_PATH"] = os.path.join(OUTPUT_FOLDER)
    env["K6_WEB_DASHBOARD"] = "true"
    env["K6_WEB_DASHBOARD_EXPORT"] = os.path.join(OUTPUT_FOLDER, f"{mu}_report.html")
    env["K6_WEB_DASHBOARD_PERIOD"] = "5s"
    subprocess.run(['k6', 'run', CLOSED_LOOP_PATH], env=env)

    print(f"Test {mu} {num_cores} {concurrent_users} {iteration} completed.")

def run_open_loop_test(mu: int, l: int, num_cores: int, iteration: int):
    OUTPUT_FOLDER = os.path.join(RESULT_FOLDER, "load", f"{num_cores}_core", str(mu), str(l), str(iteration))
    os.makedirs(os.path.join(OUTPUT_FOLDER), exist_ok=True)

    env = os.environ.copy()
    env["RATE"] = str(l)
    env["PARAM"] = str(mu)
    env["OUTPUT_PATH"] = os.path.join(OUTPUT_FOLDER)
    env["K6_WEB_DASHBOARD"] = "true"
    env["K6_WEB_DASHBOARD_EXPORT"] = os.path.join(OUTPUT_FOLDER, f"{l}_{mu}_report.html")
    env["K6_WEB_DASHBOARD_PERIOD"] = "5s"
    subprocess.run(['k6', 'run', OPEN_LOOP_PATH], env=env)

    print(f"Test {mu} {l} {num_cores} {iteration} completed.")

if __name__ == '__main__':

#    for key, value in CLOSED_LOOP_EXPERIMENTS.items():
#        NUM_CORES = value["NUM_COREs"]
#        MUs = value["MUs"]
#        USERs = value["USERs"]

#        for core in NUM_CORES:
#            create_containers([core], core)
#            for i in range(1, TESTS):
#                for users in USERs:
#                    for mu in MUs:
#                        run_closed_loop_test(mu=mu, num_cores=core, iteration=i, concurrent_users=users)

#            stop_containers(delete_containers=True)
    
    for key, value in OPEN_LOOP_EXPERIMENTS.items():
        MUs = value["MUs"]
        NUM_COREs = value["NUM_COREs"]
        LAMBDAs = value["LAMBDAs"]

        for core in NUM_COREs:
            create_containers([core], core)
            for i in range(1, TESTS):
                for mu in MUs:
                    for l in LAMBDAs:
                        run_open_loop_test(mu=mu, l=l, num_cores=core, iteration=i)
            
            stop_containers(delete_containers=True)

#    df = load_results(LAMBDAs=LAMBDAs, MUs=MUs, NUM_CORES=NUM_COREs)
#    plot_job_sizes(df)
#
#    for mu in MUs:
#        for nc in NUM_COREs:
#            plot_results_mu(df, nc)
#            plot_results(df[np.logical_and(df['mu'] == mu, df['cores'] == nc)], mu, nc)
#        
#        plot_results_core(df, mu)

#    df.to_csv(os.path.join(RESULT_FOLDER, 'data.csv'), index=False)
#    print('All tests completed.')