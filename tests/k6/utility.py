import os
import numpy as np
import pandas as pd
import json
from math import pow,factorial,log,exp
from matplotlib import pyplot as plt, colors


TEST_SERVICE = 'exponentialop'
TEST_DURATION_S = 60

RESULT_FOLDER = os.path.join(os.path.dirname(__file__), TEST_SERVICE)

TESTS = 6
OPEN_LOOP_PATH = os.path.join(RESULT_FOLDER, f'test_{TEST_SERVICE}.js')
CLOSED_LOOP_PATH = os.path.join(RESULT_FOLDER, f'performance_{TEST_SERVICE}.js')

configuration = json.load(open(os.path.join(RESULT_FOLDER, 'experiments.json')))

CLOSED_LOOP_EXPERIMENTS = { 
    "HIGH_RESOURCES": {
        "NUM_COREs": configuration["closed_loop_experiments"]["high_resources"]["cores"],
        "MUs": configuration["closed_loop_experiments"]["high_resources"]["mus"], # service rate per milliseconds
        "USERs": configuration["closed_loop_experiments"]["high_resources"]["users"],
    },
    "LOW_RESOURCES":{
        "NUM_COREs": configuration["closed_loop_experiments"]["low_resources"]["cores"],
        "MUs": configuration["closed_loop_experiments"]["low_resources"]["mus"], # service rate per milliseconds
        "USERs": configuration["closed_loop_experiments"]["low_resources"]["users"],
    },
}

OPEN_LOOP_EXPERIMENTS = {
    "high_load_experiment": {
        "NUM_COREs": configuration["open_loop_experiments"]["high_load_experiment"]["cores"],
        "LAMBDAs": configuration["open_loop_experiments"]["high_load_experiment"]["lambdas"], # arrival rate in requests per second
        "MUs": configuration["open_loop_experiments"]["high_load_experiment"]["mus"],
    },
}

def PowerFact(b,e):
    """
    Returns b^e / e! used everywhere else in the model
    
    Parameters:
        b (int): base
        e (int): exponent
    """
    return pow(b,e) / factorial(e)

def erlangC(m,p):
    """
    Returns the probability a call waits.

    Parameters:
        m   (int): agent count
        p (float): lambda over mu
    """
    u = m * p
    suma = 0
    for k in range(0,m):
        suma += PowerFact(u,k)
    erlang = PowerFact(u,m) / ((PowerFact(u,m)) + (1-p)*suma)
    return erlang

def load_load_results() -> pd.DataFrame:
    # Load the results.
    df = pd.DataFrame()
    
    for exp in OPEN_LOOP_EXPERIMENTS:
        for num_cores in OPEN_LOOP_EXPERIMENTS[exp]["NUM_COREs"]:
            for mu in OPEN_LOOP_EXPERIMENTS[exp]["MUs"]:
                for l in OPEN_LOOP_EXPERIMENTS[exp]["LAMBDAs"]:
                    for iteration in range(1, TESTS):
                        file_path = os.path.join(RESULT_FOLDER, "load", f"{num_cores}_core", str(mu), str(l), str(iteration), f"{l}_{mu}_metrics.json")
                        with open(file_path) as train_file:
                            dict = json.load(train_file)
                            dict['metrics']['lambda'] = l
                            dict['metrics']['mu'] = mu
                            dict['metrics']['iteration'] = iteration
                            dict['metrics']['cores'] = num_cores
                            df = pd.concat([df, pd.json_normalize(dict['metrics'])])

    # remove the columns whose names contain the string 'contains' and 'type'
    df = df.loc[:,~df.columns.str.contains('contains|type')]

    return df.fillna(0)

