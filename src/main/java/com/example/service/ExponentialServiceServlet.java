package com.example.service;

import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Random;

import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import io.opentelemetry.instrumentation.annotations.WithSpan;

@WebServlet("/service/exponential")
public class ExponentialServiceServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;
    private Random random = new Random();

    @WithSpan
    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response) throws IOException {
        String paramLambda = request.getParameter("lambda");
        if (paramLambda == null || paramLambda.isEmpty()) {
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Parameter 'lambda' is required");
            return;
        }

        double lambda = Double.parseDouble(paramLambda);
        if (lambda <= 0) {
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Invalid exponential distribution parameter");
            return;
        }

        double sum = 0;
        double delay = -Math.log(random.nextDouble()) / lambda;

        // Busy wait for the generated delay.
        long startTime = System.currentTimeMillis();
        while (System.currentTimeMillis() - startTime < delay) {
            sum += Math.sqrt(2);
        }

        long endTime = System.currentTimeMillis();

        // Format the date.
        SimpleDateFormat sdf = new SimpleDateFormat("dd-MM-yyyy HH:mm:ss.SSS");

        // Return the result.
        response.setContentType("text/plain");
        response.getWriter().write(
                "Exponential Distribution Delay: " + delay + " ms\n" +
                        "Start time: " + sdf.format(new Date(startTime)) + "ms\n" +
                        "Elapsed time: " + (endTime - startTime) + " ms\n" +
                        "End time: " + sdf.format(new Date(endTime)) + "ms");
    }
}