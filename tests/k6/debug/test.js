// Import the http module to make HTTP requests. From this point, you can use `http` methods to make HTTP requests.
import http from 'k6/http';

export const options = {
    summaryTimeUnit: 's',
    scenarios: {
        average_time: {
            executor: 'constant-arrival-rate',
            rate: 11,
            duration: '30s',
            preAllocatedVUs: 2000,
        }
    },
};

const API_URL = `http://localhost:8080/service/exponentialop?max=50000000`;

export default function () {
    // Make a GET request to the target URL
    http.get(API_URL);
}