def load_performance_results() -> pd.DataFrame:
    # Load the results.
    df = pd.DataFrame()
    
    for exp in CLOSED_LOOP_EXPERIMENTS:
        for num_cores in CLOSED_LOOP_EXPERIMENTS[exp]["NUM_COREs"]:
            for mu in CLOSED_LOOP_EXPERIMENTS[exp]["MUs"]:
                for iteration in range(1, TESTS):
                    for concurrent_users in CLOSED_LOOP_EXPERIMENTS[exp]["USERs"]:
                        file_path = os.path.join(RESULT_FOLDER, "performance", f"{num_cores}_core", str(mu), f"{str(concurrent_users)}_users", str(iteration), f"performance_{mu}_metrics.json")
                        with open(file_path) as train_file:
                            dict = json.load(train_file)
                            dict['metrics']['mu'] = mu
                            dict['metrics']['iteration'] = iteration
                            dict['metrics']['cores'] = num_cores
                            df = pd.concat([df, pd.json_normalize(dict['metrics'])])

    # remove the columns whose names contain the string 'contains' and 'type'
    df = df.loc[:,~df.columns.str.contains('contains|type')]

    return df.fillna(0)

# Plot the results.
def plot_results(df: pd.DataFrame, mu: int, nc: int) -> None:
    PLOT_FOLDER = os.path.join(RESULT_FOLDER, f"{nc}_core")

    if not os.path.exists(os.path.dirname(PLOT_FOLDER)):
        os.makedirs(os.path.dirname(PLOT_FOLDER), exist_ok=True)

    average = df.groupby(['mu','lambda'], as_index=False).mean()

    # Create the plot.
    plt.figure(figsize=(20, 12))

    # Plot the response time for each request.
    plt.scatter(df['lambda'], df['iteration_duration.values.avg'], s=10, c=df['lambda'], cmap='spring', label='Response Time', alpha=0.5)
    
    # Plot the average response time.
    plt.plot(average['lambda'], average['iteration_duration.values.avg'], marker='.', linestyle='-', markersize=10, color='red', label='Average Response Time')
    
    # Set the title and labels.
    plt.title(f'Response time with {mu} service time ({nc} cores - {TEST_SERVICE})')
    plt.xlabel('Number of concurrent threads')
    plt.ylabel('Response time (ms)')

    # Annotate the average response time for each request.
    #ax = plt.gca()
    #ax.set_xlim([0, 101])
    #for x, y in zip(average['grpThreads'], average['elapsed']):
    #    plt.annotate(f'{y:.1f}', (x, y), fontsize=8, weight='bold', textcoords="offset points", xytext=(0, 10), rotation=90, ha='center')

    # Show the grid and legend
    plt.grid(True)
    legend = plt.legend(loc='upper left')
    for lh in legend.legend_handles:
        lh.set_alpha(1)
    
    # Save the plot.
    plt.savefig(os.path.join(PLOT_FOLDER, f'{mu}_response_time.png'))

    # Plot the results.
def plot_results_mu(df: pd.DataFrame, nc: int, MUs: list) -> None:
    ### Plot the results for each core on the same plot with different colors.
    average = df.groupby(['mu', 'lambda', 'cores'], as_index=False).mean()

    # Create the plot.
    plt.figure(figsize=(20, 12))

    # Plot the response time for each request.
    # plt.scatter(df['lambda'], df['iteration_duration.values.avg'], s=10, c=df['lambda'], cmap='spring', label='Response Time', alpha=0.5)
    
    for mu in MUs:
        core_df = average[np.logical_and(average['cores'] == nc, average['mu'] == mu)]
        plt.plot(core_df['lambda'], core_df['iteration_duration.values.avg'], marker='.', linestyle='-', markersize=10, label=f'{mu} Service Time RT')
    
    # Set the title and labels.
    plt.title(f'Response time with {mu} service time ({TEST_SERVICE})')
    plt.xlabel('Number of concurrent threads')
    plt.ylabel('Response time (ms)')

    # Annotate the average response time for each request.
    #ax = plt.gca()
    #ax.set_xlim([0, 101])
    #for x, y in zip(average['grpThreads'], average['elapsed']):
    #    plt.annotate(f'{y:.1f}', (x, y), fontsize=8, weight='bold', textcoords="offset points", xytext=(0, 10), rotation=90, ha='center')

    # Show the grid and legend
    plt.grid(True)
    legend = plt.legend(loc='upper left')
    for lh in legend.legend_handles:
        lh.set_alpha(1)
    
    # Save the plot.
    PLOT_FOLDER = os.path.join(RESULT_FOLDER, f"{nc}_core")
    plt.savefig(os.path.join(PLOT_FOLDER, f'response_times.png'))

