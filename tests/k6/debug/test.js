// Import the http module to make HTTP requests. From this point, you can use `http` methods to make HTTP requests.
import tempo from '../http-instrumentation-tempo.js';

export const options = {
    summaryTimeUnit: 's',
    scenarios: {
        average_time: {
            executor: 'constant-arrival-rate',
            rate: 5,
            duration: '15s',
            preAllocatedVUs: 2000,
        }
    },
};

const API_URL = `http://localhost:8080/service/deterministic?millis=5`;
const instrumentedHTTP = new tempo.Client({
    propagator: 'w3c',
});

export default function () {
    // Make a GET request to the target URL
    instrumentedHTTP.get(API_URL, {
        headers: {
            'X-Example-Header': 'instrumented/request',
        }
    });
}


export function handleSummary(data) {
    const title = `test1_metrics.json`;
    var obj = {}
    obj[title] = JSON.stringify(data);

    return obj;
}