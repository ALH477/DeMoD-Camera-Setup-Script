# Developed by DeMoD LLC
# TUI-based security checker and config adjuster for MediaMTX.
# Run with: python3 security_checker.py
# Walks through checks and allows updates to mediamtx.yml.

from utils import run_command, get_devices, security_checks, calculate_rating, load_jsonc, write_yml
import subprocess
import sys

def display_checks(checks):
    print("\nSecurity Status:")
    print(f"- Running as non-root: {'Yes' if checks['root'] else 'No (Warning: Run as non-root for security)'}")
    print(f"- User in 'video' group: {'Yes' if checks['video_group'] else 'No (Add user to group for webcam access)'}")
    print(f"- UFW allows port 8554: {'Yes' if checks['ufw_port'] else 'No (Run setup.sh to open)'}")
    print(f"- RTSP auth enabled: {'Yes' if checks['auth_enabled'] else 'No (Recommended to enable)'}\n")

def tui_menu():
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
            run_command("sudo usermod -aG video $USER")
            print("Added. Log out and back in for effect.")

    # Step 2: Firewall
    if not checks['ufw_port']:
        open_port = input("Open UFW port 8554? (y/n): ").lower()
        if open_port == 'y':
            run_command("sudo ufw allow 8554/tcp && sudo ufw reload")
            print("Port opened.")

    # Step 3: Load JSONC for large-scale or manual
    use_jsonc = input("Use JSONC config file for multi-cam setup? (y/n): ").lower()
    if use_jsonc == 'y':
        filename = input("Enter JSONC file path (default config.jsonc): ") or 'config.jsonc'
        config = load_jsonc(filename)
        cams = config['cams']
    else:
        # Manual single cam
        devices = get_devices()
        print("Available devices:", ', '.join(devices))
        device = input(f"Enter webcam device (default {devices[0]}): ") or devices[0]
        framerate = input("Enter framerate (default 30): ") or '30'
        bitrate = input("Enter bitrate (default 800k): ") or '800k'
        enable_auth = input("Enable RTSP auth? (y/n, recommended): ").lower() == 'y'
        auth = {}
        if enable_auth:
            auth['user'] = input("Enter username: ")
            while not auth['user']:
                auth['user'] = input("Username cannot be empty: ")
            auth['pass'] = input("Enter password or env:VAR_NAME: ")
            while not auth['pass']:
                auth['pass'] = input("Password cannot be empty: ")
        cams = [{'device': device, 'framerate': framerate, 'bitrate': bitrate, 'auth': auth}]

    # Write yml
    write_yml(cams)
    print("Configuration updated in mediamtx.yml.")

    # Step 4: Start Server
    start = input("Start MediaMTX server? (y/n): ").lower()
    if start == 'y':
        subprocess.Popen(['./mediamtx'])
        print("Server started. Press Ctrl+C to stop in another terminal.")

    # Final checks
    checks = security_checks()
    print("\nFinal Security Status:")
    display_checks(checks)

    # Rating
    print("\nAnswer for rating:")
    questions = [
        "Is the device on a secure network? (y/n): ",
        "Have you changed default passwords? (y/n): ",
        "Is remote access restricted? (y/n): "
    ]
    user_answers = [1 if input(q).lower() == 'y' else 0 for q in questions]
    rating = calculate_rating(checks, user_answers)
    print(f"Security Rating: {rating}/100")

if __name__ == "__main__":
    tui_menu()
