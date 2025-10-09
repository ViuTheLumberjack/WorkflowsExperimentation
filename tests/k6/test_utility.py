import os
from workflow_parser import get_workflow
from docker_utility import SERVICES

TEST_TEMPLATE = """
import tempo from '../../http-instrumentation-tempo.js';
import { group, sleep } from 'k6';

export const options = {
    summaryTimeUnit: 's',
    scenarios: {
        {SCENARIOs}
    },
};

const instrumentedHTTP = new tempo.Client({
    propagator: 'w3c',
});

{FUNCTIONs}

export function handleSummary(data) {
    const title = `${__ENV.OUTPUT_PATH}/${__ENV.OUTPUT_NAME}`;
    var obj = {}
    obj[title] = JSON.stringify(data);

    return obj;
}
"""

OPEN_LOOP_EXECUTOR_TEMPLATE = """
{NAME}: {
    executor: 'constant-arrival-rate',
    rate: {RATE},
    duration: '60s',
    preAllocatedVUs: 4000
    exec: '{FN_NAME}',
},
"""

CLOSED_LOOP_EXECUTOR_TEMPLATE = """
{NAME}: {
    executor: 'constant-vus',
    vus: {USERS},
    duration: '15s',
    exec: '{FN_NAME}',
},
"""

SINGLE_CALL_TEMPLATE = """
    instrumentedHTTP.get({API_URL}, {
        headers: {
            'X-Example-Header': 'instrumented/request',
        },
        tags: {
            service_name: {SERVICE_TAG},
        },
    });"""

AND_FUNCTION_TEMPLATE = """
    async function {FN_NAME}() {
        group('{FN_NAME}', function () {
            {CALL_API_URL}
        });
    }"""

AND_CALL_TEMPLATE = """
    Promise.all([
        {FN}
    ]);"""

OR_CALL_TEMPLATE = """
    const randomNumber = Math.random();
    if (randomNumber < {PROB}) {
        {FN_CALL_TRUE};
    } else {
        {FN_CALL_FALSE};
    }"""

FUNCTION_TEMPLATE = """
export function {FN_NAME} () {
    // Make a GET request to the target URL
    {CALL_API_URL}
}
"""

def generate_test(options: dict) -> None:
    scenarios = ""
    functions = ""
    workflows = options["WORKFLOW"]
    loads = options["LOAD"]["loads"]
    out_folder = os.path.join(options["TEST_PATH"], options["RESULT_FOLDER"], "test.js")
    services_dict = {key: value for key, value in SERVICES}

    for i, (workflow, load) in enumerate(zip(workflows, loads)):
        fn_name = f"call_{i}"
        if load["type"] == "open_loop":
            scenario = OPEN_LOOP_EXECUTOR_TEMPLATE.replace("{NAME}", f"open_loop_{i}")
            scenario = scenario.replace("{RATE}", f"__ENV.RATE_{i}")
            scenario = scenario.replace("{FN_NAME}", fn_name)
        else:
            scenario = CLOSED_LOOP_EXECUTOR_TEMPLATE.replace("{NAME}", f"closed_loop_{i}")
            scenario = scenario.replace("{USERS}", f"__ENV.RATE_{i}")
            scenario = scenario.replace("{FN_NAME}", fn_name)
        scenarios += scenario

        def add_call(current, path):
            calls = []
            add_funcs = []
            if "services" in current:
                for j, child in enumerate(current["services"]):
                    child_call, addition_func = add_call(child, path + (j,))
                    
                    calls.append(child_call)
                    if addition_func:
                        add_funcs += addition_func

            match current["type"]:
                case "sequential": 
                    # add template for sequential, and recursively add calls for each branch
                    # use the data from calls to create the function body
                    fn_name = f"call_seq_{''.join(map(str, path + (0,)))}"
                    call_body = "\n".join(calls)
                    add_funcs.append(
                        FUNCTION_TEMPLATE.replace("{FN_NAME}", fn_name)
                        .replace("{CALL_API_URL}", call_body)
                    )

                    return f"{fn_name}()", add_funcs
                case "and":
                    # add template for and, and recursively add calls for each branch
                    all_names = []
                    for idx, call in enumerate(calls):
                        call = call.strip()
                        fn_name = f"and_{''.join(map(str, path + (idx,)))}"
                        all_names.append(f"{fn_name}()")

                        add_funcs.append(
                            AND_FUNCTION_TEMPLATE
                            .replace("{FN_NAME}", fn_name)
                            .replace("{CALL_API_URL}", call)
                        )

                    and_call = AND_CALL_TEMPLATE.replace("{FN}", ",\n\t".join(all_names))

                    return and_call, add_funcs
                case "or":
                    # add template for or, and recursively add calls for each branch
                    or_template = OR_CALL_TEMPLATE.replace("{PROB}", str(current["probability"]))
                    # must be two, if not it doesn't make sense
                    if len(calls) != 2:
                        raise ValueError("OR branch must have exactly two calls")

                    or_template = or_template.replace("{FN_CALL_TRUE}", calls[0].strip())
                    or_template = or_template.replace("{FN_CALL_FALSE}", calls[1].strip())

                    return or_template, add_funcs
                case _:
                    # add single call, we're in a leaf node
                    name = current["node_name"]
                    call_proto = SINGLE_CALL_TEMPLATE.replace("{SERVICE_TAG}", f"'{name}'")

                    return call_proto.replace("{API_URL}", f"\"http://localhost:{services_dict[name]}/service/\"+__ENV.API_URL_{''.join(map(str, path))}"), None     

        wf_functions, additional_funcs = add_call(workflow, (i,))
        function = FUNCTION_TEMPLATE.replace("{FN_NAME}", fn_name)
        function = function.replace("{CALL_API_URL}", wf_functions)
        if additional_funcs:
            functions += "\n".join(additional_funcs)
        functions += function  

    test_content = TEST_TEMPLATE.replace("{SCENARIOs}", scenarios)
    test_content = test_content.replace("{FUNCTIONs}", functions)

    #print(test_content)
    with open(out_folder, 'w') as f:
        f.write(test_content)

    return out_folder

