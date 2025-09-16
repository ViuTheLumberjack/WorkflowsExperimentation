import os

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

FUNCTION_TEMPLATE = """
export function {FN_NAME} () {
    // Make a GET request to the target URL
    instrumentedHTTP.get({API_URL}, {
        headers: {
            'X-Example-Header': 'instrumented/request',
        }
    });
}
"""

def generate_test(options: dict) -> None:
    scenarios = ""
    functions = ""
    workflows = options["WORKFLOW"]
    loads = options["LOAD"]["loads"]
    out_folder = os.path.join(options["TEST_PATH"], options["RESULT_FOLDER"], "test.js")

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

        # api_url = calls[i]
        function = FUNCTION_TEMPLATE.replace("{FN_NAME}", fn_name)
        function = function.replace("{API_URL}", f"__ENV.API_URL_{i}")
        functions += function

    test_content = TEST_TEMPLATE.replace("{SCENARIOs}", scenarios)
    test_content = test_content.replace("{FUNCTIONs}", functions)

    with open(out_folder, 'w') as f:
        f.write(test_content)

    return out_folder