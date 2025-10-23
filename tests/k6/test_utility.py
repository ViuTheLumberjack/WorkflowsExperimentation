import os
from workflow_parser import get_workflow
from docker_utility import SERVICES

TEST_TEMPLATE = """
import tempo from '../../http-instrumentation-tempo.js';
import { group, sleep } from 'k6';

const urls = [ {URLS} ];

export const options = {
    summaryTimeUnit: 's',
    thresholds: Object.fromEntries(
    ['http_req_duration', 'http_reqs', 'http_req_failed']
      .flatMap(metric => urls.map(url => [ `${metric}{url:${url}}`, []]))),
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
    duration: '30s',
    preAllocatedVUs: 2000,
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
    all_urls = []

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
            urls = []
            if "services" in current:
                for j, child in enumerate(current["services"]):
                    child_call, addition_func, child_urls = add_call(child, path + (j,))
                    calls.append(child_call)
                    if addition_func:
                        add_funcs += addition_func
                    if child_urls:
                        for url in child_urls:
                            if url not in urls:
                                urls.append(url)

            match current["type"]:
                case "sequential":
                    fn_name = f"call_seq_{''.join(map(str, path + (0,)))}"
                    call_body = "\n".join(calls)
                    add_funcs.append(
                        FUNCTION_TEMPLATE.replace("{FN_NAME}", fn_name)
                        .replace("{CALL_API_URL}", call_body)
                    )
                    return f"{fn_name}()", add_funcs, urls
                case "and":
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
                    return and_call, add_funcs, urls
                case "or":
                    or_template = OR_CALL_TEMPLATE.replace("{PROB}", str(current["probability"]))
                    if len(calls) != 2:
                        raise ValueError("OR branch must have exactly two calls")
                    or_template = or_template.replace("{FN_CALL_TRUE}", calls[0].strip())
                    or_template = or_template.replace("{FN_CALL_FALSE}", calls[1].strip())
                    return or_template, add_funcs, urls
                case _:
                    name = current["node_name"]
                    call_proto = SINGLE_CALL_TEMPLATE.replace("{SERVICE_TAG}", f"'{name}'")
                    base_url = f'"http://localhost:{services_dict[name]}/service/"'
                    api_url_expr = f"{base_url}+__ENV.API_URL_{''.join(map(str, path))}"
                    call = call_proto.replace("{API_URL}", api_url_expr)
                    return call, [], [api_url_expr]

        wf_functions, additional_funcs, wf_urls = add_call(workflow, (i,))

        function = FUNCTION_TEMPLATE.replace("{FN_NAME}", fn_name)
        function = function.replace("{CALL_API_URL}", wf_functions)
        if additional_funcs:
            functions += "\n".join(additional_funcs)
        functions += function  

        if wf_urls:
            for url in wf_urls:
                if url not in all_urls:
                    all_urls.append(url)

    url_entries = ",\n    ".join(all_urls)
    test_content = TEST_TEMPLATE.replace("{SCENARIOs}", scenarios)
    test_content = test_content.replace("{FUNCTIONs}", functions)
    test_content = test_content.replace("{URLS}", url_entries or "")

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