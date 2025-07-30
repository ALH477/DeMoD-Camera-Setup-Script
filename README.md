DeMoD Camera Setup Script
Developed by DeMoD LLC
This project turns your Orange Pi Zero 2W into an IP camera by streaming USB webcam feeds over RTSP using FFMPEG and MediaMTX. It supports large-scale deployments with multi-camera configurations via JSONC.
Features

Modular design with utils.py for shared logic (JSONC parsing, security checks, YML writing).
JSONC support for automated multi-camera setups, with comments and environment variable integration for passwords.
Environment variable support for sensitive data (e.g., passwords).
Automatic USB webcam detection and selection.
RTSP streaming with configurable H.264 encoding (bitrate, framerate).
Optional basic authentication for streams.
Firewall configuration (UFW port 8554/TCP).
Download integrity verification via SHA256 checksums.
Robust error handling.
Web-based configuration (config.py) with security status, rating system, and yes/no security questions.
TUI-based security checker (security_checker.py) for guided setup and security assessments.
Compatible with Linux on Orange Pi Zero 2W (assumes apt, UFW, FFMPEG installed).

Requirements

Orange Pi Zero 2W running Linux (e.g., Armbian).
USB webcam(s) connected.
Installed: FFMPEG, UFW, Git, Vim (as per your setup). The script installs v4l-utils, Python 3, etc.
Network access for downloads.

Installation

Clone or download the scripts: setup.sh, start.sh, config.py, security_checker.py, utils.py, config.jsonc, LICENSE.
Make executable: chmod +x setup.sh start.sh.
Run ./setup.sh (with sudo if needed). Follow prompts to install dependencies, download MediaMTX, configure UFW, and optionally run the security checker.

Usage

CLI Streaming: Run ./start.sh for single-camera setup with interactive prompts.
Web Configuration: Run python3 config.py and access http://<orange-pi-ip>:8000. Paste JSONC content for multi-camera setup or use form fields for single-camera. Answer security questions to improve the rating.
TUI Security Checker: Run python3 security_checker.py for a guided security walkthrough, supporting JSONC for multi-camera configs.
Stream URL: rtsp://<orange-pi-ip>:8554/cam<i> (e.g., cam0, cam1; include user:pass@ if authentication enabled).
Environment Variables: For secure password management, set environment variables (e.g., export RTSP_PASS_CAM0=secret) before running scripts with JSONC configs.
Auto-Start: Add to crontab: @reboot /path/to/start.sh (non-interactive; pre-configure YML). For web/TUI, use systemd services.
Stop: Press Ctrl+C in terminal or use web interface to restart (kills old process).

Security Notes

Authentication: Enable RTSP authentication to prevent unauthorized access.
Environment Variables: Use env:VAR_NAME in JSONC for passwords to avoid plain text storage.
Firewall: Only port 8554/TCP is opened by default; add UFW rule for web port 8000 if exposing remotely (not recommended—use VPN).
Downloads: Verified with SHA256 checksums for integrity.
Privileges: Run as non-root user; add to 'video' group for webcam access.
Exposure: Do not expose ports publicly without HTTPS/VPN. Web server binds to localhost by default.
Passwords: Stored in plain text in mediamtx.yml—secure your device physically and use env vars where possible.
Use security_checker.py or config.py to verify and adjust security settings. The rating system incorporates automated checks and user responses for a comprehensive score.

Troubleshooting

No Webcam Detected: Run ls /dev/video* or v4l2-ctl --list-devices to verify devices.
Checksum Failure: Retry download; possible network issue or tampering.
JSONC Parse Error: Ensure valid JSONC format (see config.jsonc sample).
Environment Variable Not Set: Set variables (e.g., export RTSP_PASS_CAM0=secret) before running.
Stream Not Working: Test with ffplay rtsp://localhost:8554/cam0 on the Pi.
High CPU Usage: Lower bitrate/framerate in config.
Check MediaMTX logs (runs in foreground) for detailed errors.

License
This project is licensed under the GNU General Public License v3.0 (GPL v3). See the LICENSE file for details. Any modifications or derivative works must also be licensed under GPL v3, ensuring that improvements remain open source. For more information, visit https://www.gnu.org/licenses/gpl-3.0.html.
Contributing
Contributions are welcome! Please ensure that any changes are licensed under GPL v3 and include the appropriate copyright notice. Submit pull requests with clear descriptions of improvements.
Support
For support, contact DeMoD LLC.
