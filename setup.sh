#!/bin/bash

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

# Developed by DeMoD LLC
# Installs dependencies, downloads MediaMTX for the specified architecture, and configures firewall.
# Supports multiple OSes (Debian-like with apt/ufw, Fedora-like with dnf/firewalld) and architectures (ARM 32/64-bit, RISC-V, x86-64).
# Run with sudo if needed for package installation and firewall configuration.

set -e  # Exit on any error
trap 'echo "Error occurred. Cleaning up..."; rm -f mediamtx.tar.gz checksums.sha256; exit 1' ERR INT TERM

# Check if running as root
if [ "$EUID" -eq 0 ]; then
  echo "Warning: Running as root. For better security, run as a non-root user with sudo."
fi

echo "Welcome to the DeMoD Camera Setup Script for webcam streaming."
echo "Developed by DeMoD LLC"
echo "This script updates packages, installs dependencies, downloads MediaMTX v1.13.1, and configures firewall."

# Prompt for OS type
echo "Select your OS type:"
echo "1) Debian-like (e.g., Ubuntu, Armbian, Raspberry Pi OS) - uses apt and ufw"
echo "2) Fedora-like (e.g., Fedora, RHEL) - uses dnf and firewalld"
read -p "Enter choice (1-2): " os_choice
case $os_choice in
  1) PKG_MANAGER="apt" ; UPDATE_CMD="sudo apt update" ; INSTALL_CMD="sudo apt install -y" ; FIREWALL="ufw" ;;
  2) PKG_MANAGER="dnf" ; UPDATE_CMD="sudo dnf check-update" ; INSTALL_CMD="sudo dnf install -y" ; FIREWALL="firewalld" ;;
  *) echo "Invalid choice. Defaulting to Debian-like."; PKG_MANAGER="apt" ; UPDATE_CMD="sudo apt update" ; INSTALL_CMD="sudo apt install -y" ; FIREWALL="ufw" ;;
esac

# Prompt for architecture
echo "Select your SBC architecture:"
echo "1) ARM 64-bit (e.g., Orange Pi Zero 2W, Raspberry Pi 4)"
echo "2) ARM 32-bit (e.g., Raspberry Pi Zero)"
echo "3) RISC-V (e.g., StarFive VisionFive)"
echo "4) x86-64 (e.g., Intel NUC)"
read -p "Enter choice (1-4): " arch_choice
case $arch_choice in
  1) ARCH="arm64" ;;
  2) ARCH="armv7" ;;
  3) ARCH="riscv64" ;;
  4) ARCH="amd64" ;;
  *) echo "Invalid choice. Defaulting to ARM 64-bit."; ARCH="arm64" ;;
esac

read -p "Proceed with package update and installation? (y/n): " answer
answer=${answer,,}
if [ "$answer" != "y" ]; then
  echo "Setup aborted."
  exit 0
fi

# Update and install dependencies
echo "Updating package list and installing dependencies..."
$UPDATE_CMD || { echo "Error: Failed to update package list. Check network or package manager configuration."; exit 1; }
$INSTALL_CMD v4l-utils wget tar python3 python3-venv || { echo "Error: Failed to install dependencies. Ensure package manager is configured correctly."; exit 1; }

# Ensure user has access to video devices
echo "Ensuring user has webcam access via 'video' group."
read -p "Add current user to 'video' group? (Requires logout/reboot; y/n): " answer
answer=${answer,,}
if [ "$answer" = "y" ]; then
  sudo groupadd -f video || { echo "Error: Failed to create video group."; exit 1; }
  sudo usermod -aG video "$USER" || { echo "Error: Failed to add user to video group."; exit 1; }
  echo "User added to 'video' group. Log out and back in for changes to take effect."
fi

read -p "Proceed to download and extract MediaMTX v1.13.1 for $ARCH? (y/n): " answer
answer=${answer,,}
if [ "$answer" != "y" ]; then
  echo "Setup aborted."
  exit 0
fi

# Download MediaMTX
VERSION="1.13.1"
FILE="mediamtx_v${VERSION}_linux_${ARCH}.tar.gz"
URL="https://github.com/bluenviron/mediamtx/releases/download/v${VERSION}/${FILE}"
CHECKSUM_URL="https://github.com/bluenviron/mediamtx/releases/download/v${VERSION}/checksums.sha256"

echo "Downloading MediaMTX v${VERSION} for $ARCH..."
wget "$URL" -O "$FILE" || { echo "Error: Download failed. Check network or URL: $URL"; rm -f "$FILE"; exit 1; }
wget "$CHECKSUM_URL" -O checksums.sha256 || { echo "Error: Checksum download failed. Check network or URL: $CHECKSUM_URL"; rm -f "$FILE" checksums.sha256; exit 1; }

# Verify checksum
echo "Verifying download integrity with SHA256 checksum..."
grep "$FILE" checksums.sha256 | sha256sum --check - || { echo "Error: Checksum verification failed! Download may be corrupted or tampered. Aborting."; rm -f "$FILE" checksums.sha256; exit 1; }
echo "Checksum verified successfully."

# Extract files
tar -xzf "$FILE" mediamtx mediamtx.yml || { echo "Error: Extraction failed. Check tar file integrity."; rm -f "$FILE" checksums.sha256; exit 1; }
rm "$FILE" checksums.sha256

read -p "Proceed to configure firewall port 8554 for RTSP? (y/n): " answer
answer=${answer,,}
if [ "$answer" != "y" ]; then
  echo "Setup aborted."
  exit 0
fi

# Configure firewall based on OS type
if [ "$FIREWALL" = "ufw" ]; then
  echo "Configuring UFW to allow RTSP port 8554..."
  sudo ufw allow 8554/tcp || { echo "Error: Failed to allow port 8554. Check UFW configuration."; exit 1; }
  sudo ufw reload || { echo "Error: Failed to reload UFW. Check UFW status."; exit 1; }
elif [ "$FIREWALL" = "firewalld" ]; then
  echo "Configuring firewalld to allow RTSP port 8554..."
  sudo firewall-cmd --permanent --add-port=8554/tcp || { echo "Error: Failed to add port 8554. Check firewalld configuration."; exit 1; }
  sudo firewall-cmd --reload || { echo "Error: Failed to reload firewalld. Check firewalld status."; exit 1; }
fi

echo "Setup complete. MediaMTX is ready in the current directory."
echo "Run './start.sh' for CLI setup, 'python3 config.py' for web configuration, or 'python3 security_checker.py' for TUI security checks."
echo "For large-scale multi-camera setups, prepare a 'config.jsonc' file."

read -p "Run the security checker now? (y/n): " run_checker
run_checker=${run_checker,,}
if [ "$run_checker" = "y" ]; then
  python3 security_checker.py
fi
