import os
import numpy as np
import pandas as pd
import json
from math import pow,factorial,log,exp
from matplotlib import pyplot as plt, colors

TEST_SERVICE = os.path.join('exponentialop')

RESULT_FOLDER = os.path.join(os.path.dirname(__file__), TEST_SERVICE)

TEST_PATH = os.path.join(os.path.dirname(__file__))
OPEN_LOOP_PATH = os.path.join(TEST_PATH, f'test_load.js')
CLOSED_LOOP_PATH = os.path.join(TEST_PATH, f'test_performance.js')

configuration = json.load(open(os.path.join(RESULT_FOLDER, 'experiments.json')))

WORKFLOW = configuration["workflow"] if "workflow" in configuration else None

CLOSED_LOOP_EXPERIMENTS = { 
    "HIGH_RESOURCES": {
        "START": configuration["closed_loop_experiments"]["high_resources"]["start"],
        "END": configuration["closed_loop_experiments"]["high_resources"]["end"],
        "NUM_COREs": configuration["closed_loop_experiments"]["high_resources"]["cores"],
        "MUs": configuration["closed_loop_experiments"]["high_resources"]["mus"], # service rate per milliseconds
        "USERs": configuration["closed_loop_experiments"]["high_resources"]["users"],
    },
    "LOW_RESOURCES": {
        "START": configuration["closed_loop_experiments"]["low_resources"]["start"],
        "END": configuration["closed_loop_experiments"]["low_resources"]["end"],
        "NUM_COREs": configuration["closed_loop_experiments"]["low_resources"]["cores"],
        "MUs": configuration["closed_loop_experiments"]["low_resources"]["mus"], # service rate per milliseconds
        "USERs": configuration["closed_loop_experiments"]["low_resources"]["users"],
    },
}

OPEN_LOOP_EXPERIMENTS = {
    "high_load_experiment": {
        "START": configuration["open_loop_experiments"]["high_load_experiment"]["start"],
        "END": configuration["open_loop_experiments"]["high_load_experiment"]["end"],
        "NUM_COREs": configuration["open_loop_experiments"]["high_load_experiment"]["cores"],
        "LAMBDAs": configuration["open_loop_experiments"]["high_load_experiment"]["lambdas"], # arrival rate in requests per second
        "MUs": configuration["open_loop_experiments"]["high_load_experiment"]["mus"],
    },
}

def get_s(l: list) -> str:
    """
    Returns a string from a list of strings
    """
    return "[" + ','.join([str(i) for i in l]) + "]"

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

def find_steady_state_start(diff_series, window=5, epsilon=0.5):
    for i in range(window, len(diff_series)):
        recent = diff_series.iloc[i-window:i].abs()
        if all(recent < epsilon):
            return i - window  # Index where steady state starts
    return None

def load_single_load_results(num_cores: list, mu: list, l: int, iteration: int) -> pd.DataFrame | None:
    if len(num_cores) > 1:
        # TODO: HANDLE THE CASE WHEN WE HAVE MORE THAN 1 SERVICE, HENCE WE ARE IN A WORKFLOW
        pass
    else :
        file_path = os.path.join(RESULT_FOLDER, "load", f"{get_s(num_cores)}_core", str(get_s(mu)), str(l), str(iteration), f"report.csv")
        new_df = pd.read_csv(file_path)
        new_df = new_df[new_df['metric_name'].isin(["vus", "http_req_duration"])]
        
        # get only the data at steady state
        # we are at steady state when difference between subsequent is similar
        differences = new_df[new_df['metric_name'] == 'vus']['metric_value'].diff()

        steady_start = find_steady_state_start(differences, window=10, epsilon=4)
        if steady_start:
            initial_timestamp = new_df.loc[differences.index[steady_start]]['timestamp']
            steady_df = new_df[new_df['timestamp'] >= initial_timestamp]
        else:
            # TODO: handle the case when steady state is not found
            steady_df = new_df

        # compute run statistics, so mean time values and mean vus
        stats_df = steady_df.groupby(['metric_name']).agg(
            mean=('metric_value', 'mean'),
            min=('metric_value', 'min'),
            max=('metric_value', 'max'),
            std=('metric_value', 'std'),
            count=('metric_value', 'count'),
            median=('metric_value', 'median')
        ).reset_index()

        stats_df['mu'] = mu[0]
        stats_df['lambda'] = l
        stats_df['cores'] = num_cores[0]
        stats_df['iteration'] = iteration

        return stats_df

