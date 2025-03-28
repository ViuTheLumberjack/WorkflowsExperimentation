package com.example.service;

import java.io.IOException;

import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

@WebServlet("/")
public class HomeServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;

    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response) throws IOException {
        // Return the available services.
        response.setContentType("text/plain");
        response.getWriter().write("Available services:\n" +
                "\t1. Sum service: /service/sum?n=<number>\n" +
                "\t2. Uniform service: /service/uniform?EFT=<number>&LFT=<number>\n" +
                "\t3. Exponential service: /service/exponential?lambda=<number>\n" +
                "\t4. Exponential service: /service/exponentialop?max=<number>\n" +
                "\t5. Erlang service: /service/erlang?lambda=<number>&k=<number>\n" +
                "\t6. Truncated exponential service: /service/truncated-exponential?lambda=<number>&EFT=<number>&LFT=<number>\n" +
                "\t7. Sequential services: /service/sequential?seq=<workflow>\n" +
                "\t8. Alternative services: /service/alternative?seq=<alt>\n");
    }
}
