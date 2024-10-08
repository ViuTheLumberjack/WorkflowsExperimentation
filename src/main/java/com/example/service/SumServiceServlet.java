package com.example.service;

import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;

import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

@WebServlet("/service/sum")
public class SumServiceServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;

    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response) throws IOException {
        String paramN = request.getParameter("n");
        if (paramN == null || paramN.isEmpty()) {
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Parameter 'n' is required");
            return;
        }

        long n = Long.parseLong(paramN);
        if (n <= 0) {
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Invalid natural number");
            return;
        }

        // Calculate the sum of the first n natural numbers.
        long sum = 0;
        long startTime = System.currentTimeMillis();
        for (long i = 1; i <= n; i++) {
            sum += i;
        }

        // Format the date.
        SimpleDateFormat sdf = new SimpleDateFormat("dd-MM-yyyy HH:mm:ss.SSS");

        // Return the result.
        response.setContentType("text/plain");
        response.getWriter().write(
            "Sum of the first " + n + " natural numbers: " + sum + "\n" +
            "Start time: " + sdf.format(new Date(startTime)) + "ms\n" +
            "Elapsed time: " + (System.currentTimeMillis() - startTime) + " ms\n" +
            "End time: " + sdf.format(new Date(System.currentTimeMillis())) + "ms" 
        );
    }
}