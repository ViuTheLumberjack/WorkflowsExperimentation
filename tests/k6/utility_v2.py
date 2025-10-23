import os
import re
import numpy as np
import pandas as pd
import json
import itertools
import matplotlib.pyplot as plt
import seaborn as sns
import random
import math
from matplotlib.ticker import MultipleLocator
from scipy import stats

from py4j.java_gateway import JavaGateway
from py4j.java_gateway import java_import

from subprocess import Popen
from time import sleep

from matplotlib import pyplot as plt, colors
from options_utility import parse_args, get_test_options, extract_arg_values
from workflow_parser import get_workflow, WorkflowIterator
from options_utility import extract_unique_pairs

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
    return pow(b,e) / math.factorial(e)

def erlangC(m,p):
    """
    Returns the probability a call waits.

    Parameters:
        m   (int): agent count
        p (float): lambda over (m times mu)
    """
    u = m * p
    suma = 0
    for k in range(0,m):
        suma += PowerFact(u,k)
    erlang = PowerFact(u,m) / ((PowerFact(u,m)) + (1-p)*suma)
    return erlang
    
def parse_jaeger_traces(file_path) -> tuple[pd.DataFrame, float, float]:
    """
    Parses a Jaeger JSON trace file to extract user-specific trace details
    and find the overall time range of the traces.

    Args:
        file_path (str): The path to the Jaeger JSON file.

    Returns:
        tuple: A tuple containing (processed_traces, overall_start_us, overall_end_us).
               - processed_traces (list): Traces with user_id, start, and end times.
               - overall_start_us (int): The earliest start time in microseconds.
               - overall_end_us (int): The latest end time in microseconds.
    """
    processed_traces = []
    overall_min_start_time_us = float('inf')
    overall_max_end_time_us = 0
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return [], 0, 0
    except json.JSONDecodeError:
        print(f"Error: The file '{file_path}' is not a valid JSON file.")
        return [], 0, 0

    if 'data' not in data or not isinstance(data['data'], list):
        print("Error: JSON file does not have the expected Jaeger format (missing 'data' array).")
        return [], 0, 0

    for trace in data['data']:
        user_id = None
        min_start_time = float('inf')
        max_end_time = 0

        if 'spans' not in trace or not trace['spans']:
            continue

        # Determine the absolute start and end time for this trace
        for span in trace['spans']:
            start_time = span.get('startTime', 0)
            duration = span.get('duration', 0)
            end_time = start_time + duration
            
            if start_time < min_start_time:
                min_start_time = start_time
            if end_time > max_end_time:
                max_end_time = end_time

        if min_start_time != float('inf'):
            processed_traces.append({
                'user_id': user_id,
                'duration': (max_end_time - min_start_time) // 1000,
                'start_time_us': min_start_time,
                'end_time_us': max_end_time
            })
            # Update overall min and max times
            if min_start_time < overall_min_start_time_us:
                overall_min_start_time_us = min_start_time
            if max_end_time > overall_max_end_time_us:
                overall_max_end_time_us = max_end_time

    return pd.DataFrame(processed_traces), overall_min_start_time_us, overall_max_end_time_us

def parse_metric_traces(file_path, metric_name="http_req_duration") -> tuple[pd.DataFrame, float, float]:
    """
    Parses a Jaeger JSON trace file to extract user-specific trace details
    and find the overall time range of the traces.

    Args:
        file_path (str): The path to the Jaeger JSON file.

    Returns:
        tuple: A tuple containing (processed_traces, overall_start_us, overall_end_us).
               - processed_traces (list): Traces with user_id, start, and end times.
               - overall_start_us (int): The earliest start time in microseconds.
               - overall_end_us (int): The latest end time in microseconds.
    """
    
    df = pd.read_csv(file_path)

    # Filtra solo le righe con la metrica http_req_duration
    durations = df[df["metric_name"] == metric_name].copy()

    # Calcola tempo di inizio e fine in microsecondi
    durations["start_time_us"] = durations["timestamp"] - durations['metric_value'].astype(int) * 1_000
    durations["end_time_us"] = (durations["timestamp"])

    # normalize by 0
    first = durations["start_time_us"].min()
    durations["start_time_us"] = durations["start_time_us"] - first
    durations["end_time_us"] = durations["end_time_us"] - first 

    # Seleziona colonne utili
    result = durations[["timestamp", "metric_value", "start_time_us", "group", "status", "end_time_us", "url", "scenario", "extra_tags", "metadata"]]
    result['extra_tags'] = result['extra_tags'].astype(str)

    return pd.DataFrame(result), result["start_time_us"].min(), result["end_time_us"].max()