def load_load_results() -> pd.DataFrame:
    # Load the results.
    df = pd.DataFrame()
    
    for exp in OPEN_LOOP_EXPERIMENTS:
        for num_cores in OPEN_LOOP_EXPERIMENTS[exp]["NUM_COREs"]:
            for mu in OPEN_LOOP_EXPERIMENTS[exp]["MUs"]:
                for l in OPEN_LOOP_EXPERIMENTS[exp]["LAMBDAs"]:
                    for iteration in range(OPEN_LOOP_EXPERIMENTS[exp]["START"], OPEN_LOOP_EXPERIMENTS[exp]["END"]):
                        df = pd.concat([df, load_single_load_results(num_cores, mu, l, iteration)], ignore_index=True)

    return df

def load_single_performance_results(num_cores: list, mu: list, concurrent_users: int, iteration: int) -> pd.DataFrame | None:
    if len(num_cores) > 1:
        # TODO: HANDLE THE CASE WHEN WE HAVE MORE THAN 1 SERVICE, HENCE WE ARE IN A WORKFLOW
        pass
    else :
        file_path = os.path.join(RESULT_FOLDER, "performance", f"{get_s(num_cores)}_core", str(get_s(mu)), f"{str(concurrent_users)}_users", str(iteration), f"metrics.json")
        with open(file_path) as train_file:
            dict = json.load(train_file)
            dict['metrics']['mu'] = mu[0]
            dict['metrics']['iteration'] = iteration
            dict['metrics']['cores'] = num_cores[0]

            return pd.json_normalize(dict['metrics'])

def load_performance_results() -> pd.DataFrame:
    # Load the results.
    df = pd.DataFrame()
    
    for exp in CLOSED_LOOP_EXPERIMENTS:
        for num_cores in CLOSED_LOOP_EXPERIMENTS[exp]["NUM_COREs"]:
            for mu in CLOSED_LOOP_EXPERIMENTS[exp]["MUs"]:
                for iteration in range(CLOSED_LOOP_EXPERIMENTS[exp]["START"], CLOSED_LOOP_EXPERIMENTS[exp]["END"]):
                    for concurrent_users in CLOSED_LOOP_EXPERIMENTS[exp]["USERs"]:
                        df = pd.concat([df, load_single_performance_results(num_cores, mu, concurrent_users, iteration)], ignore_index=True)

    # remove the columns whose names contain the string 'contains' and 'type'
    df = df.loc[:,~df.columns.str.contains('contains|type')]

    return df.fillna(0)

def is_outlier(s: pd.Series) -> pd.Series:
    Q1 = s.quantile(0.25)
    Q3 = s.quantile(0.75)
    IQR = Q3 - Q1

    return (s < (Q1 - 1.5 * IQR)) | (s > (Q3 + 1.5 * IQR))