if __name__ == "__main__":
    SERVICES = [("first", 8080), ("second", 8081), ("third", 8082)]

    options = {
        "TEST_PATH": os.path.dirname(__file__),
        "RESULT_FOLDER": "debug",
        "WORKFLOW": [
            {
                "node_name": "first",
                "type": "sequential",
                "services": [
                    {
                        "node_name": "first",
                        "type": "or",
                        "probability": 0.5,
                        "services": [
                            {
                                "node_name": "first",
                                "type": "deterministic",
                                "arg_name": "millis",
                                "arg_values": [
                                    1000
                                ]
                            },
                            {    
                                "node_name": "second",
                                "type": "deterministic",
                                "arg_name": "millis",
                                "arg_values": [
                                    2000
                                ]
                            }
                        ]
                    },
                    {
                        "node_name": "third",
                        "type": "and",
                        "services": [
                            {
                                "node_name": "second",
                                "type": "deterministic",
                                "arg_name": "millis",
                                "arg_values": [
                                    1002
                                ]
                            },
                            {    
                                "node_name": "third",
                                "type": "deterministic",
                                "arg_name": "millis",
                                "arg_values": [
                                    2003
                                ]
                            }
                        ]
                    },
                    {
                        "node_name": "third",
                        "type": "exponentialop",
                        "arg_name": "max",
                        "arg_values": [
                            25000000
                        ]
                    }
                ]
            },
            {
                "node_name": "second",
                "type": "deterministic",
                "arg_name": "millis",
                "arg_values": [
                    1000
                ]
            }
        ],
        "LOAD": {
            "start": 1,
            "end": 2,
            "loads": [
                {
                    "type": "closed_loop",
                    "users": [
                        5
                    ]
                },
                {
                    "type": "closed_loop",
                    "users": [
                        9
                    ]
                }
            ]
        },
        "NODES": [
            {
                "name": "first",
                "cores": [
                    1,
                    2,
                    3
                ]
            },
            {
                "name": "second",
                "cores": [
                    1,
                    2,
                    3
                ]
            }, 
            {
                "name": "third",
                "cores": [
                    1,
                    2,
                    3
                ]
            }
        ],
    }

    generate_test(options)