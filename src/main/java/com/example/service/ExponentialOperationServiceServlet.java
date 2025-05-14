package com.example.service;

import io.opentelemetry.instrumentation.annotations.WithSpan;

import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;

import static java.lang.Math.*;

@WebServlet("/service/exponentialop")
public class ExponentialOperationServiceServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;
    private DummyServiceRepository dsr = new DummyServiceRepository();

    @WithSpan
    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response) throws IOException {
        String maxParameter = request.getParameter("max");
        if (maxParameter == null || maxParameter.isEmpty()) {
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Parameter 'max' is required");
            return;
        }

        int max = Integer.parseInt(maxParameter);
        if (max <= 0) {
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Invalid exponential distribution parameter");
            return;
        }

        response.setContentType("text/plain");
        response.getWriter().write(
            dsr.doExponentialOperation(max)
        );
    }
}