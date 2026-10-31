import argparse
import json
import selectors
import signal
import sys
import time
try:
    from evdev import InputDevice, UInput, AbsInfo, list_devices, ecodes as e
except ImportError:
    sys.exit("Uh oh! python-evdev is missing: install it with your package manager (python-evdev) or pip install evdev.")

MAXV = 32767
VNAME = "touchpad-abs"
MSG_INPUT = "Uh oh! I lack permission to read your touchpad: run setup-permissions.sh once."
MSG_KEYS = "Uh oh! I can't read your keyboard for the hotkey: run setup-permissions.sh --hotkey once."
MSG_UINPUT = "Uh oh! It seems like I can't open /dev/uinput: run setup-permissions.sh once, or load the uinput module"


def find_pad(path=None):
    if path:
        return InputDevice(path)
    best, score, denied = None, 0, False
    for p in list_devices():
        try:
            d = InputDevice(p)
        except PermissionError:
            denied = True
            continue
        c = d.capabilities()
        keys = c.get(e.EV_KEY, [])
        axes = [a[0] for a in c.get(e.EV_ABS, [])]
        s = 0
        if d.name != VNAME and e.BTN_TOUCH in keys and e.ABS_X in axes and e.ABS_Y in axes:
            if "touchpad" in d.name.lower():
                s = 2
            elif e.BTN_TOOL_FINGER in keys:
                s = 1
        if s > score:
            if best:
                best.close()
            best, score = d, s
        else:
            d.close()
    if best is None and denied:
        raise PermissionError
    return best


def find_keyboards(skip=None):
    out, denied = [], False
    for p in list_devices():
        try:
            d = InputDevice(p)
        except PermissionError:
            denied = True
            continue
        keys = d.capabilities().get(e.EV_KEY, [])
        if d.name != VNAME and p != skip and e.KEY_A in keys and e.KEY_ESC in keys:
            out.append(d)
        else:
            d.close()
    if not out and denied:
        raise PermissionError
    return out


def kname(c):
    n = e.KEY.get(c) or e.BTN.get(c) or f"KEY_{c}"
    return n[0] if isinstance(n, list) else n


def record():
    try:
        kbs = find_keyboards()
    except PermissionError:
        sys.exit(MSG_KEYS)
    if not kbs:
        sys.exit("Keyboard not detected.")
    sel = selectors.DefaultSelector()
    for k in kbs:
        sel.register(k, selectors.EVENT_READ)
    held, combo = set(), []
    end = time.monotonic() + 30
    while time.monotonic() < end:
        for key, _ in sel.select(1):
            try:
                evs = list(key.fileobj.read())
            except BlockingIOError:
                continue
            for ev in evs:
                if ev.type != e.EV_KEY or ev.value == 2:
                    continue
                if ev.value == 1:
                    held.add(ev.code)
                    if len(combo) < 3 and ev.code not in combo:
                        combo.append(ev.code)
                        print(json.dumps({"keys": [kname(c) for c in combo], "done": False}), flush=True)
                else:
                    held.discard(ev.code)
                    if not held and combo:
                        print(json.dumps({"keys": [kname(c) for c in combo], "done": True}), flush=True)
                        return


