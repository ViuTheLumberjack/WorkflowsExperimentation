import tempo from '../http-instrumentation-tempo.js';
import { group, sleep } from 'k6';

export const options = {
    summaryTimeUnit: 's',
    scenarios: {

        closed_loop_0: {
            executor: 'constant-vus',
            vus: 5,
            duration: '15s',
            exec: 'call_0',
        },

        closed_loop_1: {
            executor: 'constant-vus',
            vus: 5,
            duration: '15s',
            exec: 'call_1',
        },

    },
};

const instrumentedHTTP = new tempo.Client({
    propagator: 'w3c',
});

const API_URL = 'deterministic?millis=500';

async function call_and_010() {
    group('call_and_010', function () {
        instrumentedHTTP.get("http://localhost:8080/service/" + API_URL, {
            headers: {
                'X-Example-Header': 'instrumented/request',
            },
            tags: {
                service_name: 'first',
            },
        });
    });
}

async function call_and_011() {
    group('call_and_011', function () {
        instrumentedHTTP.get("http://localhost:8080/service/" + API_URL, {
            headers: {
                'X-Example-Header': 'instrumented/request',
            },
            tags: {
                service_name: 'first',
            },
        });
    });
}

export function call_seq_00() {
    // Make a GET request to the target URL

    const randomNumber = Math.random();
    if (randomNumber < 0.5) {
        instrumentedHTTP.get("http://localhost:8080/service/" + API_URL, {
            headers: {
                'X-Example-Header': 'instrumented/request',
            },
            tags: {
                service_name: 'first',
            },
        });;
    } else {
        instrumentedHTTP.get("http://localhost:8080/service/" + API_URL, {
            headers: {
                'X-Example-Header': 'instrumented/request',
            },
            tags: {
                service_name: 'first',
            },
        });;
    }

    Promise.all([
        call_and_010(),
        call_and_011()
    ]);

    instrumentedHTTP.get("http://localhost:8080/service/" + API_URL, {
        headers: {
            'X-Example-Header': 'instrumented/request',
        },
        tags: {
            service_name: 'first',
        },
    });
}

export function call_0() {
    // Make a GET request to the target URL
    call_seq_00()
}

export function call_1() {
    // Make a GET request to the target URL

    instrumentedHTTP.get("http://localhost:8081/service/" + API_URL, {
        headers: {
            'X-Example-Header': 'instrumented/request',
        },
        tags: {
            service_name: 'second',
        },
    });
}