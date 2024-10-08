package com.example.service;

import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

import javax.servlet.ServletException;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.BufferedReader;

@WebServlet("/service/compose")
public class ComposeServicesServlet extends HttpServlet {
    private static final long serialVersionUID = 1L;

    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
        String paramN1 = request.getParameter("n1");
        String paramN2 = request.getParameter("n2");

        if (paramN1 == null || paramN1.isEmpty() || paramN2 == null || paramN2.isEmpty()) {
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("Parameters 'n1' and 'n2' are required");
            return;
        }

        try {
            // First service.
            String response1 = sendGetRequest("http://192.168.0.12:8081/service/sum?n=" + paramN1);

            // Second service.
            String response2 = sendGetRequest("http://192.168.0.12:8082/service/sum?n=" + paramN2);

            /// Set response.
            System.out.println(response1);
            response.setContentType("text/plain");
            response.getWriter().write("Composed Services:" +
                "\n\t- Service 1:\n\t\t" + response1 +
                "\n\t- Service 2:\n\t\t" + response2
            );

        } catch (Exception e) {
            response.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
            response.getWriter().write("Error composing services: " + e.getMessage());
        }
    }

    private String sendGetRequest(String urlString) throws IOException {
        URL url = new URL(urlString);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("GET");

        try (BufferedReader in = new BufferedReader(new InputStreamReader(conn.getInputStream()))) {
            String inputLine;
            StringBuilder content = new StringBuilder();
            while ((inputLine = in.readLine()) != null) {
                content.append(inputLine).append("\n\t\t");
            }
            return content.toString().substring(0, content.length() - 1);
        } finally {
            conn.disconnect();
        }
    }
}
