// Import the http module to make HTTP requests. From this point, you can use `http` methods to make HTTP requests.
import http from 'k6/http';

export const options = {
    summaryTimeUnit: 'ms',
    scenarios: {
        average_time: {
            executor: 'constant-vus',
            vus: 1,
            duration: '1m'
        }
    },
};

const API_URL = `http://localhost:8080/service/exponentialop?max=` + __ENV.PARAM;

export default function () {
    // Make a GET request to the target URL
    http.get(API_URL);
}

export function handleSummary(data) {
    const title = `${__ENV.OUTPUT_PATH}/performance_${__ENV.PARAM}_metrics.json`;
    var obj = {}
    obj[title] = JSON.stringify(data);

    return obj;
}