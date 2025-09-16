// Import the http module to make HTTP requests. From this point, you can use `http` methods to make HTTP requests.
import http from 'k6/http';
import exec from 'k6/execution';

export const options = {
    summaryTimeUnit: 'ms',
    scenarios: {
        seq_2: {
            executor: 'constant-vus',
            vus: 7,
            duration: '15s',
            exec: 'seq_2',
        },
        expop: {
            executor: 'constant-vus',
            vus: 5,
            duration: '15s',
            exec: 'expop',
        },
    },
};

const API_URL1 = 'http://localhost:8080/service/sequential?p=0.5&e1=sequential_0&p1=8080&s1=deterministic&n1=millis&a1=100&e2=sequential_1&p2=8081&s2=deterministic&n2=millis&a2=200';
const API_URL2 = 'http://localhost:8081/service/deterministic?millis=500';

export function seq_2() {
    // Make a GET request to the target URL
    http.get(API_URL1);
}

export function expop() {
    // Make a GET request to the target URL
    http.get(API_URL2);
}

/*

export function handleSummary(data) {
    const title = `prova1_metrics.json`;
    var obj = {}
    obj[title] = JSON.stringify(data);

    return obj;
}
    */