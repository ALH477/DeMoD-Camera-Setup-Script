DeMoD Camera Setup Script
Developed by DeMoD LLC
This project transforms your Single-Board Computer (SBC) into an IP camera system, streaming USB webcam feeds over RTSP using FFMPEG and MediaMTX. It supports large-scale deployments with multi-camera configurations via JSONC and is optimized for various SBC architectures (ARM 32/64-bit, RISC-V, x86-64).
Features

Modular Design: Shared logic in utils.py for JSONC parsing, security checks, and YML generation.
Multi-Camera Support: Configure multiple cameras using JSONC with environment variable integration for passwords.
Broad SBC Compatibility: Supports ARM (32/64-bit), RISC-V, and x86-64 architectures with architecture-specific MediaMTX binaries.
Security Features: SHA256 checksum verification, firewall configuration (UFW or firewalld), and optional RTSP authentication.
User Interfaces: CLI (start.sh), TUI (security_checker.py), and web-based (config.py) configuration options.
Robust Error Handling: Input validation and clear error messages for reliable operation.
Security Rating System: Evaluates system security with automated checks and user responses.
GPL v3 Licensed: Ensures all improvements remain open source.

Requirements

SBC running Debian-based (e.g., Armbian) or Fedora-based Linux with appropriate package manager.
USB webcam(s) with Video4Linux2 (v4l2) support.
Installed dependencies: FFMPEG, firewall tools (ufw or firewalld), Git, Vim. The setup script handles v4l-utils, wget, tar, python3.
Network access for downloading MediaMTX.

Installation

Clone or download the repository containing: setup.sh, start.sh, config.py, security_checker.py, utils.py, config.jsonc, LICENSE.
Set executable permissions: chmod +x setup.sh start.sh.
Run ./setup.sh (with sudo if needed). Select OS type and SBC architecture, follow prompts to install dependencies, download MediaMTX, configure firewall, and optionally run the security checker.

Usage

CLI Single-Camera Setup: Run ./start.sh for interactive single-camera configuration.
Web Configuration: Run python3 config.py and access http://<sbc-ip>:8000. Paste JSONC for multi-camera setups or use form fields for single. Answer security questions to improve the rating.
TUI Security Checker: Run python3 security_checker.py for guided security and configuration, supporting JSONC for multi-camera setups.
Stream URLs: rtsp://<sbc-ip>:8554/cam<i> (e.g., cam0, cam1; include user:pass@ if authentication enabled).
Environment Variables: For secure password management, set variables (e.g., export RTSP_PASS_CAM0=secret) before using JSONC configs.
Auto-Start: Add to crontab: @reboot /path/to/start.sh (single-camera, pre-configure YML). For multi-camera or TUI/web, use systemd services.
Stop: Press Ctrl+C in terminal or use the web interface to restart (terminates old process).

Sample config.jsonc
{
  // Example multi-camera configuration
  "cams": [
    {
      "device": "/dev/video0",
      "framerate": 30,
      "bitrate": "800k",
      "auth": {
        "user": "user1",
        "pass": "env:RTSP_PASS_CAM0"
      }
    },
    {
      "device": "/dev/video1",
      "framerate": 25,
      "bitrate": "600k"
    }
  ]
}

Security Notes

Authentication: Enable RTSP authentication to prevent unauthorized stream access.
Environment Variables: Use env:VAR_NAME in JSONC for passwords to avoid plain text storage.
Firewall: By default, only port 8554/TCP is opened. Add rules for port 8000 if exposing the web interface (use VPN for security).
Downloads: MediaMTX downloads are verified with SHA256 checksums.
Privileges: Run as a non-root user and ensure membership in the 'video' group for webcam access.
Network Exposure: Avoid exposing ports publicly without HTTPS/VPN. The web server binds to localhost by default.
Password Storage: Passwords are stored in plain text in mediamtx.yml. Secure the device and use environment variables.
Use security_checker.py or config.py to assess and improve security settings. The rating system combines automated checks with user responses.

Multi-SBC Compatibility
The codebase supports multiple SBC architectures and OSes:

OS Support: Debian-like (apt/ufw) and Fedora-like (dnf/firewalld).
Architecture Support: ARM 64-bit, ARM 32-bit, RISC-V, x86-64.The setup.sh script prompts for OS type and architecture to download the correct MediaMTX binary and configure the firewall accordingly. For other OSes (e.g., Arch), modify the script's package and firewall commands.

Troubleshooting

No Webcam Detected: Verify devices with ls /dev/video* or v4l2-ctl --list-devices.
Checksum Failure: Retry download; check network or file integrity.
JSONC Parse Error: Validate JSONC syntax (see sample above).
Environment Variable Missing: Set variables (e.g., export RTSP_PASS_CAM0=secret) before running.
Stream Issues: Test with ffplay rtsp://localhost:8554/cam0 on the SBC.
High CPU Usage: Reduce bitrate/framerate in configuration.
Check MediaMTX logs (runs in foreground) for details.

License
This project is licensed under the GNU General Public License v3.0 (GPL v3). See the LICENSE file for details. Any modifications or derivative works must also be licensed under GPL v3, ensuring improvements remain open source. For more information, visit https://www.gnu.org/licenses/gpl-3.0.html.
Contributing
Contributions are welcome! Ensure changes are licensed under GPL v3 and include the appropriate copyright notice. Submit pull requests with clear descriptions of improvements.
Support
For support, contact DeMoD LLC.
