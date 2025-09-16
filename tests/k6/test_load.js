// Import the http module to make HTTP requests. From this point, you can use `http` methods to make HTTP requests.
import tempo from './http-instrumentation-tempo.js';
// import tempo from 'https://jslib.k6.io/http-instrumentation-tempo/1.0.0/index.js';

export const options = {
    summaryTimeUnit: 's',
    scenarios: {
        average_time: {
            executor: 'constant-arrival-rate',
            rate: __ENV.RATE,
            duration: '60s',
            preAllocatedVUs: 4000
        }
    },
};

const instrumentedHTTP = new tempo.Client({
    propagator: 'w3c',
});

const API_URL = `http://localhost:8080/service/` + __ENV.PARAM;

export default function () {
    // Make a GET request to the target URL
    instrumentedHTTP.get(API_URL, {
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