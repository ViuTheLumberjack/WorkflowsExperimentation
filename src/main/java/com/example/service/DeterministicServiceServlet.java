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

@WebServlet("/service/deterministic")
public class DeterministicServiceServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;
    private DummyServiceRepository dsr = new DummyServiceRepository();

    @WithSpan
    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response) throws IOException {
        String millis = request.getParameter("millis");
        if (millis == null || millis.isEmpty()) {
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Parameter 'millis' is required");
            return;
        }

        double delay = Double.parseDouble(millis);
        if (delay < 0) {
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Invalid 'millis' parameter: Negative delay not allowed");
            return;
        }

        // Return the result.
        response.setContentType("text/plain");
        response.getWriter().write(
                dsr.doDeterministicOperation(delay));
    }
}