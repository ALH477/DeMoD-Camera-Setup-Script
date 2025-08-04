# Developed by DeMoD LLC
# Shared utilities for security checks, config writing, etc.
# Imported by config.py and security_checker.py.

import os
import subprocess
import grp
import re
import json

def run_command(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode().strip()
    except Exception as e:
        return f"Error: {str(e)}"

def parse_yml_auth():
    if os.path.exists('mediamtx.yml'):
        with open('mediamtx.yml', 'r') as f:
            content = f.read()
            if 'readUser:' in content and 'readPass:' in content:
                return True
    return False

def get_devices():
    try:
        output = run_command("v4l2-ctl --list-devices")
        devices = [line.strip() for line in output.splitlines() if line.strip().startswith('/dev/video')]
        return devices if devices else ['/dev/video0']
    except:
        return ['/dev/video0']

def security_checks():
    checks = {}
    checks['root'] = os.getuid() != 0  # Good if not root
    try:
        video_group = grp.getgrnam('video').gr_mem
        checks['video_group'] = os.getlogin() in video_group
    except KeyError:
        checks['video_group'] = False
    checks['ufw_port'] = '8554' in run_command("sudo ufw status")
    checks['auth_enabled'] = parse_yml_auth()
    return checks

def calculate_rating(checks, user_answers):
    score = 0
    if checks['root']: score += 25
    if checks['video_group']: score += 25
    if checks['ufw_port']: score += 25
    if checks['auth_enabled']: score += 25
    # Recursive call example: if low score, halve answers (self-referential adjustment)
    answer_points = sum(user_answers) * (100 // (len(user_answers) or 1))
    if score < 50:
        answer_points = sum(user_answers) * (50 // (len(user_answers) or 1))  # Reduced
    return min(score + answer_points, 100)

def load_jsonc(filename):
    with open(filename) as f:
        text = f.read()
    no_comments = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.DOTALL)
    return json.loads(no_comments)

def get_auth_config(auth):
    user = auth.get('user', '')
    pass_ = auth.get('pass', '')
    if pass_.startswith('env:'):
        var = pass_[4:]
        pass_ = os.environ.get(var)
        if not pass_:
            raise ValueError(f"Env var {var} not set. Set it or provide plain text.")
    if user and pass_:
        return f"    readUser: {user}\n    readPass: {pass_}\n"
    return ''

def write_yml(cams):
    paths = ''
    for i, cam in enumerate(cams):
        device = cam['device']
        framerate = cam['framerate']
        bitrate = cam['bitrate']
        auth_config = get_auth_config(cam.get('auth', {}))
        paths += f"  cam{i}:\n    runOnInit: ffmpeg -f v4l2 -framerate {framerate} -i {device} -c:v libx264 -pix_fmt yuv420p -preset ultrafast -b:v {bitrate} -f rtsp rtsp://localhost:$RTSP_PORT/cam{i}\n    runOnInitRestart: yes\n{auth_config}"
    yml_content = f"""
logLevel: info

# Default RTSP port
rtspAddress: :8554

paths:
{paths}
"""
    with open('mediamtx.yml', 'w') as f:
        f.write(yml_content)
