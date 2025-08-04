# Copyright (C) 2025 DeMoD LLC
# This file is part of DeMoD Camera Setup.
#
# DeMoD Camera Setup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# DeMoD Camera Setup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with DeMoD Camera Setup.  If not, see <https://www.gnu.org/licenses/>.

"""
Web-based configuration server for MediaMTX, providing a browser interface
to configure single or multi-camera setups via JSONC or form inputs.
"""

from utils import run_command, security_checks, calculate_rating, load_jsonc, write_yml
import http.server
import socketserver
import urllib.parse
import subprocess
import os
import signal
import sys

PORT = 8000
HOST = '127.0.0.1'  # Localhost for security; change to '0.0.0.0' for network access
MEDIAMTX_PROC = None  # Global to track running MediaMTX process

class ConfigHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler for serving and processing the configuration form."""
    def do_GET(self):
        checks = security_checks()
        user_answers = []  # Default for initial load
        rating = calculate_rating(checks, user_answers)
        rating_message = f"Security Rating: {rating}/100"
        if rating < 50:
            rating_message += " (Low - improve settings below)"
        elif rating < 80:
            rating_message += " (Moderate - consider additional measures)"
        else:
            rating_message += " (High - well secured)"
        security_status = "<ul>" + "".join(f"<li>{k.capitalize()}: {'Yes' if v else 'No'}</li>" for k, v in checks.items()) + "</ul>"
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>DeMoD Camera Config</title>
  <link rel="icon" href="https://demod.ltd/favicon.ico" type="image/x-icon">
  <style>
    body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
    a:link, a:visited {{ color: black; text-decoration: none; }}
    h1, h2, h3 {{ margin: 10px 0; }}
    label {{ display: block; margin: 5px 0; }}
    input, textarea {{ width: 100%; padding: 5px; margin-bottom: 10px; }}
    input[type="checkbox"] {{ width: auto; }}
    ul {{ list-style-type: disc; margin-left: 20px; }}
  </style>
</head>
<body>
  <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/a/ad/Sierpinski-Trigon-7.svg/800px-Sierpinski-Trigon-7.svg.png" alt="DeMoD Branding" style="display: block; margin: 0 auto; max-width: 200px;">
  <a href="https://demod.ltd" style="font-family: 'Courier New', Courier, monospace; display: block; text-align: center;">DeMoD LLC</a>
  <h1>DeMoD Camera Configuration</h1>
  <h2>Security Status</h2>
  <p>{rating_message}</p>
  {security_status}
  <p>Configure cameras below. Use JSONC for multi-camera setups or form fields for a single camera. Answer security questions to improve the rating.</p>
  <form method="POST">
    <h3>Multi-Camera Configuration</h3>
    <label>JSONC Config (optional for multi-camera):</label>
    <textarea name="jsonc" rows="10" cols="50" placeholder='{{ "cams": [{ "device": "/dev/video0", "framerate": 30, "bitrate": "800k", "auth": {{ "user": "user1", "pass": "env:RTSP_PASS" }} }] }}'></textarea>
    <h3>Manual Single Camera (if no JSONC)</h3>
    <label>Webcam Device (e.g., /dev/video0):</label>
    <input type="text" name="device" value="/dev/video0">
    <label>Enable Authentication:</label>
    <input type="checkbox" name="enable_auth">
    <label>RTSP Username:</label>
    <input type="text" name="rtsp_user">
    <label>RTSP Password (or env:VAR_NAME):</label>
    <input type="password" name="rtsp_pass">
    <label>Framerate (e.g., 30):</label>
    <input type="number" name="framerate" value="30" min="1">
    <label>Bitrate (e.g., 800k):</label>
    <input type="text" name="bitrate" value="800k">
    <h3>Security Questions (check for yes)</h3>
    <label>Is the device on a secure network (e.g., behind VPN/firewall)?</label>
    <input type="checkbox" name="secure_network"> Yes
    <label>Have you changed default system passwords?</label>
    <input type="checkbox" name="changed_passwords"> Yes
    <label>Is remote access restricted (e.g., SSH keys only)?</label>
    <input type="checkbox" name="restricted_access"> Yes
    <label>Start/Restart Server:</label>
    <input type="checkbox" name="start_server" checked>
    <input type="submit" value="Apply Configuration" style="margin-top: 10px;">
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
                config = load_jsonc(jsonc_text, is_file=False)
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
            ip = run_command("hostname -I | awk '{{print $1}}'")
            stream_urls = [f"rtsp://{cam.get('auth', {{}}).get('user', '')}:<password>@{ip}:8554/cam{i}" if cam.get('auth', {}).get('user') else f"rtsp://{ip}:8554/cam{i}" for i, cam in enumerate(cams)]
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
            user_answers = [
                1 if 'secure_network' in params else 0,
                1 if 'changed_passwords' in params else 0,
                1 if 'restricted_access' in params else 0
            ]
            rating = calculate_rating(checks, user_answers)
            rating_message = f"Security Rating: {rating}/100"
            if rating < 50:
                rating_message += " (Low - improve settings)"
            elif rating < 80:
                rating_message += " (Moderate - consider additional measures)"
            else:
                rating_message += " (High - good job)"
            security_status = "<ul>" + "".join(f"<li>{k.capitalize()}: {'Yes' if v else 'No'}</li>" for k, v in checks.items()) + "</ul>"
            response += f"<h2>Updated Security Status</h2><p>{rating_message}</p>{security_status}"

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
            print(f"Serving configuration webserver at http://{HOST}:{PORT}")
            print("Developed by DeMoD LLC")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down server...")
        if MEDIAMTX_PROC and MEDIAMTX_PROC.poll() is None:
            MEDIAMTX_PROC.terminate()
            MEDIAMTX_PROC.wait()
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)
