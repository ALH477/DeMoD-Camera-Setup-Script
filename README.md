# DeMoD Camera Setup Script

Developed by DeMoD LLC

This project turns your Orange Pi Zero 2W into an IP camera by streaming a USB webcam feed over RTSP using FFMPEG and MediaMTX. It's designed for integration with NVR systems. The scripts include interactive prompts, security features (checksums, auth), a web-based configuration interface, and now a TUI security checker.

## Features
- Automatic The user wants:

1. Make the setup script ask to run the security checker at the end.

2. Add a rating system into the TUI and HTML that checks the config then asks a few yes no questions.

First, update setup.sh: At the end, after "Setup complete...", add a prompt: read -p "Run the security checker now? (y/n): " answer; if y, then python3 security_checker.py

For the TUI (security_checker.py) and HTML (config.py):

Add a "rating system" that checks the config (probably mediamtx.yml and system settings), then asks a few yes/no questions.

The rating could be a security score based on checks (e.g., non-root, video group, UFW open, auth enabled). Say 25 points each, total 100.

After displaying status, show score, then ask yes/no questions like: "Is the device on a secure network? (y/n)", "Do you have physical access control? (y/n)", etc. Use answers to adjust or note in rating.

For TUI: After final status, calculate score, ask 2-3 yes/no, then give final rating.

For HTML: In the security status section, add a score. On POST, include questions in response? But since it's a form, perhaps add yes/no checkboxes in the form for additional security questions, then in response, factor them into a rating.

The request says "checks the config then asks a few yes no questions." So for HTML, add fields to the form.

Choose questions: e.g., "Is the Orange Pi behind a firewall/VPN? (y/n)", "Have you changed default passwords? (y/n)", "Is remote access restricted? (y/n)"

Based on answers and checks, compute rating (e.g., base score from automated checks + points from yes answers).

Update README if needed, but probably minor.

No tools needed, as this is code refinement.

Output the updated scripts.```bash
#!/bin/bash

# Developed by DeMoD LLC
# This script installs dependencies, downloads the latest MediaMTX (arm64) with checksum verification, extracts it, and configures UFW.
# Now with interactive prompts for confirmation, security measures, and error handling.
# Run as sudo if needed for apt and UFW.

set -e  # Exit on any error
trap 'echo "Error occurred. Cleaning up..."; rm -f mediamtx.tar.gz checksums.sha256; exit 1' ERR INT TERM

# Check if running as root (not recommended for security)
if [ "$EUID" -eq 0 ]; then
  echo "Warning: Running as root. For better security, run as a non-root user and use sudo only when prompted."
fi

echo "Welcome to the MediaMTX setup script for Orange Pi webcam streaming."
echo "Developed by DeMoD LLC"
echo "This will update packages, install v4l-utils/wget/tar/python3 if needed, download MediaMTX v1.13.1 with checksum verification, and open UFW port 8554."
read -p "Proceed with package update and installation? (y/n): " answer
answer=${answer,,}  # Convert to lowercase for validation
if [ "$answer" != "y" ]; then
  echo "Setup aborted."
  exit 0
fi

sudo apt update || { echo "apt update failed."; exit 1; }
sudo apt install -y v4l-utils wget tar python3 python3-venv || { echo "Package installation failed."; exit 1; }

# Ensure user has access to video devices (for /dev/videoX)
echo "For webcam access, ensure your user is in the 'video' group."
read -p "Add current user to 'video' group? (Requires logout/reboot; y/n): " answer
answer=${answer,,}
if [ "$answer" = "y" ]; then
  sudo groupadd -f video || { echo "groupadd failed."; exit 1; }
  sudo usermod -aG video "$USER" || { echo "usermod failed."; exit 1; }
  echo "User added to 'video' group. Please log out and back in for changes to take effect."
fi

read -p "Proceed to download and extract MediaMTX with security verification? (y/n): " answer
answer=${answer,,}
if [ "$answer" != "y" ]; then
  echo "Setup aborted."
  exit 0
fi

# Latest version as of July 29, 2025
VERSION="1.13.1"
FILE="mediamtx_v${VERSION}_linux_arm64.tar.gz"
URL="https://github.com/bluenviron/mediamtx/releases/download/v${VERSION}/${FILE}"
CHECKSUM_URL="https://github.com/bluenviron/mediamtx/releases/download/v${VERSION}/checksums.sha256"

wget "$URL" -O "$FILE" || { echo "Download failed."; rm -f "$FILE"; exit 1; }
wget "$CHECKSUM_URL" -O checksums.sha256 || { echo "Checksum download failed."; rm -f "$FILE" checksums.sha256; exit 1; }

# Verify checksum for security
echo "Verifying download integrity with SHA256 checksum..."
grep "$FILE" checksums.sha256 | sha256sum --check - || { echo "Checksum verification failed! Download may be corrupted or tampered. Aborting."; rm -f "$FILE" checksums.sha256; exit 1; }
echo "Checksum verified successfully."

tar -xzf "$FILE" mediamtx mediamtx.yml || { echo "Extraction failed."; rm -f "$FILE" checksums.sha256; exit 1; }
rm "$FILE" checksums.sha256

read -p "Proceed to open UFW port 8554 for RTSP? (y/n): " answer
answer=${answer,,}
if [ "$answer" != "y" ]; then
  echo "Setup aborted."
  exit 0
fi

# Open RTSP port in UFW (minimal exposure)
sudo ufw allow 8554/tcp || { echo "UFW allow failed."; exit 1; }
sudo ufw reload || { echo "UFW reload failed."; exit 1; }

echo "Setup complete. MediaMTX is ready in the current directory. Run start.sh for CLI, python3 config.py for web, or python3 security_checker.py for TUI security config."

read -p "Run the security checker now? (y/n): " answer
answer=${answer,,}
if [ "$answer" = "y" ]; then
  python3 security_checker.py
fi
