package com.example.service;

import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Random;

import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

@WebServlet("/service/exponential")
public class ExponentialServiceServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;
    private Random random = new Random();

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

        // Generate a random delay following an exponential distribution with the given lambda
        double delay = - Math.log(random.nextDouble()) / lambda;

        // Busy wait for the generated delay.
        long startTime = System.currentTimeMillis();
        while (System.currentTimeMillis() - startTime < delay) {
            Math.sqrt(2);
        }

        // Format the date.
        SimpleDateFormat sdf = new SimpleDateFormat("dd-MM-yyyy HH:mm:ss.SSS");

        // Return the result.
        response.setContentType("text/plain");
        response.getWriter().write(
            "Exponential Distribution Delay: " + delay + " ms\n" +
            "Start time: " + sdf.format(new Date(startTime)) + "ms\n" +
            "Elapsed time: " + (System.currentTimeMillis() - startTime) + " ms\n" +
            "End time: " + sdf.format(new Date(System.currentTimeMillis())) + "ms"
        );
    }
}