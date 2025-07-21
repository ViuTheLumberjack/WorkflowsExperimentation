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

@WebServlet("/service/uniform")
public class UniformServiceServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;
    private Random random = new Random();
    private DummyServiceRepository dsr = new DummyServiceRepository();

    @WithSpan
    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response) throws IOException {
        String paramEFT = request.getParameter("EFT");
        if (paramEFT == null || paramEFT.isEmpty()) {
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Parameter 'EFT' is required");
            return;
        }

        String paramLFT = request.getParameter("LFT");
        if (paramLFT == null || paramLFT.isEmpty()) {
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Parameter 'LFT' is required");
            return;
        }

        double EFT = Double.parseDouble(paramEFT);
        double LFT = Double.parseDouble(paramLFT);
        if (EFT < 0 || LFT < 0 || EFT >= LFT) {
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Invalid uniform distribution parameters");
            return;
        }

        // Return the result.
        response.setContentType("text/plain");
        response.getWriter().write(
                dsr.doUniformOperation(EFT, LFT));
    }
}