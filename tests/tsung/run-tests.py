import os
import subprocess
import time
import shutil
import re
import math
import json
from argparse import ArgumentParser
from datetime import datetime
from io import BytesIO
import pandas as pd
from utility import TEST_PATH, SINGLE_TEST_PATH, OUPUT_PATH, LOG_FOLDER, NUM_REQUESTS, erlangC

frame = pd.DataFrame()

def rename_test(index: int):
    # don't run me on new year's eve!
    pattern = re.compile(f'{datetime.now().year}')
    for folder in os.listdir(LOG_FOLDER):
        if pattern.match(folder):
            os.rename(f'{LOG_FOLDER}{folder}', f'{LOG_FOLDER}{index}_user0')
            break     


def get_completion_time():
    # run the test with a single user to get the completion time
    with open(SINGLE_TEST_PATH, 'r') as file:
        test_config = file.read()

        subprocess.run(['tsung', '-f', '-', '-l', LOG_FOLDER, 'start'], input=test_config, text=True)
    
    # rename the generated folder to avoid overwriting
    folder = rename_test(1)

    # analyze the data to get the completion time
    df = pd.read_csv(f'{LOG_FOLDER}1_user/tsung.dump', sep=';')

    # this is measured in milliseconds
    return df['duration'].max(), df['duration'].mean(), df['duration'].min()


def run_tests(config_file:str, arrival_rate: float, interarrival: float, max_users: int, num_requests: int):
    try:
        xml_config = config_file.replace('$$AR$$', str(arrival_rate)).replace('$$USR$$', str(max_users)).replace('$$IR$$', str(interarrival))

        if not os.path.exists(LOG_FOLDER):
            os.makedirs(os.path.dirname(LOG_FOLDER), exist_ok=True)
        
        print (f'Arrival rate: {(arrival_rate)}')
        print (f'Max Users: {(max_users)}')
        print (f'Interarrival: {(interarrival)}')
        subprocess.run(['tsung', '-f', '-', '-l', LOG_FOLDER, 'start'], input=xml_config, text=True)

        # rename the generated folder to avoid overwriting
        rename_test(num_requests)

    except Exception as e:
        print(f'Error running test {num_requests}')
        print(e)

if __name__ == '__main__':

    parser = ArgumentParser()
    parser.add_argument("-r", "--reset", action='store_true', help="Reset the log folder")

    args = parser.parse_args()

    if args.reset:
        if os.path.exists(LOG_FOLDER):
            for file in os.listdir(LOG_FOLDER):
                shutil.rmtree(f'{LOG_FOLDER}{file}')

    with open(TEST_PATH, 'r') as file:
        worst_completion_time, mean_completion_time, best_completion_time = get_completion_time()
        print(f'WCET: {worst_completion_time} MCET: {mean_completion_time} BCET: {best_completion_time}')

        test_config = file.read()
        for i in range(2, NUM_REQUESTS + 1):
            start_time = time.time()
            interarrival = (mean_completion_time / 1000 ) / i 
            arrival_rate = (i) * 1000 / (math.ceil(worst_completion_time) * 1.25)
            max_users = int(i * 60 * 1000 / best_completion_time)
            print(f'Starting test {i}...')
            run_tests(test_config, arrival_rate, interarrival, max_users, i)
            print(f'Test {i} took {time.time() - start_time} seconds to complete')

    # Load the data and create a single csv file, each test is in a different folder
    for i, directory in enumerate(os.listdir(os.path.dirname(LOG_FOLDER))):
        df = pd.read_csv(f'{LOG_FOLDER}{directory}/tsung.dump', sep=';')
        df['test'] = i + 1

        frame = pd.concat([frame, df], sort=False)

    if not os.path.exists(OUPUT_PATH):
            os.makedirs(os.path.dirname(OUPUT_PATH), exist_ok=True)

    frame.to_csv(OUPUT_PATH, index=False)
