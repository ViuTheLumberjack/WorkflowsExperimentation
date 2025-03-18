// Import the http module to make HTTP requests. From this point, you can use `http` methods to make HTTP requests.
import http from 'k6/http';
import tempo from 'https://jslib.k6.io/http-instrumentation-tempo/1.0.0/index.js';

export const options = {
    summaryTimeUnit: 's',
    scenarios: {
        average_time: {
            executor: 'constant-arrival-rate',
            rate: __ENV.RATE,
            duration: '90s',
            preAllocatedVUs: 4000
        }
    },
};

const API_URL = `http://localhost:8080/service/exponentialop?max=` + __ENV.PARAM;
const instrumentedHTTP = new tempo.Client({
    propagator: 'w3c',
});

export default function () {
    // Make a GET request to the target URL
    // http.get(API_URL);

    let res = instrumentedHTTP.request('GET', API_URL, null, {
        headers: {
            'X-Example-Header': 'instrumented/request',
        },
    });
}

export function handleSummary(data) {
    const title = `${__ENV.OUTPUT_PATH}/${__ENV.RATE}_${__ENV.PARAM}_metrics.json`;
    var obj = {}
    obj[title] = JSON.stringify(data);

    return obj;
}