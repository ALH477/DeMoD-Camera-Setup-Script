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
TUI-based security checker and configuration adjuster for MediaMTX.
Guides users through security checks and camera setup, supporting multi-camera
JSONC configs or manual single-camera input.
"""

from utils import run_command, get_devices, security_checks, calculate_rating, load_jsonc, write_yml
import subprocess
import sys

def display_checks(checks: dict) -> None:
    """
    Display security check results in a formatted manner.

    Args:
        checks: Dictionary of security check results.
    """
    print("\nSecurity Status:")
    print(f"- Running as non-root: {'Yes' if checks['root'] else 'No (Warning: Run as non-root for security)'}")
    print(f"- User in 'video' group: {'Yes' if checks['video_group'] else 'No (Add user to group for webcam access)'}")
    print(f"- UFW allows port 8554: {'Yes' if checks['ufw_port'] else 'No (Run setup.sh to open)'}")
    print(f"- RTSP auth enabled: {'Yes' if checks['auth_enabled'] else 'No (Recommended to enable)'}\n")

def tui_menu() -> None:
    """Main TUI menu for guiding users through security and configuration."""
    print("Welcome to DeMoD Security Checker & Config Adjuster")
    print("Developed by DeMoD LLC\n")
    checks = security_checks()
    display_checks(checks)

    # Step 1: Privileges
    if not checks['root']:
        print("Warning: Running as root. Restart as non-root for better security.")
    if not checks['video_group']:
        add = input("Add current user to 'video' group? (y/n): ").lower()
        if add == 'y':
            result = run_command("sudo usermod -aG video $USER")
            if "Error" in result:
                print(f"Failed to add user to group: {result}")
            else:
                print("Added. Log out and back in for effect.")

    # Step 2: Firewall
    if not checks['ufw_port']:
        open_port = input("Open UFW port 8554 for RTSP? (y/n): ").lower()
        if open_port == 'y':
            result = run_command("sudo ufw allow 8554/tcp && sudo ufw reload")
            if "Error" in result:
                print(f"Failed to configure UFW: {result}")
            else:
                print("Port opened.")

    # Step 3: Load JSONC for large-scale or manual
    cams = []
    use_jsonc = input("Use JSONC config file for multi-camera setup? (y/n): ").lower()
    if use_jsonc == 'y':
        filename = input("Enter JSONC file path (default config.jsonc): ") or 'config.jsonc'
        try:
            config = load_jsonc(filename)
            cams = config.get('cams', [])
            if not cams:
                print("No 'cams' array in JSONC. Falling back to manual configuration.")
        except ValueError as e:
            print(f"Error loading JSONC: {e}. Falling back to manual configuration.")
    if not cams:
        # Manual single camera
        devices = get_devices()
        print("Available devices:", ', '.join(devices))
        device = input(f"Enter webcam device (default {devices[0]}): ") or devices[0]
        framerate = input("Enter framerate (default 30): ") or '30'
        if not framerate.isdigit():
            print("Error: Framerate must be a number. Using default 30.")
            framerate = '30'
        bitrate = input("Enter bitrate (default 800k): ") or '800k'
        if not bitrate:
            print("Error: Bitrate cannot be empty. Using default 800k.")
            bitrate = '800k'
        enable_auth = input("Enable RTSP authentication? (y/n, recommended): ").lower() == 'y'
        auth = {}
        if enable_auth:
            auth['user'] = input("Enter username: ")
            while not auth['user']:
                auth['user'] = input("Username cannot be empty: ")
            auth['pass'] = input("Enter password or env:VAR_NAME: ")
            while not auth['pass']:
                auth['pass'] = input("Password cannot be empty: ")
        cams = [{'device': device, 'framerate': framerate, 'bitrate': bitrate, 'auth': auth}]

    # Write YML
    try:
        write_yml(cams)
        print(f"Configuration updated in mediamtx.yml for {len(cams)} camera(s).")
    except ValueError as e:
        print(f"Error writing configuration: {e}")
        sys.exit(1)

    # Step 4: Start Server
    start = input("Start MediaMTX server? (y/n): ").lower()
    if start == 'y':
        try:
            subprocess.Popen(['./mediamtx'])
            print("Server started. Press Ctrl+C in another terminal to stop.")
        except FileNotFoundError:
            print("Error: MediaMTX binary not found. Ensure setup.sh was run successfully.")
            sys.exit(1)

    # Final checks and rating
    checks = security_checks()
    print("\nFinal Security Status:")
    display_checks(checks)
    print("\nAnswer the following for a security rating:")
    questions = [
        "Is the device on a secure network (e.g., behind VPN/firewall)? (y/n): ",
        "Have you changed default system passwords? (y/n): ",
        "Is remote access restricted (e.g., SSH keys only)? (y/n): "
    ]
    user_answers = [1 if input(q).lower() == 'y' else 0 for q in questions]
    rating = calculate_rating(checks, user_answers)
    rating_message = f"Security Rating: {rating}/100"
    if rating < 50:
        rating_message += " (Low - review and improve settings)"
    elif rating < 80:
        rating_message += " (Moderate - consider additional security measures)"
    else:
        rating_message += " (High - well secured)"
    print(rating_message)

if __name__ == "__main__":
    tui_menu()