def calculate_concurrency(traces, start_time_us: int, end_time_us: int, l = 1) -> pd.DataFrame:
    """
    Calculates the number of concurrent users for each second between
    the provided start and end times and returns a DataFrame.

    Returns:
        pd.DataFrame: with columns ['timestamp', 'concurrent_users']
                      where 'timestamp' is in seconds from simulation start.
    """
    timestamps = []
    concurrency_counts = []

    timestep_us = 1_000_000 // l  # 1 second in microsenconds, adjusted by the load factor l

    current_time_us = start_time_us + timestep_us // 2

    while current_time_us <= end_time_us:
        active_users = traces[(traces['start_time_us'] <= current_time_us) & (current_time_us < traces['end_time_us'])]        
        
        timestamps.append((current_time_us - start_time_us) // 1000)  # Convert microseconds to seconds
        concurrency_counts.append(len(active_users))

        current_time_us += timestep_us

    df = pd.DataFrame({
        'timestamp': timestamps,
        'concurrent_users': concurrency_counts
    })

    return df

def find_steady_state_start(diff_series, window=5, epsilon=0.5):
    for i in range(window, len(diff_series)):
        recent = diff_series.iloc[i-window:i].abs()
        if all(recent < epsilon):
            return i - window  # Index where steady state starts
    return None

def load_single_results(num_cores: list, mu: list, concurrent_users: int, iteration: int, metric_name: str = "http_req_duration", path: str = None) -> pd.DataFrame | None:
    folder_path = path
    # df = pd.json_normalize(dict['metrics'])
    df = pd.DataFrame()
    
    test_file = "report.csv"
    file_path = os.path.join(folder_path, test_file)
    spans = []

    if 'jaeger' in test_file:
        with open(file_path) as train_file:
            dict = json.load(train_file)
            spans = []
            for trace in dict['data']:
                for span in trace['spans']:
                    if re.match("GET /", span['operationName']):
                        spans.append(span)
            
            durations = pd.DataFrame([(span['duration'], span['processID']) for span in spans], columns=['duration', 'service'])
            mean_duration = durations.groupby('service')['duration'].mean().reset_index()

            #TODO: Separate by each load
            df = mean_duration
    else:
        df, start_us, end_us = parse_metric_traces(file_path, metric_name=metric_name)

    df['iteration'] = iteration

    return df

def load_results(options: dict[str, str], metric_name: str = "http_req_duration", with_full_performance: bool = False) -> pd.DataFrame:
    # Load the results.
    df = pd.DataFrame()

    core_combinations = [
        [ {"name": d["name"], "core": c} for d, c in zip(options["NODES"], combo) ]
        for combo in itertools.product(*(d["cores"] for d in options["NODES"]))
    ]

    for c in core_combinations:
        load_combinations = itertools.product(*(d["users"] if "users" in d else d["rate"] for d in options["LOAD"]["loads"]))

        for l in load_combinations:
            for i in range(options["LOAD"]['start'], options["LOAD"]['end']):
                it = WorkflowIterator(options["WORKFLOW"])
                for arg_comb in it:
                    flat_args = extract_arg_values(arg_comb)
                    f_path = os.path.join(options["RESULT_FOLDER"], "test", f"{get_s([d['core'] for d in c])}", get_s(l), str(get_s(flat_args)), str(i))
                    single_df = load_single_results([d["core"] for d in c], arg_comb, l, i, metric_name=metric_name, path=f_path)
                    # assign the right mu and cores from the num_core list and mu list
                    # the num cores depends on the index of the node name in the cores 
                    single_df['cores'] = single_df['extra_tags'].apply(lambda x: x.split('=')[1] if len(x.split('=')) > 1 else '0')
                    single_df['cores'] = single_df['cores'].apply(lambda x: next((item["core"] for item in c if item["name"] == x), None))
                    # the load depends on the value of the scenario tag
                    single_df['service_name'] = single_df['extra_tags'].apply(lambda x: x.split('=')[1] if len(x.split('=')) > 1 else 'all')

                    def _iter_leaf_nodes(node, path, prob=1.0):
                        if not isinstance(node, dict):
                            return
                        services = node.get("services")
                        node_type = node.get("type")
                        if services:
                            if node_type == "or" and len(services) == 2:
                                true_prob = node.get("probability", 0.5)
                                for idx, srv in enumerate(services):
                                    branch_prob = prob * (true_prob if idx == 0 else 1 - true_prob)
                                    yield from _iter_leaf_nodes(srv, path + (idx,), branch_prob)
                            else:
                                for idx, srv in enumerate(services):
                                    yield from _iter_leaf_nodes(srv, path + (idx,), prob)
                        else:
                            yield node, path, prob

                    leaf_lookup = {}
                    for scenario_idx in range(len(options["WORKFLOW"])):
                        wf_instance = arg_comb[scenario_idx] if scenario_idx < len(arg_comb) else options["WORKFLOW"][scenario_idx]
                        for leaf, path, prob in _iter_leaf_nodes(wf_instance, (scenario_idx,)):
                            values = leaf.get("arg_values")
                            value = values[0] if values else None
                            leaf_type = leaf.get("type")
                            leaf_lookup[path] = (value, leaf_type, prob)
                            node_name = leaf.get("node_name")
                            if node_name:
                                leaf_lookup[(scenario_idx, node_name)] = (value, leaf_type, prob)

                    def extract_leaf_info(row):
                        scenario_idx = int(row['scenario'].split('_')[2])
                        base_lambda = l[scenario_idx]
                        value, leaf_type, prob = leaf_lookup.get((scenario_idx, row['service_name']), (None, None, 1.0))
                        return base_lambda * prob, value, leaf_type

                    res = single_df.apply(extract_leaf_info, axis=1)
                    single_df['lambda'], single_df['mu'], single_df['service'] = zip(*res)
                    if single_df is not None:
                        if with_full_performance:
                            df = pd.concat([df, single_df, load_single_performance_recap([d["core"] for d in c], arg_comb, l, i, f_path)], ignore_index=True)
                        else:
                            df = pd.concat([df, single_df], ignore_index=True)

    return df.fillna(0)

def is_outlier(s: pd.Series) -> pd.Series:
    Q1 = s.quantile(0.25)
    Q3 = s.quantile(0.75)
    IQR = Q3 - Q1

    return (s < (Q1 - 1.5 * IQR)) | (s > (Q3 + 1.5 * IQR))

def load_single_performance_recap(num_cores: list, mu: list, concurrent_users: int, iteration: int, path: str = None) -> pd.DataFrame | None:
    if path is not None:
        folder_path = path
    else:
        folder_path = os.path.join(RESULT_FOLDER, "performance", f"{get_s(num_cores)}_core", str(get_s(mu)), f"{str(concurrent_users)}_users", str(iteration))
    
    file_path = os.path.join(folder_path, "metrics.json")
    with open(file_path) as train_file:
        dict = json.load(train_file)

    df = pd.json_normalize(dict['metrics'])

    rdf = pd.DataFrame({
        'timestamp': 0,
        'metric_value': df['iteration_duration.values.avg'],
        'start_time_us': 0,
        'end_time_us': 0,
        'metadata': 'service_name=all',
        'extra_tags': f'service_name=all',
        'iteration': iteration,
        'lambda': 0,
        'mu': 0,
        'scenario': 'all',
        'service': 'all',
        'service_name': 'all'
    })

    return rdf

def compute_mean_service_time(all_data: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola il tempo medio di servizio (metric_value) per ogni run, scenario e servizio.
    """
    if all_data.empty:
        print("DataFrame vuoto: impossibile calcolare i tempi medi di servizio.")
        return pd.DataFrame(columns=["iteration", "scenario", "service", "mean_service_time_ms"])

    df = all_data[["iteration", "scenario", "service_name", "service", "extra_tags", "metric_value", "mu"]].copy()
    df["metric_value"] = pd.to_numeric(df["metric_value"], errors="coerce")
    df.dropna(subset=["metric_value"], inplace=True)

    result = (
        df.groupby(["scenario", "service_name", "service", "mu"], dropna=False)["metric_value"]
        .mean()
        .reset_index()
        .rename(columns={"metric_value": "mean_service_time_ms"})
        .sort_values(["scenario", "service_name", "service"])
        .reset_index(drop=True)
    )

    return result

def parse_service_name(extra_tags_str: str) -> str:
    """
    Estrae il valore di 'service_name' dalla stringa extra_tags.
    Esempio: 'service_name=first,trace_id=...' -> 'first'
    """
    try:
        # Divide la stringa in base alle virgole e cerca il pezzo con 'service_name'
        for part in extra_tags_str.split(','):
            if 'service_name=' in part:
                return part.split('=')[1]
    except (TypeError, AttributeError):
        # Ritorna 'sconosciuto' se il campo è vuoto o non è una stringa
        return 'sconosciuto'
    return 'sconosciuto'

def create_user_load_plot(all_data: pd.DataFrame, time_step_ms: int = 500, plot_path: str = ".") -> pd.DataFrame | None:
    """
    Carica i dati da una lista di file CSV, li elabora e crea un grafico
    a barre sovrapposte del carico di utenti nel tempo.

    Args:
        csv_files (list): Una lista di percorsi ai file CSV da analizzare.
        time_step_ms (int): L'ampiezza dell'intervallo di tempo in millisecondi.
    """
    requests_df = all_data[all_data['scenario'] != 'all'].copy()

    if requests_df.empty:
        print("Non sono state trovate metriche 'http_reqs' nei file. Impossibile generare il grafico.")
        return

    bin_width_us = time_step_ms * 1000

    requests_df['service'] = requests_df['extra_tags'].apply(parse_service_name)
    requests_df['segment'] = requests_df['service'] + ' • ' + requests_df['scenario']
    requests_df['start_bin_idx'] = (requests_df['start_time_us'] // bin_width_us).astype(int)
    requests_df['end_bin_idx'] = (
        (np.maximum(requests_df['end_time_us'] - 1, requests_df['start_time_us'])) // bin_width_us
    ).astype(int)

    start_events = (
        requests_df.groupby(['iteration', 'segment', 'start_bin_idx'])
        .size()
        .rename('delta')
        .reset_index()
        .rename(columns={'start_bin_idx': 'bin_idx'})
    )
    end_events = (
        requests_df.groupby(['iteration', 'segment', 'end_bin_idx'])
        .size()
        .rename('delta')
        .reset_index()
        .rename(columns={'end_bin_idx': 'bin_idx'})
    )
    end_events['bin_idx'] += 1
    end_events['delta'] = -end_events['delta']

    events = pd.concat([start_events, end_events], ignore_index=True)
    events['bin_idx'] = events['bin_idx'].astype(int)
    changes = events.pivot_table(index=['iteration', 'bin_idx'], columns='segment', values='delta', aggfunc='sum', fill_value=0)

    min_bin = int(requests_df['start_bin_idx'].min())
    max_bin = int(requests_df['end_bin_idx'].max()) + 1
    iterations = sorted(requests_df['iteration'].unique())
    full_index = pd.MultiIndex.from_product([iterations, range(min_bin, max_bin + 1)], names=['iteration', 'bin_idx'])
    changes = changes.reindex(full_index, fill_value=0)

    user_counts = changes.groupby(level='iteration').cumsum()
    mean_user_counts = user_counts.groupby(level='bin_idx').mean()
    if mean_user_counts.empty:
        print("Impossibile calcolare la media delle richieste attive.")
        return
    mean_user_counts.index = mean_user_counts.index.astype(int) * time_step_ms

    column_tuples = []
    for seg in mean_user_counts.columns:
        parts = seg.split(' • ', 1)
        if len(parts) == 2:
            service, scenario = parts
        else:
            service, scenario = seg, 'sconosciuto'
        column_tuples.append((scenario.strip(), service.strip()))
    mean_user_counts.columns = pd.MultiIndex.from_tuples(column_tuples, names=['scenario', 'service'])

    scenarios = list(mean_user_counts.columns.levels[0])
    scenario_totals = mean_user_counts.groupby(level='scenario', axis=1).sum()

    sns.set_style("whitegrid")
    num_plots = len(scenarios)
    fig, axes = plt.subplots(num_plots, 1, figsize=(16, 6 * num_plots), sharex=True)
    if num_plots == 1:
        axes = [axes]

    def handle_x_ticks(ax, stacked=True):
        num_ticks = len(ax.get_xticklabels())
        if num_ticks > 50:
            tick_spacing = max(1, num_ticks // 25)
            for i, label in enumerate(ax.get_xticklabels()):
                if i % tick_spacing != 0:
                    label.set_visible(False)

        if stacked:
            for container in ax.containers:
                labels = [f"{int(v)}" if v > 0 else "" for v in container.datavalues]
                ax.bar_label(container, labels=labels, label_type='center', color='black', fontsize=9)

    for idx, scenario in enumerate(scenarios):
        ax = axes[idx]
        scenario_data = mean_user_counts.xs(scenario, axis=1)
        scenario_data.plot(
            kind='bar',
            stacked=True,
            figsize=(16, 10),
            width=0.9,
            ax=ax,
            colormap='summer'
        )
        ax.set_title(f"Request distibution each {time_step_ms} ms • {scenario}", fontsize=18, pad=20)
        ax.set_ylabel('# Requests', fontsize=12)
        ax.legend(title='Service', bbox_to_anchor=(1.02, 1), loc='upper left')
        ax.set_yticks(range(0, int(scenario_totals[scenario].max()) + 1, 1))
        handle_x_ticks(ax, stacked=True)
        if idx < num_plots - 1:
            ax.tick_params(labelbottom=False)

    plt.tight_layout(rect=[0, 0, 0.9, 1])
    #plt.show()
    plt.savefig(os.path.join(plot_path, f"binned_requests.png"))
    plt.close()

    return mean_user_counts

def sample_users(all_data: pd.DataFrame, sample_time_us: int = 500000) -> pd.DataFrame:
    if all_data is None or all_data.empty:
        return pd.DataFrame(columns=['timestamp', 'service', 'scenario', 'service_name', 'mu', 'users'])

    # Ensure necessary columns exist
    requests_df = all_data.copy()
    if 'service' not in requests_df.columns:
        requests_df['service'] = requests_df['extra_tags'].apply(parse_service_name)
    if 'service_name' not in requests_df.columns:
        requests_df['service_name'] = requests_df['extra_tags'].apply(parse_service_name)
    if 'mu' not in requests_df.columns:
        requests_df['mu'] = requests_df.get('mu', np.nan)

    max_time_us = int(requests_df['end_time_us'].max())
    time_points = range(0, max_time_us + sample_time_us, sample_time_us)

    records = []
    for t in time_points:
        active = requests_df[(requests_df['start_time_us'] <= t) & (t < requests_df['end_time_us'])]
        if active.empty:
            # optionally include zero rows for known service/scenario combos if desired
            continue

        # compute per-iteration concurrent counts, then average across iterations
        per_iter_counts = (
            active
            .groupby(['iteration', 'service', 'scenario', 'service_name', 'mu'])
            .size()
            .reset_index(name='count')
        )

        mean_counts = (
            per_iter_counts
            .groupby(['service', 'scenario', 'service_name', 'mu'], dropna=False)['count']
            .mean()
            .reset_index()
            .rename(columns={'count': 'users'})
        )

        mean_counts['timestamp'] = t
        # keep desired column order
        mean_counts = mean_counts[['timestamp', 'service', 'scenario', 'service_name', 'mu', 'users']]
        records.append(mean_counts)

    if not records:
        return pd.DataFrame(columns=['timestamp', 'service', 'scenario', 'service_name', 'mu', 'users'])

    result = pd.concat(records, ignore_index=True)
    # users is an average across iterations; keep float (or round/ceil as needed downstream)
    result['users'] = result['users'].astype(float)

    return result

def plot_sampled_users(sampled_df: pd.DataFrame, time_step_ms: int = 1_000, plot_path: str = "."):
    if sampled_df.empty:
        print("Nessun dato campionato disponibile per il grafico.")
        return

    df = sampled_df.copy()
    df['timestamp_ms'] = (df['timestamp'] // time_step_ms).astype(int)

    pivot = df.pivot_table(
        index='timestamp_ms',
        columns=['scenario', 'service', 'service_name', 'mu'],
        values='users',
        aggfunc='mean',
        fill_value=0
    )

    if pivot.empty:
        print("Impossibile aggregare i dati campionati per il grafico.")
        return

    pivot.columns = [' • '.join(map(str, col)) for col in pivot.columns]
    sns.set_style("whitegrid")
    ax = pivot.plot(
        kind='bar',
        stacked=True,
        width=0.9,
        colormap='summer',
        figsize=(30, 10)
    )

    ax.set_title(f"Users sampled each {time_step_ms} ms", fontsize=18, pad=20)
    ax.set_xlabel("Simulation Time (ms)", fontsize=12)
    ax.set_ylabel("# Users", fontsize=12)
    ax.legend(title='Scenario • Service • Service Name • μ', bbox_to_anchor=(0.95, 1), loc='upper left')

    num_ticks = len(ax.get_xticklabels())
    if num_ticks > 50:
        tick_spacing = max(1, num_ticks // 10)
        for i, label in enumerate(ax.get_xticklabels()):
            if i % tick_spacing != 0:
                label.set_visible(False)

    for container in ax.containers:
        labels = [f"{math.ceil(v)}" if v > 0 else "" for v in container.datavalues]
        ax.bar_label(container, labels=labels, label_type='center', color='black', fontsize=9)

    plt.tight_layout(rect=[0, 0, 0.9, 1])
    #plt.show()
    plt.savefig(os.path.join(plot_path, "sampled_users.png"))
    plt.close()

def histogram_completion_times_full(all_data: pd.DataFrame, all=False, tick_ms: int = 100, time_limit_ms: int = None, plot_path: str = "."):
    """
    Crea un istogramma dei tempi di completamento delle richieste.

    Args:
        all_data (pd.DataFrame): DataFrame contenente i dati delle richieste.
        bin_size_ms (int): Dimensione del bin in millisecondi.
    """
    if 'metric_value' not in all_data.columns:
        print("La colonna 'metric_value' non è presente nei dati.")
        return

    # get rid of outliers
    # completion_times_ms = all_data['metric_value']
    # calc the histogram

    # plot the histogram of each scenario-service couple
    for (scenario, service), group in all_data.groupby(['scenario', 'service_name']):
        if not all and service != 'all':
            continue

        times = group['metric_value']
        if times.empty:
            continue
        count, bins = np.histogram(times, bins=range(0, int(times.max() if not time_limit_ms else time_limit_ms) + tick_ms, tick_ms))
        plt.figure(figsize=(20, 6))
        plt.stairs(count / count.sum(), bins, color='skyblue', fill=True)
        plt.title(f"Completion times Histogram • {service} • {scenario}", fontsize=16)
        plt.xlabel("Completion Time (ms)", fontsize=14)
        plt.ylabel("# Requests", fontsize=14)
        plt.gca().xaxis.set_major_locator(MultipleLocator(tick_ms * 4, ))
        plt.grid(axis='y', alpha=0.75)
        #plt.show()
        plt.savefig(os.path.join(plot_path, f"histogram_completion_times_{service}_{scenario}.png"))
        plt.close()

        # and now the cdf
        cdf = np.cumsum(count) / count.sum()
        plt.figure(figsize=(20, 6))
        plt.stairs(cdf, bins, color='skyblue', fill=True)
        plt.title(f"Completion times CDF • {service} • {scenario}", fontsize=16)
        plt.xlabel("Completion Time (ms)", fontsize=14)
        plt.ylabel("# Requests", fontsize=14)
        plt.yticks(np.arange(0, 1.1, 0.1))
        plt.gca().xaxis.set_major_locator(MultipleLocator(tick_ms * 4))
        plt.grid(axis='y', alpha=0.75)
        #plt.show()
        plt.savefig(os.path.join(plot_path, f"cdf_completion_times_{service}_{scenario}.png"))
        plt.close()

        #print(f"Media tempi di completamento per {service} • {scenario}: {times.mean()} ms")
        #print(f"CDF: " + ", ".join([f"{cdf[i]:.2f}" for i in range(len(cdf))]))

def load_single_performance_results(num_cores: list, mu: list, service: str, concurrent_users: int, iteration: int, path: str = None) -> pd.DataFrame | None:
    folder_path = path
    
    file_path = os.path.join(folder_path, "metrics.json")
    with open(file_path) as train_file:
        dict = json.load(train_file)

    df = pd.json_normalize(dict['metrics'])
    df['users'] = df['vus_max.values.max']
    df['iteration'] = iteration
    df['duration'] = df['http_req_duration.values.avg']
    df['service'] = service
    df['mu'] = mu[0]
    df['cores'] = num_cores[0]

    return df

def load_performance_results(combinations) -> pd.DataFrame:
    # Load the results.
    df = pd.DataFrame()
    RESULT_FOLDER = 'base'
    
    for exp in combinations:
        service_type = exp['type']
        arg = exp['arg_values']
        path_incomplete = os.path.join(RESULT_FOLDER, service_type, "performance", f"{get_s([1])}_core", str(get_s(arg)), f"{str(1)}_users")
        if os.path.exists(path_incomplete):
            for iteration in os.listdir(path_incomplete):
                path = os.path.join(path_incomplete, str(iteration))
                df = pd.concat([df, load_single_performance_results([1], [arg], service_type, [1], iteration, path=path)], ignore_index=True)
        else:
            if service_type in ["deterministic"]:
                print("Check if the service name is correct.")
                for i in range(101):
                    data = {
                        'users': 1,
                        'iteration': 1,
                        'duration': arg[0] + random.uniform(-arg[0] * 0.01, arg[0] * 0.1),
                        'service': service_type,
                        'mu': arg[0],
                        'cores': 1
                    }

                    df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)

    # remove the columns whose names contain the string 'contains' and 'type'
    df = df.loc[:,~df.columns.str.contains('contains|type')]
    # calc std
    df['duration_std'] = df.groupby(['service', 'mu', 'cores', 'users'])['duration'].transform('std')
    df = df.groupby(['service', 'mu', 'cores', 'users', 'duration_std']).agg({'duration': 'mean'}).reset_index()
    df['job_size'] = df['duration']

    return df.fillna(0)

def calc_mean_users_per_workflow(all_data: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola il numero medio di utenti per ogni workflow.
    """
    if all_data.empty:
        print("DataFrame vuoto: impossibile calcolare il numero medio di utenti.")
        return pd.DataFrame(columns=["scenario", "mean_users"])

    df = all_data[["scenario", "service_name", "service", "mu", "cores", "start_time_us", "end_time_us", 'iteration']].copy()

    users = (df.groupby(["scenario", "service_name", "service", "mu", 'iteration', "cores"], dropna=False)
        .apply(lambda x: calculate_concurrency(x, x['start_time_us'].min(), x['end_time_us'].max()))
        .reset_index(level=[0,1,2])
        .groupby(["scenario", "service_name", 'timestamp', "service", "mu", "cores"], dropna=False)["concurrent_users"]
        .mean()
        .reset_index()
    )

    users["concurrent_users"] = users["concurrent_users"].apply(lambda x: math.ceil(x)).astype(int)
    
    result = (
        users
        .groupby(["scenario", "service_name", "service", "mu", "cores"], dropna=False)["concurrent_users"]
        .mean()
        .reset_index()
        .rename(columns={"concurrent_users": "mean_users"})
        .sort_values(["scenario", "service_name", "service", "mu", "cores"])
        .reset_index(drop=True)
    )

    return result

def get_theoretical_cdf(model_type, mean_users_per_workflow, performance_result, time_tick_ms: int, time_limit_ms: int) -> list[float]:
    process = Popen(['java', '-cp', '../../rospo-1.0-SNAPSHOT.jar', 'parallel.Py4jEntryPoint'])
    print(process.pid)
    sleep(1)  # wait for the JVM to start

    try:
        from py4j.java_gateway import JavaGateway
        gateway = JavaGateway()
        from py4j.java_gateway import java_import
        java_import(gateway.jvm,'java.math.*')

        print( "Setting model..." )
        print( f"Model type: {model_type}" )

        mean_users_per_workflow_cp = mean_users_per_workflow.copy()
        mean_users_per_workflow_cp = mean_users_per_workflow_cp.groupby(['service_name', 'service', 'mu', 'cores']).sum().reset_index()

        loadMap = gateway.jvm.java.util.HashMap()
        coreMap = gateway.jvm.java.util.HashMap()  
        keys = gateway.new_array(gateway.jvm.java.lang.String, len(mean_users_per_workflow_cp))

        for i, row in enumerate(mean_users_per_workflow_cp.itertuples()):
            key = f"{row.service_name}"
            duration = (performance_result[(performance_result['service'] == row.service) & (performance_result['mu'] == row.mu)]['duration'].values[0])
            keys[i] = key

            match row.service:
                case "deterministic":
                    print("Adding deterministic distribution for", key, "with duration", duration)
                    gateway.entry_point.addDeterministicDistribution(float(duration))
                case "exponential" | "exponentialop":
                    print("Adding exponential distribution for", key, "with duration", duration)
                    gateway.entry_point.addExponentialDistribution(key, float(1 / duration))
                    time_limit_ms = int(duration) * 10 if time_limit_ms < 0 else time_limit_ms
                case "erlang":
                    print("Adding erlang distribution for", key, "with duration", duration)
                    gateway.entry_point.addErlangDistribution(key, int(duration[0]), float(duration[1]))
                case "uniform":
                    print("Adding uniform distribution for", key, "with duration", duration)
                    gateway.entry_point.addUniformDistribution(key, float(duration[0]), float(duration[1]))
                case "trunc_exp":
                    print("Adding truncated exponential distribution for", key, "with duration", duration)
                    gateway.entry_point.addTruncatedExponentialDistribution(key, float(duration[0]), float(duration[1]), float(duration[2]))
                case _:
                    gateway.entry_point.addExponentialDistribution(key, float(1 / duration))

            print("Adding load and cores for", key, "with mean users", row.mean_users, "and cores", row.cores)
            loadMap.put(key, float(row.mean_users))
            coreMap.put(key, int(row.cores))

        gateway.entry_point.setModel(model_type, keys)
        theoretical_cdf = list(gateway.entry_point.evalModel(coreMap, loadMap, float(time_tick_ms), float(time_limit_ms)))

        gateway.close()
        gateway.shutdown()
    except Exception as e:
        print("Errore durante l'esecuzione del modello teorico:", e)
        theoretical_cdf = []

    return theoretical_cdf

def derive_theoretical_pdf(theoretical_cdf: list[float], time_tick_ms: int) -> list[float]:
    theoretical_pdf = []
    for i in range(1, len(theoretical_cdf)):
        pdf_value = (theoretical_cdf[i] - theoretical_cdf[i - 1]) / (time_tick_ms)
        theoretical_pdf.append(pdf_value)
    return theoretical_pdf

def dominance(cdf1: list[float], cdf2: list[float], time_tick_ms:int) -> float:
    """
    Calcola la dominanza tra due CDF.
    Restituisce:
        1 se cdf1 domina cdf2,
        -1 se cdf2 domina cdf1,
        0 se nessuna domina l'altra.
    """
    pdf1 = derive_theoretical_pdf(cdf1, time_tick_ms)
    integrate = 0;

    for i in range(len(pdf1)):
        integrate += (1 - cdf2[i]) * pdf1[i] * time_tick_ms # * (i * time_tick_ms)

    return integrate

def pairwise_compliance(cdf1: list[float], cdf2: list[float], time_tick_ms:int) -> float:
    return math.fabs(dominance(cdf1, cdf2, time_tick_ms) - 0.5)

def compare_cdfs(iteration_results, model_type, mean_users_per_workflow, performance_result, time_tick_ms: int = 100, time_limit_ms: int = 250, plot_path: str = "."):
    """
    Confronta le CDF teoriche con quelle misurate e crea un grafico.

    Args:
        iteration_results (pd.DataFrame): DataFrame contenente i risultati delle iterazioni.
        theoretical_cdf (list): Lista delle CDF teoriche calcolate.
        time_tick_ms (int): Intervallo di tempo in millisecondi per il calcolo della CDF.
        time_limit_ms (int): Limite massimo di tempo in millisecondi per il grafico.
    """
    grouping = ['service_name', 'scenario'] if len(model_type) != 1 else "service_name"
    for i, (_, group) in enumerate(iteration_results.groupby(grouping)):
        times = group['metric_value']
        service = group['service_name'].iloc[0]
        scenario = group['scenario'].iloc[0]
        if times.empty:
            continue
        count, bins = np.histogram(times, bins=range(0, int(times.max()), time_tick_ms))
        cdf_measured = np.cumsum(count) / count.sum()
        cdf_measured = np.pad(cdf_measured, (1, 0))

        time_limit_ms = time_limit_ms if time_limit_ms > int(times.max()) else int(times.max())

        theoretical_cdf = get_theoretical_cdf(model_type[i], mean_users_per_workflow, performance_result, time_tick_ms, time_limit_ms)[:len(bins)]
        compliance = pairwise_compliance(cdf_measured, theoretical_cdf, time_tick_ms)

        figsize=(20, 10) if service == "all" else (10, 5)
        plt.figure(figsize=figsize)
        plt.plot(bins, cdf_measured, color='gold', label='Observed', linewidth=2)
        
        # plot the theoretical cdf
        #theoretical_cdf.pop(0)
        #theoretical_cdf = theoretical_cdf[1:]
        plt.plot(bins, theoretical_cdf, color='purple', label='Theoretical', alpha=0.7, linewidth=2)

        plt.title(f"CDF comparison compliance {compliance:4f} • {service} • {scenario}", fontsize=16)
        plt.xlabel("Completion Time (ms)", fontsize=14)
        plt.ylabel("CDF", fontsize=14)
        plt.yticks(np.arange(0, 1.1, 0.1))
        plt.gca().xaxis.set_major_locator(MultipleLocator(time_limit_ms // time_tick_ms))
        plt.grid(axis='y', alpha=0.75)
        plt.legend()
        #plt.show()
        plt.savefig(os.path.join(plot_path, f"compare_cdfs_{model_type[i]}_{service}_{scenario}.png"))
        plt.close()

def compare_all_cdfs(test_result, mean_users_per_workflow, performance_result, time_tick_ms: int = 100, time_limit_ms: int = 250, plot_path: str = "."):
    service_names = test_result['service_name'].unique()
    for service_name in service_names:
        compare_cdfs(test_result[test_result["service_name"] == service_name], ["simple"], mean_users_per_workflow[mean_users_per_workflow["service_name"] == service_name], performance_result, time_tick_ms, time_limit_ms, plot_path=plot_path)

def get_scv(service: str, params: list[float]) -> float:
    """
    Returns the squared coefficient of variation for the service times
    of a stochastic process, the ratio between the variance and the mean squared.
    """
    match service:
        case "deterministic" | "deterministic_core":
            return 0.0
        case "exponential" | "exponentialop":
            return 1.0
        case "uniform":
            a = params[0]
            b = params[1]
            variance = (b - a) ** 2 / 12
            mean = (a + b) / 2
            return variance / (mean ** 2)
        case _:
            variance = params[0]
            mean = params[1]
            return variance / (mean ** 2)

def create_user_load_prediction_plot(requests_df: pd.DataFrame, performance_data: pd.DataFrame, recalc: bool = True, time_step_ms: int = 500, plot_path: str = ".") -> pd.DataFrame | None:
    requests_df = requests_df.copy()

    bin_width_us = time_step_ms * 1000

    requests_df['segment'] = requests_df['service'] + ' • ' + requests_df['scenario'] + ' • ' + requests_df['service_name']
    requests_df['start_bin_idx'] = (requests_df['start_time_us'] // bin_width_us).astype(int)
    requests_df['end_bin_idx'] = (
        (np.maximum(requests_df['end_time_us'] - 1, requests_df['start_time_us'])) // bin_width_us
    ).astype(int)

    # Calcola il numero di utenti concorrenti per ogni bin
    start_events = (
        requests_df.groupby(['iteration', 'segment', 'start_bin_idx'])
        .size()
        .rename('delta')
        .reset_index()
        .rename(columns={'start_bin_idx': 'bin_idx'})
    )
    end_events = (
        requests_df.groupby(['iteration', 'segment', 'end_bin_idx'])
        .size()
        .rename('delta')
        .reset_index()
        .rename(columns={'end_bin_idx': 'bin_idx'})
    )
    end_events['bin_idx'] += 1
    end_events['delta'] = -end_events['delta']

    events = pd.concat([start_events, end_events], ignore_index=True)
    events['bin_idx'] = events['bin_idx'].astype(int)
    changes = events.pivot_table(index=['iteration', 'bin_idx'], columns='segment', values='delta', aggfunc='sum', fill_value=0)

    min_bin = int(requests_df['start_bin_idx'].min())
    max_bin = int(requests_df['end_bin_idx'].max()) + 1
    iterations = sorted(requests_df['iteration'].unique())
    full_index = pd.MultiIndex.from_product([iterations, range(min_bin, max_bin + 1)], names=['iteration', 'bin_idx'])
    changes = changes.reindex(full_index, fill_value=0)

    user_counts = changes.groupby(level='iteration').cumsum()
    mean_user_counts = user_counts.groupby(level='bin_idx').mean()
    
    if mean_user_counts.empty:
        print("Impossibile calcolare la media delle richieste attive.")
        return
    
    mean_user_counts.index = mean_user_counts.index.astype(int) * time_step_ms

    column_tuples = []
    for seg in mean_user_counts.columns:
        parts = seg.split(' • ', 2)
        if len(parts) == 3:
            service, scenario, service_name = parts
        else:
            service, scenario, service_name = seg, 'sconosciuto', 'sconosciuto'
        column_tuples.append((scenario.strip(), service.strip(), service_name.strip()))
    mean_user_counts.columns = pd.MultiIndex.from_tuples(column_tuples, names=['scenario', 'service', 'service_name'])

    # Calcola i tempi osservati medi per scenario e servizio
    observed_times = (
        requests_df.groupby(['scenario', 'service', 'service_name', 'mu', 'lambda'])['metric_value']
        .mean()
        .reset_index()
        .rename(columns={'metric_value': 'observed_time_ms'})
    )

    # Calcola i tempi teorici usando la formula di check_law
    theoretical_times = []
    for _, row in observed_times.iterrows():
        scenario = row['scenario']
        service = row['service']
        service_name = row['service_name']
        mu = row['mu']
        
        # Ottieni il job_size dal performance_data
        perf_match = performance_data[
            (performance_data['service'] == service) &
            (performance_data['mu'] == mu) & 
            (performance_data['users'] == 1) &
            (performance_data['cores'] == 1)
        ]
        
        if not perf_match.empty:
            
            # Ottieni cores e mu dal test_result
            test_match = requests_df[
                (requests_df['scenario'] == scenario) & 
                (requests_df['service'] == service) & 
                (requests_df['service_name'] == service_name)
            ]
            
            if not test_match.empty:
                cores = int(test_match['cores'].iloc[0] * 1)#6
                l = test_match['lambda'].iloc[0]
                mean_users = mean_user_counts.loc[:, (slice(None), slice(None), service_name)][(np.abs(stats.zscore(mean_user_counts)) < 2).all(axis=1)].mean().sum()
                #mean_users = mean_users if mean_users > 1 else 1
                job_size = test_match['metric_value'].mean() * np.minimum(cores, mean_users) / mean_users if recalc else perf_match['job_size'].values[0]
                
                # Calcola il numero medio di utenti concorrenti per questo scenario/servizio
                # Somma tra di loro gli utenti che incidono sullo stesso service_name anche se su due scenari diversi
                service_rate = 1000 / (job_size)  
                ro = l / (service_rate)
                std = perf_match['duration_std'].values[0] if 'duration_std' in perf_match else 0
                mmk = ro + (ro / (1 - ro)) * erlangC(cores, ro * cores) * (get_scv(service, [mu, std]) + get_scv("deterministic", 1000 / (ro * mu * cores))) / 2
                print(f"Scenario: {scenario}, Service: {service}, Service Name: {service_name}, Lambda: {l}, Mu: {mu}, Cores: {cores}, Job Size: {job_size:.2f} ms, Mean Users: {mean_users:.2f}, Ro: {ro:.2f}, SCV: {get_scv(service, [mu, std]):.2f}, MMK: {mmk:.2f}")
                mean_mmk = 1 if mmk <= 1 else mmk
                theoretical_time = mean_mmk * job_size / np.minimum(cores, mean_mmk)

                # Calcola il tempo teorico: T = L * X / min(cores, L)               
                theoretical_times.append({
                    'scenario': scenario,
                    'service_name': service_name,
                    'service': service,
                    'mu': mu,
                    'lambda': l,
                    'theoretical_time_ms': theoretical_time,
                    'cores': cores,
                    'concurrent_users': mean_mmk
                })

    theoretical_df = pd.DataFrame(theoretical_times)
    
    # Merge observed and theoretical times
    comparison_df = observed_times.merge(theoretical_df, on=['scenario', 'service', 'service_name', 'lambda'], how='left')

    # Crea i grafici
    scenarios = sorted(requests_df['scenario'].unique())

    for scenario in scenarios:
        scenario_comparison = comparison_df[comparison_df['scenario'] == scenario]

        if scenario_comparison.empty:
            continue

        services = scenario_comparison['service_name'].unique()
        num_services = len(services)

        fig, axes = plt.subplots(1, num_services, figsize=(6 * num_services, 6))
        if num_services == 1:
            axes = [axes]

        for idx, service_name in enumerate(services):
            ax = axes[idx]
            service_data = scenario_comparison[scenario_comparison['service_name'] == service_name]

            if service_data.empty:
                continue

            x = np.arange(2)
            observed = service_data['observed_time_ms'].values[0]
            theoretical = service_data['theoretical_time_ms'].values[0] if not pd.isna(service_data['theoretical_time_ms'].values[0]) else 0

            bars = ax.bar(x, [observed, theoretical], color=['#2ecc71', '#e74c3c'], alpha=0.7, width=0.6)
            ax.set_xticks(x)
            ax.set_xticklabels(['Observed', 'Theoretical'])
            ax.set_ylabel('Simulation Time (ms)', fontsize=12)
            ax.set_title(f'{service_name}', fontsize=14, fontweight='bold')
            ax.grid(axis='y', alpha=0.3)

            # Aggiungi valori sopra le barre
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.2f}',
                       ha='center', va='bottom', fontsize=10, fontweight='bold')

        fig.suptitle(f'Completion Time Comparison: {scenario}{" (Recalculated)" if recalc else ""}', fontsize=16, fontweight='bold')
        plt.tight_layout()
        #plt.show()
        plt.savefig(os.path.join(plot_path, f"user_load_prediction_{scenario.replace(' ', '_')}{'_recalc' if recalc else ''}.png"))
        plt.close()

def create_user_load_prediction_comparison(requests_df: pd.DataFrame,
                                           theoretical_data: pd.DataFrame,
                                           recalc: bool = True,
                                           time_step_ms: int = 1000,
                                           plot_path: str = ".") -> pd.DataFrame:
    """
    Confronta l'andamento osservato con una predizione basata sulla formula T = L·X / R,
    usando finestre di 1 secondo.
    """
    if requests_df.empty:
        print("DataFrame vuoto: impossibile generare il confronto.")
        return pd.DataFrame()

    if 'service_name' not in requests_df.columns:
        requests_df = requests_df.copy()
        requests_df['service_name'] = requests_df['extra_tags'].apply(parse_service_name)

    required_cols = {'scenario', 'service_name', 'metric_value', 'start_time_us', 'end_time_us'}
    if not required_cols.issubset(requests_df.columns):
        missing = required_cols - set(requests_df.columns)
        raise ValueError(f"Mancano colonne necessarie nel DataFrame richiesto: {missing}")

    weight_df = theoretical_data.copy()

    if 'weight_ms' not in weight_df.columns:
        for cand in ('job_size', 'duration', 'mean_service_time_ms'):
            if cand in weight_df.columns:
                weight_df = weight_df.rename(columns={cand: 'weight_ms'})
                break
        else:
            raise ValueError("Il DataFrame teorico deve fornire un peso in ms (es. 'job_size').")

    if 'resources' not in weight_df.columns:
        if 'cores' in weight_df.columns:
            weight_df = weight_df.rename(columns={'cores': 'resources'})
        else:
            weight_df['resources'] = 1

    bin_width_us = time_step_ms * 1000
    df = requests_df.copy()
    df['segment'] = df['scenario'] + ' • ' + df["service"] + ' • ' + df['service_name']
    df['start_bin_idx'] = (df['start_time_us'] // bin_width_us).astype(int)
    df['end_bin_idx'] = ((np.maximum(df['end_time_us'] - 1, df['start_time_us'])) // bin_width_us).astype(int)

    start_events = (
        df.groupby(['iteration', 'segment', 'start_bin_idx'])
          .size().rename('delta').reset_index()
          .rename(columns={'start_bin_idx': 'bin_idx'})
    )
    end_events = (
        df.groupby(['iteration', 'segment', 'end_bin_idx'])
          .size().rename('delta').reset_index()
          .rename(columns={'end_bin_idx': 'bin_idx'})
    )
    end_events['bin_idx'] += 1
    end_events['delta'] = -end_events['delta']

    events = pd.concat([start_events, end_events], ignore_index=True)
    events['bin_idx'] = events['bin_idx'].astype(int)
    changes = events.pivot_table(index=['iteration', 'bin_idx'],
                                 columns='segment',
                                 values='delta',
                                 aggfunc='sum',
                                 fill_value=0)

    min_bin = int(df['start_bin_idx'].min())
    max_bin = int(df['end_bin_idx'].max()) + 1
    iterations = sorted(df['iteration'].unique())
    full_index = pd.MultiIndex.from_product([iterations, range(min_bin, max_bin + 1)],
                                            names=['iteration', 'bin_idx'])
    changes = changes.reindex(full_index, fill_value=0)

    user_counts = changes.groupby(level='iteration').cumsum()
    mean_user_counts = user_counts.groupby(level='bin_idx').mean()
    if mean_user_counts.empty:
        print("Impossibile calcolare la media delle richieste attive.")
        return pd.DataFrame()

    mean_user_counts.index = mean_user_counts.index.astype(int) * time_step_ms
    concurrency = mean_user_counts.stack().reset_index()
    concurrency.columns = ['time_ms', 'scenario_service', 'concurrent_users']

    concurrency[['scenario', 'service', 'service_name']] = concurrency['scenario_service'].str.split(' • ', n=2, expand=True)
    concurrency.drop(columns='scenario_service', inplace=True)
    concurrency['time_s'] = concurrency['time_ms'] / 1000.0

    observed = (
        df.groupby(['scenario', 'service_name', 'service', 'lambda' , 'mu', 'start_bin_idx'])['metric_value']
          .mean().rename('observed_time_ms').reset_index()
    )
    observed['time_ms'] = observed['start_bin_idx'] * time_step_ms
    observed['time_s'] = observed['time_ms'] / 1000.0
    observed.drop(columns='start_bin_idx', inplace=True)

    resource_lookup = (
        df.groupby(['scenario', 'service_name'])['cores']
          .first().rename('assigned_resources').reset_index()
        if 'cores' in df.columns else pd.DataFrame()
    )

    merge_keys = ['service', 'mu']
    if 'scenario' in weight_df.columns:
        merge_keys.append('scenario')
    weight_df = weight_df[weight_df['weight_ms'] > 0]

    comparison = concurrency.merge(observed, on=['scenario', 'service_name', 'service', 'time_ms', 'time_s'], how='left')
    comparison = comparison.merge(weight_df, on=merge_keys, how='left')
    if not resource_lookup.empty:
        comparison = comparison.merge(resource_lookup, on=['scenario', 'service_name'], how='left')

    if 'assigned_resources' in comparison.columns:
        comparison['resources'] = comparison['assigned_resources'].fillna(1)
    else:
        comparison['resources'] = 1
    comparison['resources'] = comparison['resources'].replace(0, 1) * 16
    comparison['effective_resources'] = comparison[['resources', 'concurrent_users']].min(axis=1).replace(0, 1)
    comparison = comparison.sort_values(['scenario', 'service', 'service_name', 'time_ms'])

    comparison['previous_users'] = (
        comparison.groupby(['scenario', 'service', 'service_name'])['concurrent_users'].shift(1)
    )
    comparison['previous_users'] = comparison['previous_users'].fillna(0)

    if recalc:
        # evaluate the job size from the observed time on the previous time step
        comparison['weight_ms'] = (
            (comparison['observed_time_ms'] * comparison['effective_resources']) / comparison['concurrent_users']
        ).shift(1)
        comparison['weight_ms'] = comparison['weight_ms'].fillna(0)
    else:
        # Use theoretical data, great when no interfering services
        comparison['weight_ms'] = (
            comparison.groupby(['scenario', 'service', 'service_name'])['weight_ms']
                    .ffill()
                    .bfill()
        )
        
    comparison['predicted_time_ms'] = (comparison['previous_users'] * comparison['weight_ms']) / comparison['effective_resources']
    
    scenarios = sorted(comparison['scenario'].dropna().unique())
    for scenario in scenarios:
        scenario_df = comparison[comparison['scenario'] == scenario].dropna(subset=['observed_time_ms', 'predicted_time_ms'])
        if scenario_df.empty:
            continue

        services = sorted(scenario_df['service_name'].unique())
        fig, axes = plt.subplots(len(services), 1, figsize=(18, 4 * len(services)), sharex=True)
        if len(services) == 1:
            axes = [axes]

        for ax, service_name in zip(axes, services):
            service_df = scenario_df[scenario_df['service_name'] == service_name]
            ax.plot(service_df['time_s'], service_df['observed_time_ms'], label='Observed', marker='o', linewidth=1.6)
            ax.plot(service_df['time_s'], service_df['predicted_time_ms'], label='Predicted', marker='s', linewidth=1.6)
            ax.set_title(f"{scenario} • {service_name} {'(Recalculated)' if recalc else ''}", fontsize=16, pad=20)
            ax.set_ylabel("Completion Time (ms)")
            ax.grid(alpha=0.3)
            ax.set_xticks(service_df['time_s'])
            ax.legend()

        axes[-1].set_xlabel("Simulation Time (s)")
        plt.tight_layout()
        #plt.show()
        plt.savefig(os.path.join(plot_path, f"user_load_prediction_comparison_{scenario.replace(' ', '_')}{'_recalc' if recalc else '_theoretical'}.png"))
        plt.close()

    return comparison

def create_user_load_prediction_comparison_2(requests_df: pd.DataFrame, performance_result: pd.DataFrame, time_tick_us: int = 1_000_000, plot_path: str = ".") -> pd.DataFrame:
    """
    Confronta l'andamento osservato con una predizione basata sulla formula T = L·X / R,
    usando finestre di 1 secondo.
    """

    # get the mean times from the data requests for each time_tick_us
    df = requests_df.copy()
    df['segment'] = df['scenario'] + ' • ' + df["service"] + ' • ' + df['service_name']
    df['start_bin_idx'] = (df['start_time_us'] // time_tick_us).astype(int)
    df['end_bin_idx'] = ((np.maximum(df['end_time_us'] - 1, df['start_time_us'])) // time_tick_us).astype(int)
    
    times = (
        df.groupby(['service_name', 'service', 'mu', 'start_bin_idx'])['metric_value']
          .mean().rename('observed_time_ms').reset_index()
    )
    times.rename(columns={"start_bin_idx": "bin_idx"}, inplace=True)
    times["time_s"] = times["bin_idx"] * (time_tick_us / 1_000_000.0)
    times["time_ms"] = times["time_s"] * 1000.0

    sampled_users = sample_users(df, time_tick_us)
    sampled_users["bin_idx"] = (sampled_users["timestamp"] // time_tick_us).astype(int)

    base_services = (
        df.groupby("service_name")
        .agg(
            service=("service", "first"),
            mu=("mu", "first"),
            cores=("cores", "first")
        )
        .reset_index()
    )
    base_services["cores"] = base_services["cores"].fillna(1).replace(0, 1).astype(int)
    base_services["mu"] = base_services["mu"].fillna(0)

    min_bin = int(df["start_bin_idx"].min())
    max_bin = int(df["end_bin_idx"].max())
    bin_indices = range(min_bin, max_bin + 1)

    if times.empty:
        raise ValueError("Impossibile calcolare tempi osservati per i bin selezionati.")

    observed_max = times["observed_time_ms"].max()
    if pd.isna(observed_max):
        observed_max = time_tick_ms

    predicted_records: list[dict[str, float]] = []
    for bin_idx in bin_indices:
        bin_users = (
            sampled_users[sampled_users["bin_idx"] == bin_idx]
            .groupby("service_name")["users"]
            .sum()
            .rename("mean_users")
            .reset_index()
        )

        mean_users_per_workflow = base_services.merge(bin_users, on="service_name", how="left")
        mean_users_per_workflow["mean_users"] = mean_users_per_workflow["mean_users"].fillna(0.0)

        for sn in mean_users_per_workflow["service_name"].unique():
            if sn == 'all':
                continue
            mean_users_per_workflow_sn = mean_users_per_workflow[mean_users_per_workflow["service_name"] == sn]
            theoretical_cdf = get_theoretical_cdf(
                "simple",
                mean_users_per_workflow_sn,
                performance_result,
                time_tick_ms,
                -1.
            )

            predicted_mean_ms = np.nan
            
            total = 0.0
            for v in theoretical_cdf:
                total = total + (1 - v) * time_tick_ms

            predicted_mean_ms = total

            predicted_records.append(
                {
                    "bin_idx": bin_idx,
                    #"scenario": mean_users_per_workflow_sn["scenario"].values[0],
                    "service_name": sn,
                    "service": mean_users_per_workflow_sn["service"].values[0],
                    "mu": mean_users_per_workflow_sn["mu"].values[0],
                    "time_s": bin_idx * (time_tick_us / 1_000_000.0),
                    "predicted_time_ms": predicted_mean_ms
                }
            )

    predicted_df = pd.DataFrame(predicted_records)
    predicted_df["predicted_time_ms"] = predicted_df["predicted_time_ms"].fillna(0)
    comparison = times.merge(predicted_df, on=["bin_idx", "time_s", "service_name", 'service', "mu"], how="left")
    comparison = comparison.sort_values(["service_name", "service", "time_s"]).reset_index(drop=True)

    for service_name, group in comparison.groupby("service_name", dropna=False):
        if group.empty:
            continue

        plt.figure(figsize=(12, 4))
        plt.plot(group["time_s"], group["observed_time_ms"], marker="o", linewidth=1.6, label="Observed")
        if group["predicted_time_ms"].notna().any():
            plt.plot(group["time_s"], group["predicted_time_ms"], marker="s", linewidth=1.6, label="Predicted")
        plt.title(f"{service_name}", fontsize=14, pad=12)
        plt.xlabel("Simulation Time (s)")
        plt.ylabel("Completion Time (ms)")
        plt.grid(alpha=0.3)
        plt.legend()
        plt.tight_layout()
        #plt.show()
        plt.savefig(os.path.join(plot_path, f"user_load_prediction_comparison_2_{service_name.replace(' ', '_')}.png"))
        plt.close()

if __name__ == "__main__":
    args = parse_args()
    options = get_test_options(args.path)
    plot_path = os.path.join(args.path, "plots")
    os.makedirs(plot_path, exist_ok=True)

    print(options)
    test_result = load_results(options)
    iteration_results = load_results(options, metric_name="iteration_duration")

    mean_service_times = compute_mean_service_time(test_result)
    # USERS LOAD PLOTS
    mean_user_counts = create_user_load_plot(test_result, 0.15 * 1_000, plot_path=plot_path)
    sampled_users = sample_users(test_result, 10 * 100_000)
    plot_sampled_users(sampled_users, plot_path=plot_path)

    # HISTOGRAM OF COMPLETION TIMES
    time_tick_ms = 10
    time_limit_ms = 250
    histogram_completion_times_full(iteration_results, True, time_tick_ms, time_limit_ms, plot_path=plot_path)
    # for completion, but wait
    if False:
        histogram_completion_times_full(test_result, True, time_tick_ms, time_limit_ms, plot_path=plot_path)


    performance_result = load_performance_results(extract_unique_pairs(options["WORKFLOW"]))
    # CDFs
    mean_users_per_workflow = calc_mean_users_per_workflow(test_result)
    compare_cdfs(iteration_results, [options["TEST_SERVICE"].split('_')[1], "simple"], mean_users_per_workflow, performance_result, time_tick_ms, 1000, plot_path=plot_path)
    compare_all_cdfs(test_result, mean_users_per_workflow, performance_result, time_tick_ms, time_limit_ms, plot_path=plot_path)

    # OG
    create_user_load_prediction_plot(test_result, performance_result, recalc=False, time_step_ms=100, plot_path=plot_path)
    create_user_load_prediction_comparison(test_result, performance_result, False, time_step_ms=1000, plot_path=plot_path)
    create_user_load_prediction_comparison_2(test_result, performance_result, plot_path=plot_path)