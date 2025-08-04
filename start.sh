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
# Configures and starts a single-camera MediaMTX stream using a USB webcam.
# Supports interactive device selection and authentication setup.
# Stream available at rtsp://<ip>:8554/cam (add user:pass@ if auth enabled).
# For multi-camera setups, use security_checker.py or config.py.

set -e  # Exit on any error
trap 'echo "Error occurred. Exiting..."; exit 1' ERR INT TERM

# Check if running as root
if [ "$EUID" -eq 0 ]; then
  echo "Warning: Running as root. For better security, run as a non-root user."
fi

echo "Welcome to the DeMoD MediaMTX Start Script for webcam streaming."
echo "Developed by DeMoD LLC"

# Detect video devices
result = run_command("v4l2-ctl --list-devices")
if "Error" in result:
  echo "Error: v4l2-ctl failed. Ensure v4l-utils is installed and webcam is connected."
  exit 1
DEVICES=($(echo "$result" | awk '/usb/{getline; print $1}' | grep '/dev/video'))

if [ ${#DEVICES[@]} -eq 0 ]; then
  echo "No USB webcams detected. Defaulting to /dev/video0 if available."
  DEVICE="/dev/video0"
  read -p "Use default /dev/video0? (y/n): " answer
  answer=${answer,,}
  if [ "$answer" != "y" ]; then
    echo "Start aborted. Please connect a webcam and try again."
    exit 0
  fi
else
  echo "Detected USB webcams:"
  for i in "${!DEVICES[@]}"; do
    echo "$((i+1))) ${DEVICES[$i]}"
  done
  if [ ${#DEVICES[@]} -eq 1 ]; then
    echo "Only one device found: ${DEVICES[0]}"
    read -p "Use this device? (y/n): " answer
    answer=${answer,,}
    if [ "$answer" != "y" ]; then
      echo "Start aborted."
      exit 0
    fi
    DEVICE="${DEVICES[0]}"
  else
    read -p "Select device number (1-${#DEVICES[@]}): " choice
    if [[ ! $choice =~ ^[0-9]+$ ]] || [[ $choice -lt 1 || $choice -gt ${#DEVICES[@]} ]]; then
      echo "Error: Invalid choice. Please select a number between 1 and ${#DEVICES[@]}."
      exit 0
    fi
    DEVICE="${DEVICES[$((choice-1))]}"
  fi
fi

echo "Using device: $DEVICE"

# Validate device exists
if [ ! -e "$DEVICE" ]; then
  echo "Error: Device $DEVICE does not exist. Check with 'ls /dev/video*'."
  exit 1
fi

# Prompt for RTSP authentication
read -p "Enable basic authentication for the RTSP stream? (Recommended; y/n): " enable_auth
enable_auth=${enable_auth,,}
if [ "$enable_auth" = "y" ]; then
  read -p "Enter RTSP username: " rtsp_user
  while [ -z "$rtsp_user" ]; do
    echo "Error: Username cannot be empty."
    read -p "Enter RTSP username: " rtsp_user
  done
  read -s -p "Enter RTSP password: " rtsp_pass
  echo ""
  while [ -z "$rtsp_pass" ]; do
    echo "Error: Password cannot be empty."
    read -s -p "Enter RTSP password: " rtsp_pass
    echo ""
  done
  AUTH_CONFIG="    readUser: $rtsp_user\n    readPass: $rtsp_pass"
  STREAM_URL="rtsp://${rtsp_user}:<password>@$(hostname -I | awk '{print $1}'):8554/cam"
else
  AUTH_CONFIG=""
  echo "Warning: No authentication enabled. Stream is publicly accessible."
  STREAM_URL="rtsp://$(hostname -I | awk '{print $1}'):8554/cam"
fi

# Configure mediamtx.yml
cat > mediamtx.yml << EOL
logLevel: info

# Default RTSP port
rtspAddress: :8554

paths:
  cam:
    # Run FFMPEG to capture from webcam and publish internally
    runOnInit: ffmpeg -f v4l2 -framerate 30 -i $DEVICE -c:v libx264 -pix_fmt yuv420p -preset ultrafast -b:v 800k -f rtsp rtsp://localhost:\$RTSP_PORT/cam
    runOnInitRestart: yes
$AUTH_CONFIG
EOL
[ $? -eq 0 ] || { echo "Error: Failed to write mediamtx.yml. Check disk permissions or space."; exit 1; }

read -p "Proceed to start the MediaMTX server? (y/n): " answer
answer=${answer,,}
if [ "$answer" != "y" ]; then
  echo "Start aborted."
  exit 0
fi

# Start MediaMTX
echo "Starting MediaMTX server. Stream available at $STREAM_URL"
echo "Press Ctrl+C to stop."
./mediamtx || { echo "Error: Failed to start MediaMTX. Ensure binary exists and is executable."; exit 1; }
