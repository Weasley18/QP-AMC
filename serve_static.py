import http.server
import socketserver

PORT = 8080
Handler = http.server.SimpleHTTPRequestHandler

print(f"Serving at http://localhost:{PORT}")
print("Access the user creation form at: http://localhost:8080/user_creation.html")

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    httpd.serve_forever() 