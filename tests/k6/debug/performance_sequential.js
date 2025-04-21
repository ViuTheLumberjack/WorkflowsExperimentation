import tempo from 'https://jslib.k6.io/http-instrumentation-tempo/1.0.0/index.js';

export const options = {
    summaryTimeUnit: 'ms',
    scenarios: {
        average_time: {
            executor: 'constant-vus',
            vus: 2,
            duration: '30s'
        }
    },
};

const instrumentedHTTP = new tempo.Client({
    propagator: 'w3c',
});

const API_URL = `http://localhost:8080/service/sequential?n1=` + 75000000 + `&n2=` + 75000000;

export default function () {
    // Make a GET request to the target URL
    instrumentedHTTP.get(API_URL, {
        headers: {
            'X-Example-Header': 'instrumented/request',
        }
    });
}