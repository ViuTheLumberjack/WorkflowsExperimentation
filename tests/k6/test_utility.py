import os
from workflow_parser import get_workflow
from docker_utility import SERVICES

TEST_TEMPLATE = """
import tempo from '../../http-instrumentation-tempo.js';

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

CALL_TEMPLATE = """
    instrumentedHTTP.get({API_URL}, {
        headers: {
            'X-Example-Header': 'instrumented/request',
        },
        tags: {
            service_name: {SERVICE_TAG},
        },
    });"""

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
    

        # TODO: GENERA TUTTE LE CHIAMATE E NEL MAIN SOSTITUISCI CON GLI ARGOMENTI GIUSTI PER OGNI TIPO
        calls = ""
        if "services" in workflow:
            for j, element in enumerate(workflow.get("services", [])):
                name = element["node_name"]
                # call_api_url = get_workflow(element)
                call_proto = CALL_TEMPLATE.replace("{SERVICE_TAG}", f"'{name}'")
                calls += call_proto.replace("{API_URL}", f"\"http://localhost:{services_dict[name]}/service/\"+__ENV.API_URL_{str(i)+str(j)}")
                calls += "\n"
        else:
            # call_api_url = get_workflow(workflow)
            name = workflow["node_name"]
            call_proto = CALL_TEMPLATE.replace("{SERVICE_TAG}", f"'{name}'")
            calls += call_proto.replace("{API_URL}", f"\"http://localhost:{services_dict[name]}/service/\"+__ENV.API_URL_{str(i)}")
        # api_url = get_workflow(workflow)
        function = FUNCTION_TEMPLATE.replace("{FN_NAME}", fn_name)
        function = function.replace("{CALL_API_URL}", calls)
        functions += function

    test_content = TEST_TEMPLATE.replace("{SCENARIOs}", scenarios)
    test_content = test_content.replace("{FUNCTIONs}", functions)

    with open(out_folder, 'w') as f:
        f.write(test_content)

    return out_folder

if __name__ == "__main__":
    SERVICES = [("first", 8080), ("second", 8081)]

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
                        "type": "exponentialop",
                        "arg_name": "max",
                        "arg_values": [
                            25000000,
                            50000000
                        ]
                    },
                    {
                        "node_name": "second",
                        "type": "exponentialop",
                        "arg_name": "max",
                        "arg_values": [
                            25000000,
                            50000000
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
            }
        ],
    }

    generate_test(options)