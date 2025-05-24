package com.example.service;

import io.opentelemetry.instrumentation.annotations.WithSpan;

import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Random;

import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

@WebServlet("/service/alternative")
public class AlternativeServiceServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;
    private Random random = new Random();
    private DummyServiceRepository dsr = new DummyServiceRepository();

    @Override
    @WithSpan
    protected void doGet(HttpServletRequest request, HttpServletResponse response) throws IOException {
        String probability = request.getParameter("p");
        String endpoint1 = request.getParameter("e1");
        String endpoint2 = request.getParameter("e2");
        String service1 = request.getParameter("s1");
        String service2 = request.getParameter("s2");
        String paramN1 = request.getParameter("n1");
        String paramN2 = request.getParameter("n2");
        String argument1 = request.getParameter("a1");
        String argument2 = request.getParameter("a2");

        if(probability == null || probability.isEmpty()){
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Parameters 'probability' is required");
            return;
        }

        if(endpoint1 == null || endpoint1.isEmpty()){
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Parameters 'endpoint1' is required");
            return;
        }

        if(endpoint2 == null || endpoint2.isEmpty()){
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Parameters 'endpoint2' is required");
            return;
        }

        if(service1 == null || service1.isEmpty()){
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Parameters 'service1' is required");
            return;
        }

        if(argument1 == null || argument1.isEmpty()){
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Parameters 'argument1' is required");
            return;
        }

        if(paramN1 == null || paramN1.isEmpty()){
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Parameters 'paramN1' is required");
            return;
        }

        if(service2 == null || service2.isEmpty()){
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Parameters 'service2' is required");
            return;
        }

        if(argument2 == null || argument2.isEmpty()){
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Parameters 'argument2' is required");
            return;
        }

        if(paramN2 == null || paramN2.isEmpty()) {
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Parameters 'paramN2' is required");
            return;
        }

        try {
            response.setContentType("text/plain");
            response.getWriter().write(dsr.doAlternative(Float.parseFloat(probability), endpoint1, service1, argument1, paramN1, endpoint2, service2, argument2, paramN2));
        } catch (Exception e) {
            response.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
            response.getWriter().write("Error composing services: " + e.getMessage());
        }
    }
}