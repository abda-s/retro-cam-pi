#!/bin/bash
# Disable WiFi and optional services again (slower boot, but saves resources)
# Run with: sudo bash disable-wifi.sh

echo "Disabling WiFi and optional services for faster boot..."

# Stop WiFi service
systemctl stop wifi-connect

# Disable services
systemctl disable bluetooth
systemctl disable avahi-daemon
systemctl disable ModemManager
systemctl disable cloud-init
systemctl disable keyboard-setup

# Mask NetworkManager wait-online
systemctl mask NetworkManager-wait-online.service

echo "Done! WiFi disabled."
echo "Reboot to apply all changes: sudo reboot"
echo ""
echo "To re-enable later, run: sudo bash restore-wifi.sh"