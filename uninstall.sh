#!/bin/bash
# uninstall.sh - undo install.sh and turn the built-in Bluetooth back on
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }

CONF=/etc/bt-dongle-fix.conf
RULE=/etc/udev/rules.d/99-disable-internal-bt.rules
MAIN=/etc/bluetooth/main.conf

INTERNAL=""; BACKUP_DIR=""
[ -f "$CONF" ] && . "$CONF"

# Turn the chip back on right now (no reboot needed)
if [ -x /usr/local/bin/btinternal ] && [ -n "$INTERNAL" ]; then
    /usr/local/bin/btinternal on >/dev/null || true
fi

rm -f "$RULE"
echo "Removed $RULE"

if [ -n "$BACKUP_DIR" ] && [ -f "$BACKUP_DIR/main.conf" ]; then
    cp -a "$BACKUP_DIR/main.conf" "$MAIN"
    echo "Restored $MAIN from $BACKUP_DIR"
else
    echo "No backup of $MAIN found, left as is (ControllerMode = dual is harmless)."
fi

# Bring back hacks that install.sh retired
for f in /etc/udev/rules.d/*.rules.disabled; do
    [ -f "$f" ] || continue
    if [ -n "$BACKUP_DIR" ] && [ -f "$BACKUP_DIR/$(basename "${f%.disabled}")" ]; then
        mv "$f" "${f%.disabled}"
        echo "Re-enabled ${f%.disabled}"
    fi
done

rm -f /usr/local/bin/btinternal /usr/local/bin/btpairing "$CONF"

udevadm control --reload-rules
udevadm trigger --action=add --subsystem-match=usb
systemctl restart bluetooth
echo "Done. Built-in Bluetooth is back. Backups are kept in /var/backups/bt-dongle-fix/"
