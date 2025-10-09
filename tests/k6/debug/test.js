
import tempo from '../http-instrumentation-tempo.js';

export const options = {
    summaryTimeUnit: 's',
    scenarios: {

        closed_loop_0: {
            executor: 'constant-vus',
            vus: __ENV.RATE_0,
            duration: '15s',
            exec: 'call_0',
        },

        closed_loop_1: {
            executor: 'constant-vus',
            vus: __ENV.RATE_1,
            duration: '15s',
            exec: 'call_1',
        },

    },
};

const instrumentedHTTP = new tempo.Client({
    propagator: 'w3c',
});


export function call_0() {
    // Make a GET request to the target URL

    instrumentedHTTP.get("http://localhost:8080/service/" + __ENV.CALL_00, {
        headers: {
            'X-Example-Header': 'instrumented/request',
        }
    });

    instrumentedHTTP.get("http://localhost:8081/service/" + __ENV.CALL_01, {
        headers: {
            'X-Example-Header': 'instrumented/request',
        }
    });

}

export function call_1() {
    // Make a GET request to the target URL

    instrumentedHTTP.get("http://localhost:8081/service/" + __ENV.CALL_1), {
        headers: {
            'X-Example-Header': 'instrumented/request',
        }
    });
}


export function handleSummary(data) {
    const title = `${__ENV.OUTPUT_PATH}/${__ENV.OUTPUT_NAME}`;
    var obj = {}
    obj[title] = JSON.stringify(data);

    return obj;
}
