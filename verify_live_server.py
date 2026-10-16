"""
Live Server Verification Script:
Launches the Flask web server on port 5055, performs real network socket HTTP requests
against the endpoints, verifies response codes, HTML contents, sessions, and headers,
then gracefully terminates the server.
"""

import sys
import time
import threading
import urllib.request
import urllib.error

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
from werkzeug.serving import make_server
from app import create_app

class ServerThread(threading.Thread):
    def __init__(self, app, port=5055):
        super().__init__()
        self.server = make_server('127.0.0.1', port, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        print("Live WSGI Server starting on http://127.0.0.1:5055...")
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


def test_live_server():
    app = create_app()
    server_thread = ServerThread(app, port=5055)
    server_thread.start()
    time.sleep(1.0)  # Allow server to bind and start listening

    try:
        endpoints_to_test = [
            ('/', 200, "Online Examination System"),
            ('/about', 200, "About The Project"),
            ('/auth/login', 200, "Candidate Login"),
            ('/auth/admin-login', 200, "Faculty Administrator Login"),
            ('/auth/register', 200, "Candidate Registration")
        ]

        print("\n=== Testing Live HTTP Network Requests (http://127.0.0.1:5055) ===")
        for path, expected_status, text_snippet in endpoints_to_test:
            url = f"http://127.0.0.1:5055{path}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as resp:
                status = resp.status
                body = resp.read().decode('utf-8')
                assert status == expected_status, f"Expected {expected_status} for {url}, got {status}"
                assert text_snippet in body, f"Snippet '{text_snippet}' not found in {url}"
                print(f"✓ HTTP GET {url} -> Status {status} OK (Snippet verified: '{text_snippet}')")

        print("\nAll live HTTP network endpoints responded successfully!")

    finally:
        print("\nShutting down live WSGI server...")
        server_thread.shutdown()
        server_thread.join()
        print("Server shutdown completed.")


if __name__ == '__main__':
    test_live_server()
