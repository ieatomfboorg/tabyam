# Tabyam

Makes your trackpad function like a drawing tablet, featuring absolute positioning, Area profiles, Tap to click, and a toggle keybind.

<p align="center"><img src="assets/logo.svg" width="128" alt="Tabyam logo"></p>

## Features

- Absolute positioning: Picking any part of trackpad instantly maps it to the whole screen
- Ratio presets (Full, 16:9, 16:10, 4:3, 3:4, 1:1, Quarter) Pick whatever suits your use
- Tap to click switch: On by default. Turning it off prevents the trackpad from performing any sort of clicking. 
- Profiles: Name and save presets for future use.
- Toggle keybind: Record a keybind to toggle Tabyam on or off.
- Dark and light themes with a choice of accent colors.

## Pre-requirements

Run one of following commands based on your distro :

Arch, Manjaro, EndeavourOS:

```
sudo pacman -S python python-evdev python-pyqt6
```

Debian, Ubuntu, Mint:

```
sudo apt install python3 python3-evdev python3-pyqt6
```

Fedora:

```
sudo dnf install python3 python3-evdev python3-pyqt6
```

## Installation

To Acquire and start using Tabyam, either download the package from Releases, or run the install script.
                                                                                        Note that the script is a Linux only.

```
git clone https://github.com/ieatomfboorg/tabyam
cd tabyam
sh install.sh
```

The install scipt obtains `python`, `python-evdev` and PyQt6 using your package manager (pacman, apt or dnf), adds the `tabyam` command alongside a menu entry, and sets up the permissions Tabyam needs. If your distro doesn't have neither pacman, apt or dnf, acquire the dependenices yourself then run the install script again.

## Use

1. Execute Tabyam either using a terminal or the menu entry, and pick an area that suits you, either using the preloaded presets or by making one yourself.
2. Press Run.

To turn off, press Kill, or your toggle keybind. To record a toggle keybind, head over to settings and record up to 3 keys at once.

## Status

This project is mostly targeted towards the osu! community and artists that can't afford a drawing tablet.

Developed and tested on Arch Linux. If Tabyam doesn't work or doesn't function properly on an alternative distro, please do not hesitate to open an issue describing what won't work or what doesn't work properly.
A Windows release is planned.

## License

Seek the `LICENSE` file.