def listen(names):
    want = {e.ecodes[n] for n in names if n in e.ecodes}
    if not want:
        return
    try:
        kbs = find_keyboards()
    except PermissionError:
        sys.exit(MSG_KEYS)
    if not kbs:
        sys.exit("Keyboard not detected.")
    sel = selectors.DefaultSelector()
    for k in kbs:
        sel.register(k, selectors.EVENT_READ)
    held, fired = set(), False
    while True:
        for key, _ in sel.select():
            try:
                evs = list(key.fileobj.read())
            except BlockingIOError:
                continue
            for ev in evs:
                if ev.type != e.EV_KEY or ev.value == 2:
                    continue
                if ev.value:
                    held.add(ev.code)
                else:
                    held.discard(ev.code)
                if want <= held:
                    if not fired:
                        fired = True
                        print("toggle", flush=True)
                else:
                    fired = False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-seconds", type=float, default=0)
    ap.add_argument("-minutes", type=float, default=0)
    ap.add_argument("-hours", type=float, default=0)
    ap.add_argument("-area", type=int, nargs=4)
    ap.add_argument("-device")
    ap.add_argument("-notap", action="store_true")
    ap.add_argument("-info", action="store_true")
    ap.add_argument("-record", action="store_true")
    ap.add_argument("-keys", nargs="*", default=[])
    ap.add_argument("-listen", action="store_true")
    a = ap.parse_args()
    limit = a.seconds + a.minutes * 60 + a.hours * 3600
    tap = [not a.notap]

    def on_tap(s, f):
        tap[0] = s == signal.SIGUSR1

    def halt(s, f):
        raise KeyboardInterrupt

    signal.signal(signal.SIGUSR1, on_tap)
    signal.signal(signal.SIGUSR2, on_tap)
    for s in (signal.SIGINT, signal.SIGTERM, signal.SIGALRM):
        signal.signal(s, halt)

    if a.record:
        try:
            record()
        except KeyboardInterrupt:
            pass
        return

    if a.listen:
        try:
            listen(a.keys)
        except KeyboardInterrupt:
            pass
        return

    try:
        dev = find_pad(a.device)
    except PermissionError:
        sys.exit(MSG_INPUT)
    except OSError as ex:
        sys.exit(f"Cannot open device: {ex}")
    if dev is None:
        sys.exit("Touchpad not detected.")

    ax, ay = dev.absinfo(e.ABS_X), dev.absinfo(e.ABS_Y)
    W, H = ax.max - ax.min, ay.max - ay.min
    if a.info:
        print(json.dumps({"name": dev.name, "path": dev.path, "w": W, "h": H, "rx": ax.resolution, "ry": ay.resolution}))
        return

    area = a.area or [0, 0, W, H]
    x0, y0 = area[0], area[1]
    x1, y1 = x0 + area[2], y0 + area[3]
    minx, miny = ax.min, ay.min

    caps = {
        e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT],
        e.EV_ABS: [
            (e.ABS_X, AbsInfo(0, 0, MAXV, 0, 0, 0)),
            (e.ABS_Y, AbsInfo(0, 0, MAXV, 0, 0, 0)),
        ],
    }
    try:
        ui = UInput(caps, name=VNAME)
    except Exception:
        sys.exit(MSG_UINPUT)

    def scale(v, lo, hi):
        return int(min(max((v - lo) / (hi - lo), 0), 1) * MAXV)

    try:
        dev.grab()
    except OSError:
        ui.close()
        sys.exit("Touchpad is busy: is Tabyam already running?")

    sel = selectors.DefaultSelector()
    sel.register(dev, selectors.EVENT_READ, "pad")

    if limit > 0:
        signal.setitimer(signal.ITIMER_REAL, limit)

    x = y = 0
    down = press = release = ignored = clicked = False
    pb = None

    def handle(ev):
        nonlocal x, y, down, press, release, ignored, clicked, pb
        if ev.type == e.EV_ABS and ev.code == e.ABS_X:
            x = ev.value - minx
        elif ev.type == e.EV_ABS and ev.code == e.ABS_Y:
            y = ev.value - miny
        elif ev.type == e.EV_KEY and ev.code == e.BTN_TOUCH:
            if ev.value:
                down = press = True
            else:
                down = False
                release = True
        elif ev.type == e.EV_KEY and ev.code == e.BTN_LEFT:
            if ev.value:
                pb = None if ignored else e.BTN_RIGHT
            if pb is not None:
                ui.write(e.EV_KEY, pb, ev.value)
                ui.syn()
            if not ev.value:
                pb = None
        elif ev.type == e.EV_SYN:
            if press:
                ignored = not (x0 <= x <= x1 and y0 <= y <= y1)
            if (down or press) and not ignored:
                ui.write(e.EV_ABS, e.ABS_X, scale(x, x0, x1))
                ui.write(e.EV_ABS, e.ABS_Y, scale(y, y0, y1))
                ui.syn()
            if press and not ignored and tap[0]:
                ui.write(e.EV_KEY, e.BTN_LEFT, 1)
                ui.syn()
                clicked = True
            if release:
                if clicked:
                    ui.write(e.EV_KEY, e.BTN_LEFT, 0)
                    ui.syn()
                    clicked = False
                ignored = False
            press = release = False

    try:
        while True:
            for key, _ in sel.select():
                try:
                    evs = list(key.fileobj.read())
                except BlockingIOError:
                    continue
                for ev in evs:
                    handle(ev)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            dev.ungrab()
        except OSError:
            pass
        ui.close()


main()
