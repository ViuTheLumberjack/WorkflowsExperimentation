// Import the http module to make HTTP requests. From this point, you can use `http` methods to make HTTP requests.
import http from 'k6/http';
import exec from 'k6/execution';

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

const API_URL = 'http://localhost:8080/service/exponentialop?max=50000000';

export default function () {
    // Make a GET request to the target URL
    http.get(API_URL);
}

export function handleSummary(data) {
    const title = `prova1_metrics.json`;
    var obj = {}
    obj[title] = JSON.stringify(data);

    return obj;
}