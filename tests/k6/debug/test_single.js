// Import the http module to make HTTP requests. From this point, you can use `http` methods to make HTTP requests.
import http from 'k6/http';
import exec from 'k6/execution';
import { group, sleep } from 'k6';

export const options = {
    summaryTimeUnit: 'ms',
    scenarios: {
        average_time: {
            executor: 'constant-vus',
            vus: 1,
            duration: '15s'
        }
    },
};

const API_URL = 'http://localhost:8080/service/deterministic?millis=500';

// Define the first sequential flow as an async function
async function flowA() {
    group('Flow A: Create and Update', function () {
        // 1. Sequential Call 1 in Flow A
        let createRes = http.get(API_URL);

        // Check/assert the response...
        // sleep(0.5); // Optional: Simulate think time between steps

        // 2. Sequential Call 2 in Flow A
        let updateRes = http.get(API_URL);

        // Check/assert the response...
    });
}

// Define the second sequential flow as an async function
async function flowB() {
    group('Flow B: Search and Retrieve', function () {
        // 1. Sequential Call 1 in Flow B
        let searchRes = http.get(API_URL);

        // Check/assert the response...
        // sleep(0.5); // Optional: Simulate think time between steps

        // 2. Sequential Call 2 in Flow B
        let retrieveRes = http.get(API_URL);

        // Check/assert the response...
    });
}

export default function () {
    // Use Promise.all to execute both flows concurrently (in parallel)
    Promise.all([
        flowA(),
        flowB()
    ]);

    // The VU will wait here until both flowA and flowB have completed.
    // The 'group_duration' for each flow will be recorded independently.
}

/*

export function handleSummary(data) {
    const title = `prova1_metrics.json`;
    var obj = {}
    obj[title] = JSON.stringify(data);

    return obj;
}
    */