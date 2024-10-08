import os
import subprocess
import time
from utility import TEST_PATH, OUPUT_PATH, LOG_PATH, NUM_REQUESTS


def run_tests(num_requests: int):
    try:
        if not os.path.exists(OUPUT_PATH):
            os.makedirs(os.path.dirname(OUPUT_PATH), exist_ok=True)

        subprocess.call(['jmeter', '-n', '-t', TEST_PATH, '-l', OUPUT_PATH, '-j', LOG_PATH, f'-Jrequests={num_requests}'])

    except Exception as e:
        print(f'Error running test {num_requests}')
        print(e)

if __name__ == '__main__':
    for i in range(1, NUM_REQUESTS + 1):
        start_time = time.time()
        print(f'Starting test {i}...')
        run_tests(i)
        print(f'Test {i} took {time.time() - start_time} seconds to complete')