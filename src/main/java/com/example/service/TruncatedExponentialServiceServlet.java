package com.example.service;

import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Random;

import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

@WebServlet("/service/truncatedExponential")
public class TruncatedExponentialServiceServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;
    private Random random = new Random();

    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response) throws IOException {
        String paramLambda = request.getParameter("lambda");
        String paramEFT = request.getParameter("EFT");
        String paramLFT = request.getParameter("LFT");

        if (paramLambda == null || paramLambda.isEmpty() || paramEFT == null || paramEFT.isEmpty() || paramLFT == null || paramLFT.isEmpty()) {
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Parameters 'lambda', 'EFT' and 'LFT' are required");
            return;
        }

        double lambda = Double.parseDouble(paramLambda);
        double EFT = Double.parseDouble(paramEFT);
        double LFT = Double.parseDouble(paramLFT);
        if (lambda <= 0 || EFT < 0 || LFT < 0 || EFT >= LFT) {
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Invalid parameters for truncated exponential distribution");
            return;
        }

        // Generate a random delay following a truncated exponential distribution
        double delay = - Math.log(Math.exp(-lambda * EFT) - random.nextDouble() * (Math.exp(-lambda * EFT) - Math.exp(-lambda * LFT))) / lambda;

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
            "Truncated Exponential Distribution Delay: " + delay + " ms\n" +
            "Start time: " + sdf.format(new Date(startTime)) + "ms\n" +
            "Elapsed time: " + (System.currentTimeMillis() - startTime) + " ms\n" +
            "End time: " + sdf.format(new Date(System.currentTimeMillis())) + "ms"
        );
    }
}