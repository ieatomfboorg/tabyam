#!/bin/sh
set -e

pause() {
    [ -t 0 ] || return 0
    printf "Press Enter to close. "
    read -r _ || true
}

finish() {
    code=$?
    if [ "$code" -ne 0 ]; then
        echo "Install stopped (exit code $code). Read the messages above."
    fi
    pause
}

trap finish EXIT

DIR="$(cd "$(dirname "$0")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
DEST="$DATA/tabyam"
BIN="$HOME/.local/bin"

if python3 -c "import evdev, PyQt6" >/dev/null 2>&1; then
    echo "Dependencies already installed."
elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --needed --noconfirm python python-evdev python-pyqt6
elif command -v apt-get >/dev/null 2>&1; then
    sudo apt-get install -y python3 python3-evdev python3-pyqt6
elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y python3 python3-evdev python3-pyqt6
else
    echo "Your distro doesn't use pacman, apt or dnf. Install python3, python-evdev and PyQt6 manually using your package manager, then run this script again."
    exit 1
fi

mkdir -p "$DEST" "$BIN" "$DATA/applications"
cp "$DIR/core.py" "$DIR/ui.py" "$DEST/"

cat > "$BIN/tabyam" <<EOF
#!/bin/sh
exec python3 "$DEST/ui.py" "\$@"
EOF
chmod +x "$BIN/tabyam"

cat > "$DATA/applications/tabyam.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Tabyam
Comment=Use your touchpad as a drawing tablet
Exec=$BIN/tabyam
Terminal=false
Categories=Utility;
EOF

FLAG=""
echo
echo "The toggle hotkey lets you start and stop Tabyam with a key combo, and needs permission to read your keyboard."
printf "Enable the toggle hotkey? [y/N] "
read -r ans || ans=n
case "$ans" in y|Y) FLAG="--hotkey" ;; esac
echo "Setting up permissions . . ."
sudo sh "$DIR/setup-permissions.sh" $FLAG
if [ -n "$FLAG" ]; then
    echo "Keyboard access for the hotkey is enabled. To undo it, run : sudo rm /etc/udev/rules.d/61-tabyam-keyboard.rules"
fi

echo "Done. To run, execute Tabyam via terminal or menu entry."
case ":$PATH:" in *":$BIN:"*) ;; *) echo "Add $BIN to PATH to launch it by name." ;; esac
