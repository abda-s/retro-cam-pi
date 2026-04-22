#!/bin/bash
# Restore WiFi and disabled services
# Run with: sudo bash restore-wifi.sh

echo "Re-enabling WiFi and all disabled services..."

# Re-enable services that were disabled for faster boot
systemctl enable cloud-init
systemctl enable bluetooth
systemctl enable avahi-daemon
systemctl enable ModemManager
systemctl enable keyboard-setup

# Unmask NetworkManager wait-online service
systemctl unmask NetworkManager-wait-online.service

# Restart WiFi to apply changes
systemctl restart wifi-connect

echo "Done! WiFi services restored."
echo "Reboot to apply all changes: sudo reboot"