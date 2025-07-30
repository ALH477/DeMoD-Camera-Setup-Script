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
Shared utilities for DeMoD Camera Setup, including security checks, JSONC parsing,
and MediaMTX configuration file generation.
"""

import os
import subprocess
import grp
import re
import json

def run_command(cmd: str) -> str:
    """
    Execute a shell command and return its output.

    Args:
        cmd: The command to execute.

    Returns:
        The command output as a string, or an error message if execution fails.
    """
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode().strip()
    except Exception as e:
        return f"Error executing '{cmd}': {str(e)}"

def parse_yml_auth(yml_path: str = 'mediamtx.yml') -> bool:
    """
    Check if authentication is enabled in the MediaMTX YML config.

    Args:
        yml_path: Path to the MediaMTX YML file.

    Returns:
        True if auth is enabled, False otherwise.
    """
    if os.path.exists(yml_path):
        with open(yml_path, 'r') as f:
            content = f.read()
            return 'readUser:' in content and 'readPass:' in content
    return False

def get_devices() -> list:
    """
    Detect available video devices using v4l2-ctl.

    Returns:
        A list of video device paths (e.g., ['/dev/video0']), or ['/dev/video0'] if none found.
    """
    try:
        output = run_command("v4l2-ctl --list-devices")
        devices = [line.strip() for line in output.splitlines() if line.strip().startswith('/dev/video')]
        return devices if devices else ['/dev/video0']
    except:
        return ['/dev/video0']

def security_checks() -> dict:
    """
    Perform security checks for the system configuration.

    Returns:
        A dictionary with check results (root, video_group, ufw_port, auth_enabled).
    """
    checks = {}
    checks['root'] = os.getuid() != 0
    try:
        video_group = grp.getgrnam('video').gr_mem
        checks['video_group'] = os.getlogin() in video_group
    except KeyError:
        checks['video_group'] = False
    checks['ufw_port'] = '8554' in run_command("sudo ufw status")
    checks['auth_enabled'] = parse_yml_auth()
    return checks

def calculate_rating(checks: dict, user_answers: list) -> int:
    """
    Calculate a security rating based on checks and user answers.

    Args:
        checks: Dictionary of security check results.
        user_answers: List of 1 (yes) or 0 (no) for security questions.

    Returns:
        A score from 0 to 100.
    """
    score = sum(25 for v in checks.values() if v)
    answer_points = sum(user_answers) * (100 // (len(user_answers) or 1))
    if score < 50:  # Recursive-like penalty for low base score
        answer_points = sum(user_answers) * (50 // (len(user_answers) or 1))
    return min(score + answer_points, 100)

def load_jsonc(source: str, is_file: bool = True) -> dict:
    """
    Parse a JSONC file or string, removing comments.

    Args:
        source: File path or JSONC string.
        is_file: True if source is a file path, False if it's a string.

    Returns:
        Parsed JSON dictionary.

    Raises:
        json.JSONDecodeError: If JSONC is invalid.
    """
    try:
        if is_file:
            with open(source) as f:
                text = f.read()
        else:
            text = source
        no_comments = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.DOTALL)
        return json.loads(no_comments)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSONC format: {str(e)}. Ensure proper syntax (e.g., valid JSON with // or /* */ comments).")
    except FileNotFoundError:
        raise ValueError(f"JSONC file '{source}' not found. Provide a valid file path.")

def get_auth_config(auth: dict) -> str:
    """
    Generate MediaMTX auth configuration from a dictionary.

    Args:
        auth: Dictionary with 'user' and 'pass' (plain or 'env:VAR_NAME').

    Returns:
        YML-formatted auth string, or empty string if no auth.

    Raises:
        ValueError: If env var is missing or invalid.
    """
    user = auth.get('user', '')
    pass_ = auth.get('pass', '')
    if pass_.startswith('env:'):
        var = pass_[4:]
        pass_ = os.environ.get(var)
        if not pass_:
            raise ValueError(f"Environment variable '{var}' not set. Set it (e.g., 'export {var}=secret') or use plain text.")
    if user and pass_:
        return f"    readUser: {user}\n    readPass: {pass_}\n"
    return ''

def write_yml(cams: list) -> None:
    """
    Generate and write MediaMTX YML configuration for multiple cameras.

    Args:
        cams: List of dictionaries with device, framerate, bitrate, and auth.

    Raises:
        ValueError: If device path is invalid or parameters are malformed.
    """
    paths = ''
    for i, cam in enumerate(cams):
        device = cam.get('device', f'/dev/video{i}')
        if not os.path.exists(device):
            raise ValueError(f"Device '{device}' does not exist. Check with 'ls /dev/video*'. ")
        framerate = cam.get('framerate', '30')
        if not str(framerate).isdigit():
            raise ValueError(f"Framerate '{framerate}' for cam{i} must be a number.")
        bitrate = cam.get('bitrate', '800k')
        if not bitrate:
            raise ValueError(f"Bitrate for cam{i} cannot be empty.")
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
