# Developed by DeMoD LLC
# Simple Python web server for configuring MediaMTX via a browser form.
# Run with: python3 config.py
# Access at http://localhost:8000 (change HOST to '0.0.0.0' for network access, but secure it).
# Generates mediamtx.yml and can start/restart the server.

from utils import run_command, security_checks, calculate_rating, load_jsonc, write_yml
import http.server
import socketserver
import urllib.parse
import subprocess
import os
import signal
import sys
import json

PORT = 8000
HOST = '127.0.0.1'  # Localhost for security; change to '0.0.0.0' if needed
MEDIAMTX_PROC = None  # Global to track running process

def load_jsonc_from_text(text):
    no_comments = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.DOTALL)
    return json.loads(no_comments)

class ConfigHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        checks = security_checks()
        security_status = "<ul>" + "".join(f"<li>{k.capitalize()}: {'Yes' if v else 'No'}</li>" for k, v in checks.items()) + "</ul>"
        html = f"""
<!DOCTYPE html>
<html>
<head>
  <title>DeMoD Camera Config</title>
  <link rel="icon" href="https://demod.ltd/favicon.ico" type="image/x-icon">
  <style>
    a:link, a:visited {{ color: black; text-decoration: none; }}
  </style>
</head>
<body>
<img src="https://upload.wikimedia.org/wikipedia/commons/thumb/a/ad/Sierpinski-Trigon-7.svg/800px-Sierpinski-Trigon-7.svg.png" alt="DeMoD Branding" style="display: block; margin: 0 auto;">
<a href="https://demod.ltd" style="font-family: 'Courier New', Courier, monospace; display: block; text-align: center;">DeMoD LLC</a>
<h1>DeMoD Camera Configuration</h1>
<h2>Security Status</h2>
{security_status}
<p>Review and adjust below. For multi-cam, paste JSONC content.</p>
<form method="POST">
  <label>JSONC Config (optional for multi-cam):</label><br>
  <textarea name="jsonc" rows="10" cols="50"></textarea><br><br>
  <h3>Manual Single Cam (if no JSONC)</h3>
  <label>Webcam Device:</label><br>
  <input type="text" name="device" value="/dev/video0"><br><br>
  <label>Enable Auth:</label><br>
  <input type="checkbox" name="enable_auth"><br><br>
  <label>RTSP Username:</label><br>
  <input type="text" name="rtsp_user"><br><br>
  <label>RTSP Password (or env:VAR_NAME):</label><br>
  <input type="password" name="rtsp_pass"><br><br>
  <label>Framerate:</label><br>
  <input type="number" name="framerate" value="30" min="1"><br><br>
  <label>Bitrate:</label><br>
  <input type="text" name="bitrate" value="800k"><br><br>
  <input type="checkbox" name="start_server" checked> Start/Restart Server<br><br>
  <input type="submit" value="Apply">
</form>
</body>
</html>
"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode()
        params = urllib.parse.parse_qs(post_data)

        try:
            cams = []
            jsonc_text = params.get('jsonc', [''])[0].strip()
            if jsonc_text:
                config = load_jsonc_from_text(jsonc_text)
                cams = config.get('cams', [])
            if not cams:
                # Single from form
                device = params.get('device', ['/dev/video0'])[0].strip()
                if not device:
                    raise ValueError("Device cannot be empty.")
                framerate = params.get('framerate', ['30'])[0].strip()
                if not framerate.isdigit():
                    raise ValueError("Framerate must be a number.")
                bitrate = params.get('bitrate', ['800k'])[0].strip()
                if not bitrate:
                    raise ValueError("Bitrate cannot be empty.")
                enable_auth = 'enable_auth' in params
                auth = {}
                if enable_auth:
                    auth['user'] = params.get('rtsp_user', [''])[0].strip()
                    if not auth['user']:
                        raise ValueError("Username required if auth enabled.")
                    auth['pass'] = params.get('rtsp_pass', [''])[0].strip()
                    if not auth['pass']:
                        raise ValueError("Password required if auth enabled.")
                cams = [{'device': device, 'framerate': framerate, 'bitrate': bitrate, 'auth': auth}]

            write_yml(cams)

            response = f"Configuration saved for {len(cams)} cam(s).<br>"
            ip = run_command("hostname -I | awk '{print $1}'")
            stream_urls = [f"rtsp://{cam.get('auth', {}).get('user', '')}:<password>@{ip}:8554/cam{i}" if cam.get('auth', {}).get('user') else f"rtsp://{ip}:8554/cam{i}" for i, cam in enumerate(cams)]
            response += "Streams at: " + ", ".join(stream_urls) + "<br>"

            if 'start_server' in params:
                global MEDIAMTX_PROC
                if MEDIAMTX_PROC and MEDIAMTX_PROC.poll() is None:
                    os.kill(MEDIAMTX_PROC.pid, signal.SIGTERM)
                    MEDIAMTX_PROC.wait()
                    response += "Old server stopped.<br>"
                
                MEDIAMTX_PROC = subprocess.Popen(['./mediamtx'])
                response += "Server started.<br>"

            # Updated status
            checks = security_checks()
            security_status = "<ul>" + "".join(f"<li>{k.capitalize()}: {'Yes' if v else 'No'}</li>" for k, v in checks.items()) + "</ul>"
            response += "<h2>Updated Security Status</h2>" + security_status

            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(response.encode())
        except Exception as e:
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"Error: {str(e)}".encode())

if __name__ == "__main__":
    try:
        with socketserver.TCPServer((HOST, PORT), ConfigHandler) as httpd:
            print(f"Serving at http://{HOST}:{PORT}")
            print("Developed by DeMoD LLC")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down...")
        if MEDIAMTX_PROC and MEDIAMTX_PROC.poll() is None:
            MEDIAMTX_PROC.terminate()
            MEDIAMTX_PROC.wait()
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
