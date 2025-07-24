import urllib.parse
from docker_utility import SERVICES

def get_num_services(workflow: dict) -> int:
    """
    Get the services in the workflow. With their relative argument.
    """
    # BFS on the dict which is a DAG, count leaves
    count = 1
    queue = [workflow]
    while queue:
        node = queue.pop(0)
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, dict):
                    queue.append(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            queue.append(item)
                        else:
                            count += 1
                else:
                    count += 1
        else:
            count += 1

    if workflow["type"] in ["sequential", "parallel", "choice"]:
        count += 1

    return count

def get_workflow(workflow: dict, args: list) -> list:
    if workflow["type"] in ["sequential", "parallel", "alternative"]:
        return get_simple_workflow_instance(workflow, args)
    elif workflow["type"] in ["exponentialop", "sum", "exponential", "deterministic", "uniform"]:
        return get_simple_service_instance(workflow, args)
    else:
        raise ValueError(f"Unknown workflow type")

def get_simple_workflow_instance(workflow: list, args: list) -> str:
    """
    Returns the api that must be called with the right params, 
    hence replacing the variables with the right values.
    """
    #in the workflow 
    wf_complete = {}
    wf_complete[f"p"] = workflow["p"] if "p" in workflow else 0.5
    for i in range(1, len(args) + 1):
        wf_complete[f"e{i}"] = SERVICES[i - 1][0]
        wf_complete[f"p{i}"] = SERVICES[i - 1][1]
        wf_complete[f"s{i}"] = workflow["services"][i - 1]["type"]
        wf_complete[f"n{i}"] = workflow["services"][i - 1]["arg_name"]
        wf_complete[f"a{i}"] = args[i - 1]

    return workflow["type"] + "?" + urllib.parse.urlencode(wf_complete)

def get_simple_service_instance(workflow: list, args: list) -> str:
    """
    Returns the api that must be called with the right params, 
    hence replacing the variables with the right values.
    """
    #in the workflow 
    wf_complete = {}
    
    if "arg_name" in workflow:
        wf_complete[workflow["arg_name"]] = args[0]
    elif "args" in workflow:
        for i, arg in enumerate(workflow["args"]):
            wf_complete[arg] = args[i] if i < len(args) else None

    return workflow["type"] + "?" + urllib.parse.urlencode(wf_complete)

def sequential_wf_test():
    SERVICES = [
        ("exponentialop_0", 8080),
        ("exponentialop_0", 8081),
    ]

    workflow = {
        "type": "sequential",
        "services": [
            {
                "type": "exponentialop",
                "arg_name": "max"
            },
            {
                "type": "exponentialop",
                "arg_name": "max"
            }
        ]
    }

    print(get_workflow(workflow, [1, 2]))

if __name__ == "__main__":
    SERVICES = [
        ("uniform_0", 8080)
    ]

    workflow = {
        "type": "uniform",
        "args": [
            "EFT",
            "LFT"
        ]
    }

    print(get_workflow(workflow, [1, 2]))


# workflow parses the workflow and returns the api that must be called
# /api/services/sequential?call=exponentialop&arg=max&val=750&next=exponentialop(max=750))&num=0
# when the first exponentialop finishes, calls whatever is in next
# /api/services/exponentialop?call=exponentialop&arg=max&val=750&next=None&num=1