def plot_results_core(df: pd.DataFrame, mu: int, NUM_CORES: list) -> None:
    ### Plot the results for each core on the same plot with different colors.
    average = df.groupby(['mu','lambda', 'cores'], as_index=False).mean()

    # Create the plot.
    plt.figure(figsize=(20, 12))

    # Plot the response time for each request.
    # plt.scatter(df['lambda'], df['iteration_duration.values.avg'], s=10, c=df['lambda'], cmap='spring', label='Response Time', alpha=0.5)
    
    for core in NUM_CORES:
        core_df = average[np.logical_and(average['cores'] == core, average['mu'] == mu)]
        plt.plot(core_df['lambda'], core_df['iteration_duration.values.avg'], marker='.', linestyle='-', markersize=10, label=f'{core} Cores RT')
    
    # Set the title and labels.
    plt.title(f'Response time with {mu} service time ({TEST_SERVICE})')
    plt.xlabel('Number of concurrent threads')
    plt.ylabel('Response time (ms)')

    # Annotate the average response time for each request.
    #ax = plt.gca()
    #ax.set_xlim([0, 101])
    #for x, y in zip(average['grpThreads'], average['elapsed']):
    #    plt.annotate(f'{y:.1f}', (x, y), fontsize=8, weight='bold', textcoords="offset points", xytext=(0, 10), rotation=90, ha='center')

    # Show the grid and legend
    plt.grid(True)
    legend = plt.legend(loc='upper left')
    for lh in legend.legend_handles:
        lh.set_alpha(1)
    
    # Save the plot.
    plt.savefig(os.path.join(RESULT_FOLDER, f'{mu}_response_time.png'))

def plot_job_sizes(df: pd.DataFrame = None) -> None:
    ### Plot the results for each job_size and 
    # get the job size for each test and create a dataframe with it
    if df is None:
        df = load_performance_results()

    # if we use more than 1 core, we don't need to divide the job size by the number of cores.
    # else we need to divide the job size by the number of cores.
    # L * X = R * T => X = R * T / L 
    df['job_size'] = df['iteration_duration.values.avg'] * df['cores'] / df['vus.values.value']

    average = df.groupby(['cores', 'mu', 'vus.values.value'], as_index=False).mean()
    # Create the plot.
    plt.figure(figsize=(20, 12))

    # Plot the response time for each request.
    # plt.scatter(df['lambda'], df['iteration_duration.values.avg'], s=10, c=df['lambda'], cmap='spring', label='Response Time', alpha=0.5)
    
    for user in CLOSED_LOOP_EXPERIMENTS["HIGH_RESOURCES"]["USERs"]:
        for mu in CLOSED_LOOP_EXPERIMENTS["HIGH_RESOURCES"]["MUs"]:
            core_df = average[np.logical_and(average['mu'] == mu, average['vus.values.value'] == user)]
            plt.plot(core_df['cores'], core_df['iteration_duration.values.avg'], marker='.', linestyle='-', markersize=10, label=f'Job Size with mu={mu} ')
        
    # Set the title and labels.
    plt.title(f'Job size for different resources ({TEST_SERVICE})')
    plt.xlabel('# Cores')
    plt.ylabel('Job Size')

    # Show the grid and legend
    plt.grid(True)
    legend = plt.legend(loc='upper left')
    for lh in legend.legend_handles:
        lh.set_alpha(1)
    
    # Save the plot.
    df.to_csv(os.path.join(RESULT_FOLDER,'performance', 'data.csv'), index=False)
    plt.savefig(os.path.join(RESULT_FOLDER, "performance", f'job_sizes.png'))

plot_job_sizes()