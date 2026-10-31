#!/bin/sh
set -e
[ "$(id -u)" -eq 0 ] || exec sudo sh "$0" "$@"
cat > /etc/udev/rules.d/60-tabyam.rules <<'EOF'
KERNEL=="uinput", SUBSYSTEM=="misc", OPTIONS+="static_node=uinput", TAG+="uaccess"
KERNEL=="event*", SUBSYSTEM=="input", ENV{ID_INPUT_TOUCHPAD}=="1", TAG+="uaccess"
EOF
if [ "$1" = "--hotkey" ]; then
cat > /etc/udev/rules.d/61-tabyam-keyboard.rules <<'EOF'
KERNEL=="event*", SUBSYSTEM=="input", ENV{ID_INPUT_KEYBOARD}=="1", TAG+="uaccess"
EOF
fi
echo uinput > /etc/modules-load.d/tabyam.conf
modprobe uinput || true
udevadm control --reload
udevadm trigger --subsystem-match=input --subsystem-match=misc --action=change
echo "Tabyam permissions are set."
