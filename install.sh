#!/bin/sh

DIR="$(cd "$(dirname "$0")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
DEST="$DATA/tabyam"
BIN="$HOME/.local/bin"
LOG="${TMPDIR:-/tmp}/tabyam-install-$(id -u).log"
FAIL="${TMPDIR:-/tmp}/tabyam-install-$(id -u).failed"
TITLE="Tabyam setup"
FLAG=""
KEEP=""
SUDO=sudo
[ "$(id -u)" -eq 0 ] && SUDO=""
BOX=0
if [ -t 0 ] && [ -t 1 ] && command -v whiptail >/dev/null 2>&1; then
    BOX=1
fi
: > "$LOG"
rm -f "$FAIL"

cleanup() {
    [ -n "$KEEP" ] && kill "$KEEP" 2>/dev/null
    return 0
}
trap cleanup EXIT

banner() {
    [ "$BOX" = 1 ] && return 0
    printf '\n  +----------------------------------+\n'
    printf '  |  %-32s|\n' "$1"
    printf '  +----------------------------------+\n\n'
}

msg() {
    if [ "$BOX" = 1 ]; then
        whiptail --title "$TITLE" --msgbox "$1" 16 64
    else
        printf '%s\n\n' "$1"
        if [ -t 0 ]; then
            printf 'Press Enter to continue. '
            read -r _ || true
            printf '\n'
        fi
    fi
}

ask() {
    if [ "$BOX" = 1 ]; then
        whiptail --title "$TITLE" --defaultno --yesno "$1" 16 64
    else
        printf '%s [y/N] ' "$1"
        read -r a || a=n
        printf '\n'
        case "$a" in y|Y) return 0 ;; *) return 1 ;; esac
    fi
}

progress() {
    if [ "$BOX" = 1 ]; then
        printf 'XXX\n%s\n%s\nXXX\n' "$1" "$2"
    else
        printf '  [%3s%%] %s\n' "$1" "$2"
    fi
}

keepalive() {
    while kill -0 "$$" 2>/dev/null; do
        sudo -n true 2>/dev/null
        sleep 50
    done
}

run_steps() {
    progress 5 "Getting things ready"
    if ! python3 -c "import evdev, PyQt6" >/dev/null 2>&1; then
        progress 15 "Installing what Tabyam needs"
        if command -v pacman >/dev/null 2>&1; then
            $SUDO pacman -S --needed --noconfirm python python-evdev python-pyqt6 qt6-svg >>"$LOG" 2>&1 || return 1
        elif command -v apt-get >/dev/null 2>&1; then
            $SUDO apt-get install -y python3 python3-evdev python3-pyqt6 >>"$LOG" 2>&1 || return 1
        elif command -v dnf >/dev/null 2>&1; then
            $SUDO dnf install -y python3 python3-evdev python3-pyqt6 >>"$LOG" 2>&1 || return 1
        else
            echo unsupported > "$FAIL"
            return 1
        fi
    fi

    progress 55 "Adding Tabyam to your apps"
    mkdir -p "$DEST/assets" "$BIN" "$DATA/applications" >>"$LOG" 2>&1 || return 1
    cp "$DIR/core.py" "$DIR/ui.py" "$DEST/" >>"$LOG" 2>&1 || return 1
    cp "$DIR/assets/icon.svg" "$DEST/assets/" >>"$LOG" 2>&1 || return 1

    cat > "$BIN/tabyam" <<EOF || return 1
#!/bin/sh
exec python3 "$DEST/ui.py" "\$@"
EOF
    chmod +x "$BIN/tabyam" || return 1

    cat > "$DATA/applications/tabyam.desktop" <<EOF || return 1
[Desktop Entry]
Type=Application
Name=Tabyam
Comment=Use your touchpad as a drawing tablet
Icon=$DEST/assets/icon.svg
Exec=$BIN/tabyam
Terminal=false
Categories=Utility;
EOF

    progress 75 "Letting Tabyam use your touchpad"
    $SUDO sh "$DIR/setup-permissions.sh" $FLAG >>"$LOG" 2>&1 || return 1

    progress 100 "All done"
    return 0
}

banner "Tabyam setup"

MISSING=""
for f in core.py ui.py setup-permissions.sh assets/icon.svg; do
    [ -f "$DIR/$f" ] || MISSING="$MISSING $f"
done
if [ -n "$MISSING" ]; then
    msg "Some of Tabyam's files are missing next to this installer.

Extract the whole download first, then run install.sh from inside that folder instead of running it on its own."
    exit 1
fi

msg "Welcome to Tabyam!

This sets things up so your touchpad can work like a drawing tablet.

It takes about a minute. You may be asked for your password."

if ask "Turn on the toggle hotkey?

It lets you switch Tabyam on and off with a key combo, even while a game is open. To do that, Tabyam needs to be allowed to see your keyboard.

You can skip this and still use Tabyam."; then
    FLAG="--hotkey"
fi

if [ -n "$SUDO" ]; then
    printf '\nEnter your password to continue.\n\n'
    if ! sudo -v; then
        msg "That password didn't work, so setup has stopped. Nothing was changed.

Run the installer again to retry."
        exit 1
    fi
    keepalive &
    KEEP=$!
fi

if [ "$BOX" = 1 ]; then
    { run_steps || { [ -e "$FAIL" ] || echo failed > "$FAIL"; }; } | whiptail --title "$TITLE" --gauge "Getting started" 7 64 0
else
    run_steps || { [ -e "$FAIL" ] || echo failed > "$FAIL"; }
    printf '\n'
fi

if [ -e "$FAIL" ]; then
    if [ "$(cat "$FAIL")" = "unsupported" ]; then
        msg "Tabyam couldn't install what it needs on this system automatically.

Please install Python 3, evdev and PyQt6 using your package manager, then run this installer again."
    else
        msg "Something went wrong during setup.

A report was saved to:
$LOG

Send it along if you ask for help."
    fi
    exit 1
fi

DONE="Tabyam is ready!

Open it from your apps menu, or type tabyam in a terminal."
case ":$PATH:" in
    *":$BIN:"*) ;;
    *) DONE="$DONE

To start it by name, add $BIN to your PATH. The apps menu works either way." ;;
esac
if [ -n "$FLAG" ]; then
    DONE="$DONE

The hotkey is on. To turn it off later, run:
sudo rm /etc/udev/rules.d/61-tabyam-keyboard.rules"
fi
msg "$DONE"
