import os
import argparse
import json

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

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the tests")
    # Test args
    parser.add_argument('--path', type=str, default=None, help='Path to folder with experiments.json file')
    # Test type
    parser.add_argument('--all', action='store_true', help='Run all the tests')
    parser.add_argument('--closed_loop', action='store_true', help='Run closed loop tests')
    parser.add_argument('--open_loop', action='store_true', help='Run open loop tests')
    # Wildfly Args
    parser.add_argument('--limit_threads', action='store_true', default=False, help='Run the tests with limited threads')

    args = parser.parse_args()

    assert not (args.all and (args.closed_loop or args.open_loop)), "Cannot use --all with --closed_loop or --open_loop"
    assert args.path is not None, "Path to experiments.json file is required"

    return args

def get_test_options(path: os.path) -> dict:
    RESULT_FOLDER = os.path.join(path)
    TEST_SERVICE = os.path.basename(os.path.normpath(path))

    TEST_PATH = os.path.join(os.path.dirname(__file__))
    OPEN_LOOP_PATH = os.path.join(TEST_PATH, f'test_load.js')
    CLOSED_LOOP_PATH = os.path.join(TEST_PATH, f'test_performance.js')

    configuration = json.load(open(os.path.join(RESULT_FOLDER, 'experiments.json')))

    WORKFLOW = configuration["workflow"] if "workflow" in configuration else None
    LOAD = configuration["load"] if "load" in configuration else None
    NODES = configuration["nodes"] if "nodes" in configuration else None

    return {
        "RESULT_FOLDER": RESULT_FOLDER,
        "TEST_SERVICE": TEST_SERVICE,
        "TEST_PATH": TEST_PATH,
        #"OPEN_LOOP_PATH": OPEN_LOOP_PATH,
        #"CLOSED_LOOP_PATH": CLOSED_LOOP_PATH,
        "WORKFLOW": WORKFLOW,
        "LOAD": LOAD,
        "NODES": NODES
    }