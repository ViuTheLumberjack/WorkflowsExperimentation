import os
import pandas as pd
from math import pow,factorial,log,exp
from matplotlib import colors, pyplot as plt

NUM_REQUESTS = 4
NUM_CORES = 2

TEST_SERVICE = 'A'
TEST_DURATION_S = 60

TEST_PATH = os.path.join(os.path.dirname(__file__), f'configurations/test_{TEST_SERVICE}.xml')
SINGLE_TEST_PATH = os.path.join(os.path.dirname(__file__), f'configurations/test_{TEST_SERVICE}_single.xml')
LOG_FOLDER = os.path.join(os.path.dirname(__file__), f'log/{TEST_SERVICE}/')
OUPUT_PATH = os.path.join(os.path.dirname(__file__), f'results/{TEST_SERVICE}/results.csv')
PLOT_PATH = os.path.join(os.path.dirname(__file__), f'results/{TEST_SERVICE}/plots/response_time_{NUM_CORES}cores_50.pdf')

def PowerFact(b,e):
    """
    Returns b^e / e! used everywhere else in the model
    
    Parameters:
        b (int): base
        e (int): exponent
    """
    return pow(b,e)/factorial(e)

def erlangC(m,p):
    """
    Returns the probability a call waits.

    Parameters:
        m   (int): agent count
        p (float): lambda over mu
    """
    suma = 0
    for k in range(0,m):
        suma += PowerFact(u,k)
    erlang = PowerFact(u,m) / ((PowerFact(u,m)) + (1-p)*suma)
    return erlang

# Plot the results.
def plot_results(df: pd.DataFrame, average: pd.DataFrame):
    if not os.path.exists(os.path.dirname(PLOT_PATH)):
        os.makedirs(os.path.dirname(PLOT_PATH), exist_ok=True)

    # Create the plot.
    plt.figure(figsize=(20, 12))

    # Plot the response time for each request.
    plt.scatter(df['grpThreads'], df['elapsed'], s=10, c=df['grpThreads'], cmap='spring', label='Response Time', alpha=0.5)
    
    # Plot the average response time.
    plt.plot(average['grpThreads'], average['elapsed'], marker='.', linestyle='-', markersize=10, color='red', label='Average Response Time')
    
    # Set the title and labels.
    plt.title(f'Response time over number of concurrent threads ({NUM_CORES} cores - SEQ)')
    plt.xlabel('Number of concurrent threads')
    plt.ylabel('Response time (ms)')

    # Annotate the average response time for each request.
    ax = plt.gca()
    ax.set_xlim([0, 101])
    for x, y in zip(average['grpThreads'], average['elapsed']):
        plt.annotate(f'{y:.1f}', (x, y), fontsize=8, weight='bold', textcoords="offset points", xytext=(0, 10), rotation=90, ha='center')

    # Show the grid and legend
    plt.grid(True)
    legend = plt.legend(loc='upper left')
    for lh in legend.legend_handles:
        lh.set_alpha(1)
    
    # Save the plot.
    plt.savefig(PLOT_PATH)

def plot_results_clamp(df: pd.DataFrame, average: pd.DataFrame):
    if not os.path.exists(os.path.dirname(PLOT_PATH)):
        os.makedirs(os.path.dirname(PLOT_PATH), exist_ok=True)

    plt.figure(figsize=(12, 6))

    # Plot the response time for each request.
    cmap = colors.LinearSegmentedColormap.from_list("", ["pink", "yellow"])
    plt.scatter(df['grpThreads'], df['elapsed'], s=10, c=df['grpThreads'], cmap=cmap, label='Response Time', alpha=0.05, rasterized=True)
    
    # Plot the average response time.
    plt.plot(average['grpThreads'], average['elapsed'], marker='.', linestyle='-', markersize=10, color='red', label='Average Response Time')
    
    # Set the title and labels.
    plt.title(f'Response time over number of concurrent threads ({NUM_CORES} cores - AND(A, B))')
    plt.xlabel('Number of concurrent threads')
    plt.ylabel('Response time (ms)')

    # Annotate the average response time for each request.
    ax = plt.gca()
    ax.set_xlim([0, 51])
    for x, y in zip(average['grpThreads'], average['elapsed']):
        plt.annotate(f'{y:.1f}', (x, y), fontsize=10, weight='bold', textcoords="offset points", xytext=(0, 10), rotation=90, ha='center')

    # Show the grid and legend
    ax.set_axisbelow(True)
    plt.grid(color = 'gray', linestyle = '--', linewidth = 0.8, alpha = 0.5)
    legend = plt.legend(loc='upper left')
    legend.legend_handles[0].set_alpha(1)

    
    # Save the plot.
    plt.tight_layout()
    plt.savefig(PLOT_PATH)