def check_law(df_performance: pd.DataFrame = None, df_load: pd.DataFrame = None) -> None:
    ## Check if L * X = T * R
    ## So calculate theoretical values for each test and compare with the results
    if df_performance is None:
        df_performance = load_performance_results()

    df_performance = df_performance[~df_performance.groupby(['cores', 'mu', 'vus.values.value'])['http_req_duration.values.avg'].transform(is_outlier)].reset_index(drop=True)
    df_performance['job_size'] = df_performance['http_req_duration.values.avg'] * df_performance['cores'] / df_performance['vus_max.values.value']

    if df_load is None:
        df_load = load_load_results()

    # for each load test calculate L, the number of concurrent requests. we can extract it from the vus column
    job_sizes = df_performance.groupby(['cores', 'mu', 'vus_max.values.value'], as_index=False).mean()
    BASE_PLOT_FOLDER = os.path.join(RESULT_FOLDER, 'results')
    if not os.path.exists(os.path.join(BASE_PLOT_FOLDER)):
        os.makedirs(BASE_PLOT_FOLDER, exist_ok=True)

    # plot T as a function of L, comparing theoretical and real values for each load rate and each service rate and each core
    for cores in OPEN_LOOP_EXPERIMENTS['high_load_experiment']["NUM_COREs"]:
        for mus in OPEN_LOOP_EXPERIMENTS["high_load_experiment"]["MUs"]:
            for mu in mus:
                for core in cores:
                    load_df = df_load[np.logical_and(df_load['cores'] == core, df_load['mu'] == mu)]
                    load_df = load_df.groupby(['metric_name', 'lambda'], as_index=False).mean()
                    performance_df = job_sizes[np.logical_and(job_sizes['mu'] == mu, job_sizes['cores'] == core)]
                    
                    job_size = performance_df[performance_df['vus.values.value'] == 1]['job_size'].values[0]
                    
                    users = load_df.loc[load_df.metric_name=='vus'] 
                    times = load_df.loc[load_df.metric_name=='http_req_duration']

                    lx = users[['lambda', 'mean']].copy()
                    # lx['count'] = times["count"].values
                    lx['mean'] = lx['mean'] * job_size / core
                    lx['mean'].mean()
                    times
                    # plot the results
                    plt.figure(figsize=(20, 12))
                    plt.plot(lx['lambda'], lx['mean'], marker='.', linestyle='-', markersize=10, label='Theoretical')
                    plt.plot(times['lambda'], times['mean'], marker='.', linestyle='-', markersize=10, label='Empirical')
                    
                    # Set the title and labels.
                    plt.title(f'Check law for mu = {mu} with R = {core} core ({TEST_SERVICE})')
                    plt.xlabel('Lambda')
                    plt.ylabel('Time')

                    # Show the grid and legend
                    plt.grid(True)
                    legend = plt.legend(loc='upper left')
                    for lh in legend.legend_handles:
                        lh.set_alpha(1)

                    # Save the plot.
                    PLOT_FOLDER = os.path.join(BASE_PLOT_FOLDER, str(mu))
                    if not os.path.exists(PLOT_FOLDER):
                        os.makedirs(PLOT_FOLDER, exist_ok=True)
                        
                    plt.savefig(os.path.join(PLOT_FOLDER, f'check_law_{mu}_{core}cores.png'))
                    plt.close()

def _plot_job_size(core_df: pd.DataFrame, mu: int, user: int, PLOT_FOLDER: str) -> None:
    # Create the plot.
    plt.figure(figsize=(20, 12))
    ## PLOT THE JOB SIZE
    plt.plot(core_df['cores'], core_df['job_size'], marker='.', linestyle='-', markersize=10)
    # Set the title and labels.
    plt.title(f'Job size for mu = {mu} with {user} users ({TEST_SERVICE})')
    plt.xlabel('# Cores')
    plt.ylabel('Job Size')

    # Annotate the average response time for each request.
    for x, y in zip(core_df['cores'], core_df['job_size']):
        plt.annotate(f'{y:.2f}', (x, y), fontsize=10, weight='bold', textcoords="offset points", xytext=(10, 10), ha='center')

    # Show the grid and legend
    plt.grid(True)
    
    # Save the plot.
    plt.savefig(os.path.join(PLOT_FOLDER, f'job_sizes.png'))
    plt.close()

def _plot_time(core_df: pd.DataFrame, mu: int, user: int, PLOT_FOLDER: str) -> None:
    plt.figure(figsize=(20, 12))
    plt.plot(core_df['cores'], core_df['http_req_duration.values.avg'], marker='.', linestyle='-', markersize=10)
    # Set the title and labels.
    plt.title(f'Times for mu = {mu} with {user} users ({TEST_SERVICE})')
    plt.xlabel('# Cores')
    plt.ylabel('Time')

    for x, y in zip(core_df['cores'], core_df['http_req_duration.values.avg']):
        plt.annotate(f'{y:.2f}', (x, y), fontsize=10, weight='bold', textcoords="offset points", xytext=(0, 10), rotation=90, ha='center')
    # Show the grid and legend
    plt.grid(True)

    plt.savefig(os.path.join(PLOT_FOLDER, f'{mu}_times.png'))
    plt.close()

