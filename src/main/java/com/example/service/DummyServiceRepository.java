package com.example.service;

import io.opentelemetry.instrumentation.annotations.WithSpan;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.InvalidParameterException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Random;

import static java.lang.Math.sqrt;

public class DummyServiceRepository {
    private Random random = new Random();

    private String sendGetRequest(String urlString) throws IOException {
        URL url = new URL(urlString);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("GET");
        conn.connect();

        try (BufferedReader in = new BufferedReader(new InputStreamReader(conn.getInputStream()))) {
            String inputLine;
            StringBuilder content = new StringBuilder();
            while ((inputLine = in.readLine()) != null) {
                content.append(inputLine).append("\n\t\t");
            }
            return content.substring(0, content.length() - 1);
        } finally {
            conn.disconnect();
        }
    }

    @WithSpan
    public String doSequential(String endpoint1, String service1, String argument1, String paramN1, String endpoint2, String service2, String argument2, String paramN2) throws IOException {
        // First service.
        String response1 = sendGetRequest("http://" + endpoint1 + ":8080/service/" + service1 + "?" + paramN1 +"=" + argument1);
        // Second service.
        String response2 = sendGetRequest("http://" + endpoint2 + ":8080/service/" + service2 + "?" + paramN2 +"=" + argument2);
        /// Set response.

        return ("Composed Services:" +
                "\n\t- Service 1:\n\t\t" + response1 +
                "\n\t- Service 2:\n\t\t" + response2
        );
    }

    @WithSpan
    public String doAlternative(float probability, String endpoint1, String service1, String argument1, String paramN1, String endpoint2, String service2, String argument2, String paramN2) throws IOException {

        double randVal = random.nextDouble();

        String response;
        int i = 0;

        if (randVal < probability){
            // First service.
            i = 1;
            response = sendGetRequest("http://" + endpoint1 + ":8080/service/" + service1 + "?" + paramN1 +"=" + argument1);
        } else {
            // Second service.
            i = 2;
            response = sendGetRequest("http://" + endpoint2 + ":8080/service/" + service2 + "?" + paramN2 +"=" + argument2);
        }

        /// Set response.
        return ("Selected Service:" +
                "\n\t- Service "+ i +" :\n\t\t" + response
        );
    }

    @WithSpan
    public String doExponentialOperation(int max){
        // Generate a random delay following an exponential distribution with the given lambda
        double delay = (- Math.log(random.nextDouble())) * max;

        // Busy wait for the generated delay.
        long startTime = System.currentTimeMillis();

        double sum = 0;
        for (int i = 0; i < delay; i++){
            sum += sqrt(delay);
        }

        long endTime = System.currentTimeMillis();

        // Format the date.
        SimpleDateFormat sdf = new SimpleDateFormat("dd-MM-yyyy HH:mm:ss.SSS");

        // Return the result.
        return (
                "Exponential Distribution Delay: " + delay + " ms\n" +
                        "Start time: " + sdf.format(new Date(startTime)) + "ms\n" +
                        "Elapsed time: " + (endTime - startTime) + " ms\n" +
                        "End time: " + sdf.format(new Date(endTime)) + "ms"
        );
    }
}
