package com.example.service;

import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Random;

import static java.lang.Math.sqrt;

@WebServlet("/service/exponentialop")
public class ExponentialOperationServiceServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;
    private Random random = new Random();

    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response) throws IOException {
        String maxParameter = request.getParameter("max");
        if (maxParameter == null || maxParameter.isEmpty()) {
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Parameter 'lambda' is required");
            return;
        }

        double max = Double.parseDouble(maxParameter);
        if (max <= 0) {
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Invalid exponential distribution parameter");
            return;
        }

        // Generate a random delay following an exponential distribution with the given lambda
        double delay = - Math.log(random.nextDouble()) / max;

        // Busy wait for the generated delay.
        long startTime = System.currentTimeMillis();
        double sum = 0;
        for (int i = 0; i < delay; i++){
            sum += sqrt(2);
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
            "End time: " + sdf.format(new Date(endTime)) + "ms"
        );
    }
}