def _plot_all_job_sizes(average: pd.DataFrame, mu: int, PLOT_FOLDER: str) -> None:
    # Create the plot.
    plt.figure(figsize=(20, 12))
    for user in CLOSED_LOOP_EXPERIMENTS["HIGH_RESOURCES"]["USERs"]:
        user_df = average[np.logical_and(average['mu'] == mu, average['vus.values.value'] == user)]
        plt.plot(user_df['cores'], user_df['http_req_duration.values.avg'], marker='.', linestyle='-', markersize=10, label=f'{user} Users')

    # Set the title and labels.
    plt.title(f'Times for mu = {mu} ({TEST_SERVICE})')
    plt.xlabel('# Cores')
    plt.ylabel('Time')

    plt.grid(True)
    legend = plt.legend(loc='upper right')
    for lh in legend.legend_handles:
        lh.set_alpha(1)

    plt.savefig(os.path.join(PLOT_FOLDER, f'{mu}_times.png'))
    plt.close()

def _plot_all_times(average: pd.DataFrame, mu: int, PLOT_FOLDER: str) -> None:
    plt.figure(figsize=(20, 12))

    for user in CLOSED_LOOP_EXPERIMENTS["HIGH_RESOURCES"]["USERs"]:
        user_df = average[np.logical_and(average['mu'] == mu, average['vus.values.value'] == user)]
        plt.plot(user_df['cores'], user_df['job_size'], marker='.', linestyle='-', markersize=10, label=f'{user} Users')

    # Set the title and labels.
    plt.title(f'Job Size for mu = {mu} ({TEST_SERVICE})')
    plt.xlabel('# Cores')
    plt.ylabel('Job Size')

    # Show the grid and legend
    plt.grid(True)
    legend = plt.legend(loc='upper left')
    for lh in legend.legend_handles:
        lh.set_alpha(1)

    plt.savefig(os.path.join(PLOT_FOLDER, f'job_sizes.png'))
    plt.close()

def plot_job_sizes(df_performance: pd.DataFrame = None) -> None:
    ### Plot the results for each job_size and 
    # get the job size for each test and create a dataframe with it
    if df_performance is None:
        df_performance = load_performance_results()

    BASE_PLOT_FOLDER = os.path.join(RESULT_FOLDER, 'results')
    if not os.path.exists(os.path.join(BASE_PLOT_FOLDER)):
        os.makedirs(BASE_PLOT_FOLDER, exist_ok=True)

    # df_performance = df_performance[~df_performance.groupby(['cores', 'mu', 'vus.values.value'])['http_req_duration.values.avg'].transform(is_outlier)].reset_index(drop=True)
    
    # if we use more than 1 core, we don't need to divide the job size by the number of cores.
    # else we need to divide the job size by the number of cores.
    # L * X = R * T => X = R * T / L 
    df_performance['job_size'] = df_performance['http_req_duration.values.avg'] * df_performance['cores'] / df_performance['vus_max.values.value']
    average = df_performance.groupby(['cores', 'mu', 'vus_max.values.value'], as_index=False).mean()

    for mus in CLOSED_LOOP_EXPERIMENTS["HIGH_RESOURCES"]["MUs"]:
        for user in CLOSED_LOOP_EXPERIMENTS["HIGH_RESOURCES"]["USERs"]:
            PLOT_FOLDER = os.path.join(BASE_PLOT_FOLDER, get_s(mus), str(user))
            if not os.path.exists(PLOT_FOLDER):
                os.makedirs(PLOT_FOLDER, exist_ok=True)
            for mu in mus:
                core_df = average[np.logical_and(average['mu'] == mu, average['vus_max.values.value'] == user)]

                _plot_job_size(core_df, mu, user, PLOT_FOLDER)
                _plot_time(core_df, mu, user, PLOT_FOLDER)

    for mus in CLOSED_LOOP_EXPERIMENTS["HIGH_RESOURCES"]["MUs"]:
        # plot on the same plot the job size for each user
        PLOT_FOLDER = os.path.join(BASE_PLOT_FOLDER, get_s(mus))
        for mu in mus:
            ## plot the times
            _plot_all_job_sizes(average, mu, PLOT_FOLDER)
            _plot_all_times(average, mu, PLOT_FOLDER)

    df_performance.to_csv(os.path.join(BASE_PLOT_FOLDER, 'data.csv'), index=False)

if __name__ == '__main__':
    plot_job_sizes()
    check_law()