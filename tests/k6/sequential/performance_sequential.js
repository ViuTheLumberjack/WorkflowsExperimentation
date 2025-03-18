import http from 'k6/http';
import { group, sleep } from 'k6';
import { URL } from 'https://jslib.k6.io/url/1.0.0/index.js';
import exec from 'k6/execution';

const API_URL = `https://crawler-test.com/redirects/`;
const INITIAL_URL = `${API_URL}redirect_2`; // Your starting URL
const allURLs = new Set();
const discoveredURLPaths = new Set();

// Create a basic options object
export const options = {
    summaryTimeUnit: 'ms',
    scenarios: {
        // First scenario - discovery mode
        discovery: {
            executor: 'per-vu-iterations',
            vus: 1,
            iterations: 1,
            maxDuration: '30s',
            exec: 'discoveryPhase',
            startTime: '0s',
        },
        // Second scenario - testing with thresholds
        testing: {
            executor: 'constant-vus',
            vus: 1,
            duration: '10s',
            exec: 'testingPhase',
            startTime: '5s', // Start after discovery is likely complete
        },
    },
    thresholds: {}, // Will be populated dynamically
};

// Discovery phase to find all URLs in the redirect chain
export function discoveryPhase() {
    console.log("Starting discovery phase...");

    let redirectCount = 0;
    let currentURL = INITIAL_URL;

    // Follow the redirect chain to discover all URLs
    while (true) {
        redirectCount++;

        const urlPath = new URL(currentURL).pathname.split('/').pop();
        discoveredURLPaths.add(urlPath);

        // Make request without auto-following redirects
        const res = http.get(currentURL, { redirects: 0 });
        allURLs.add(currentURL);

        // Check if we got a redirect
        if (res.status >= 300 && res.status < 400 && res.headers.Location) {
            // Get the next URL
            currentURL = res.headers.Location;

            // If relative URL, resolve it
            if (!currentURL.startsWith('http')) {
                const urlObj = new URL(res.url);
                currentURL = `${urlObj.origin}${currentURL}`;
            }
        } else {
            // No more redirects
            break;
        }

        // Safety check
        if (redirectCount > 10) {
            break;
        }
    }

    // Set up thresholds for all discovered URLs
    const urlPaths = Array.from(discoveredURLPaths);
    console.log(`Discovered URLs: ${JSON.stringify(urlPaths)}`);

    // Dynamically add thresholds for each discovered URL
    urlPaths.forEach(urlPath => {
        options.thresholds[`http_req_duration{url_name:${urlPath}}`] = ['avg>0'];
    });
}

// Testing phase that uses the discovered URLs and set thresholds
export function testingPhase() {
    // Wait to ensure discovery is complete
    if (exec.scenario.iterationInScenario === 0) {
        console.log("Starting testing phase...");
    }

    // Follow the same redirect chain but now with thresholds
    let redirectCount = 0;
    let currentURL = INITIAL_URL;
    let visitedURLs = [];

    while (true) {
        redirectCount++;

        const urlPath = new URL(currentURL).pathname.split('/').pop();

        group(`URL: ${urlPath}`, function () {
            // Make request with proper tagging
            const res = http.get(currentURL, {
                redirects: 0,
                tags: {
                    url_name: urlPath,
                    full_url: currentURL,
                    redirect_number: redirectCount
                }
            });

            visitedURLs.push(currentURL);

            // Check if we got a redirect
            if (res.status >= 300 && res.status < 400 && res.headers.Location) {
                // Get the next URL
                currentURL = res.headers.Location;

                // If relative URL, resolve it
                if (!currentURL.startsWith('http')) {
                    const urlObj = new URL(res.url);
                    currentURL = `${urlObj.origin}${currentURL}`;
                }
            } else {
                // No more redirects
                __ENV.exitLoop = true;
            }
        });

        if (__ENV.exitLoop) {
            delete __ENV.exitLoop;
            break;
        }

        // Safety check
        if (redirectCount > 10) {
            break;
        }
    }
}

export function handleSummary(data) {
    // Create a structured JSON with URL-based grouping
    const metrics = {};

    // Process metrics data
    Object.entries(data.metrics).forEach(([metricName, metricData]) => {
        // Look through all metric entries
        Object.entries(metricData).forEach(([key, value]) => {
            // Find metrics with URL tags
            if (value && typeof value === 'object' && value.tags && value.tags.url_name) {
                const urlName = value.tags.url_name;

                // Group metrics by URL
                if (!metrics[urlName]) {
                    metrics[urlName] = {};
                }
                if (!metrics[urlName][metricName]) {
                    metrics[urlName][metricName] = {};
                }
                metrics[urlName][metricName][key] = value;
            }
        });
    });

    // Output results
    const title = `performance_metrics.json`;
    const result = {};
    result[title] = JSON.stringify({
        discoveredURLs: Array.from(discoveredURLPaths),
        thresholds: options.thresholds,
        byUrl: metrics,
        urlChain: Array.from(allURLs),
        raw: data
    }, null, 2);

    return result;
}