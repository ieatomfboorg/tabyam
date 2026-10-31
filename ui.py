import json
import os
import signal
import subprocess
import sys
import time
from PyQt6.QtCore import QEasingCurve, QPointF, QProcess, QRectF, Qt, QTimer, QVariantAnimation, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QIcon, QLinearGradient, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QButtonGroup, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QInputDialog,
    QLabel, QMenu, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

PY = sys.executable
CORE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core.py")
CONF = os.path.expanduser("~/.config/tabyam/config.json")
ACCENTS = ["#2563eb", "#7c3aed", "#db2777", "#16a34a", "#ea580c"]
PRESETS = [("Full", None), ("16:9", (16, 9)), ("16:10", (16, 10)), ("4:3", (4, 3)), ("3:4", (3, 4)), ("1:1", (1, 1)), ("Quarter", "q")]
PAL = {
    "dark": {"bg": "#1b1c20", "panel": "#25262b", "text": "#e6e6e8", "title": "#ffffff", "hint": "#7f7f88", "seg": "#2c2d33", "seghover": "#36373d", "navhover": "#2f3036", "off": "#3a3b42", "pad": "#25262b", "padline": "#3a3b42", "ok": "#4ade80", "mute": "#8e8e96", "err": "#f87171"},
    "light": {"bg": "#eceef2", "panel": "#ffffff", "text": "#1c1d21", "title": "#111216", "hint": "#6a6b75", "seg": "#e3e5ea", "seghover": "#d6d9e0", "navhover": "#eef0f4", "off": "#c8cbd3", "pad": "#ffffff", "padline": "#c9ccd4", "ok": "#16a34a", "mute": "#6a6b75", "err": "#dc2626"},
}
HANDLES = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
CURS = {
    (-1, -1): Qt.CursorShape.SizeFDiagCursor, (1, 1): Qt.CursorShape.SizeFDiagCursor,
    (1, -1): Qt.CursorShape.SizeBDiagCursor, (-1, 1): Qt.CursorShape.SizeBDiagCursor,
    (-1, 0): Qt.CursorShape.SizeHorCursor, (1, 0): Qt.CursorShape.SizeHorCursor,
    (0, -1): Qt.CursorShape.SizeVerCursor, (0, 1): Qt.CursorShape.SizeVerCursor,
}
NICE = {"LEFTCTRL": "Ctrl", "RIGHTCTRL": "Ctrl", "LEFTSHIFT": "Shift", "RIGHTSHIFT": "Shift", "LEFTALT": "Alt", "RIGHTALT": "Alt", "LEFTMETA": "Meta", "RIGHTMETA": "Meta", "ESC": "Esc"}


def clamp(v, lo, hi):
    return min(max(v, lo), hi)


def load_conf():
    d = {"tap": True, "accent": 4, "theme": "dark", "x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0, "stop": [], "profiles": {}}
    try:
        with open(CONF) as f:
            d.update(json.load(f))
    except Exception:
        pass
    try:
        d["accent"] = int(d["accent"]) % len(ACCENTS)
    except Exception:
        d["accent"] = 4
    if d["theme"] not in PAL:
        d["theme"] = "dark"
    if not isinstance(d["stop"], list):
        d["stop"] = []
    d["stop"] = [k for k in d["stop"] if isinstance(k, str)][:3]
    if not isinstance(d["profiles"], dict):
        d["profiles"] = {}
    try:
        d["w"] = clamp(float(d["w"]), 0.1, 1.0)
        d["h"] = clamp(float(d["h"]), 0.1, 1.0)
        d["x"] = clamp(float(d["x"]), 0.0, 1 - d["w"])
        d["y"] = clamp(float(d["y"]), 0.0, 1 - d["h"])
    except Exception:
        d.update(x=0.0, y=0.0, w=1.0, h=1.0)
    return d


def save_conf(d):
    try:
        os.makedirs(os.path.dirname(CONF), exist_ok=True)
        with open(CONF, "w") as f:
            json.dump(d, f)
    except Exception:
        pass


def make_icon(ac):
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(ac))
    p.drawRoundedRect(QRectF(4, 4, 56, 56), 14, 14)
    p.setPen(QColor("white"))
    f = QFont()
    f.setBold(True)
    f.setPixelSize(38)
    p.setFont(f)
    p.drawText(QRectF(0, 0, 64, 64), Qt.AlignmentFlag.AlignCenter, "T")
    p.end()
    return QIcon(pm)


def pretty(names):
    if not names:
        return "None"
    out = []
    for n in names:
        k = n[4:] if n.startswith("KEY_") else n
        out.append(NICE.get(k, k.title() if len(k) > 1 else k))
    return " + ".join(out)


def sheet(ac, p):
    return f"""
#root {{ background: {p['bg']}; }}
QDialog {{ background: {p['bg']}; }}
QLabel {{ color: {p['text']}; font-size: 14px; background: transparent; }}
QLabel#title {{ color: {p['title']}; font-size: 34px; font-weight: 800; padding: 4px 8px 16px 8px; }}
QLabel#h {{ color: {ac}; font-size: 18px; font-weight: 800; padding-top: 10px; }}
QLabel#hint {{ color: {p['hint']}; font-size: 12px; }}
QLabel#strip {{ background: {p['panel']}; border-radius: 10px; padding: 10px 14px; }}
QFrame#side {{ background: {p['panel']}; border-radius: 14px; }}
QPushButton {{ font-size: 14px; border: none; color: {p['text']}; }}
QPushButton#nav {{ background: transparent; text-align: left; padding: 11px 14px; border-radius: 10px; }}
QPushButton#nav:hover {{ background: {p['navhover']}; }}
QPushButton#nav:checked {{ background: {ac}; color: white; }}
QPushButton#seg {{ background: {p['seg']}; padding: 9px 16px; border-radius: 9px; }}
QPushButton#seg:hover {{ background: {p['seghover']}; }}
QPushButton#seg:checked {{ background: {ac}; color: white; }}
QPushButton#go {{ background: {ac}; color: white; padding: 12px; border-radius: 10px; font-weight: 700; }}
QPushButton#go:checked {{ background: {p['off']}; color: {p['text']}; }}
QDialogButtonBox QPushButton {{ background: {p['seg']}; padding: 8px 16px; border-radius: 9px; }}
QDoubleSpinBox {{ background: {p['seg']}; border: none; border-radius: 8px; padding: 7px 10px; color: {p['text']}; font-size: 14px; min-width: 110px; selection-background-color: {ac}; }}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0px; border: none; }}
QLineEdit {{ background: {p['seg']}; color: {p['text']}; border: none; border-radius: 8px; padding: 7px 10px; selection-background-color: {ac}; }}
QMenu {{ background: {p['panel']}; color: {p['text']}; border: 1px solid {p['off']}; }}
QMenu::item {{ padding: 6px 18px; }}
QMenu::item:selected {{ background: {ac}; color: white; }}
"""


def resize_area(a0, hx, hy, u, v):
    x, y, w, h = a0
    cx, cy = x + w / 2, y + h / 2
    c = []
    if hx:
        c.append(((u - x) if hx > 0 else (x + w - u)) / w)
    if hy:
        c.append(((v - y) if hy > 0 else (y + h - v)) / h)
    s = max(c)
    lo = max(0.1 / w, 0.1 / h)
    mw = (1 - x) if hx > 0 else ((x + w) if hx < 0 else 2 * min(cx, 1 - cx))
    mh = (1 - y) if hy > 0 else ((y + h) if hy < 0 else 2 * min(cy, 1 - cy))
    hi = max(min(mw / w, mh / h), lo)
    s = clamp(s, lo, hi)
    nw, nh = w * s, h * s
    nx = x if hx > 0 else ((x + w - nw) if hx < 0 else cx - nw / 2)
    ny = y if hy > 0 else ((y + h - nh) if hy < 0 else cy - nh / 2)
    return [clamp(nx, 0, 1 - nw), clamp(ny, 0, 1 - nh), nw, nh]


class Canvas(QWidget):
    changed = pyqtSignal()
    sized = pyqtSignal()
    done = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setMinimumSize(420, 280)
        self.setMouseTracking(True)
        self.area = [0.0, 0.0, 1.0, 1.0]
        self.aspect = 1816 / 1101
        self.accent = QColor(ACCENTS[4])
        self.pal = PAL["dark"]
        self.last = None
        self.hdl = None
        self.a0 = None

    def pad_rect(self):
        m = 16
        aw, ah = self.width() - 2 * m, self.height() - 2 * m
        if aw / ah > self.aspect:
            h = ah
            w = h * self.aspect
        else:
            w = aw
            h = w / self.aspect
        return QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h)

    def area_rect(self):
        p = self.pad_rect()
        x, y, w, h = self.area
        return QRectF(p.x() + x * p.width(), p.y() + y * p.height(), w * p.width(), h * p.height())

    def handle_pos(self, hx, hy):
        r = self.area_rect()
        xs = (r.left(), r.center().x(), r.right())
        ys = (r.top(), r.center().y(), r.bottom())
        return xs[hx + 1], ys[hy + 1]

    def hit(self, pt):
        best, bd = None, 14.0
        for hx, hy in HANDLES:
            x, y = self.handle_pos(hx, hy)
            d = ((pt.x() - x) ** 2 + (pt.y() - y) ** 2) ** 0.5
            if d < bd:
                best, bd = (hx, hy), d
        return best

    def paintEvent(self, ev):
        q = QPainter(self)
        q.setRenderHint(QPainter.RenderHint.Antialiasing)
        q.setPen(QPen(QColor(self.pal["padline"]), 2))
        q.setBrush(QColor(self.pal["pad"]))
        q.drawRoundedRect(self.pad_rect(), 10, 10)
        fill = QColor(self.accent)
        fill.setAlpha(70)
        q.setPen(QPen(self.accent, 2))
        q.setBrush(fill)
        q.drawRoundedRect(self.area_rect(), 4, 4)
        q.setPen(QPen(QColor(self.pal["pad"]), 2))
        q.setBrush(QColor(self.accent).lighter(160))
        for hx, hy in HANDLES:
            x, y = self.handle_pos(hx, hy)
            q.drawEllipse(QPointF(x, y), 5.5, 5.5)

    def mousePressEvent(self, ev):
        pt = ev.position()
        h = self.hit(pt)
        if h:
            self.hdl = h
            self.a0 = list(self.area)
        elif self.area_rect().contains(pt):
            self.last = pt

    def mouseMoveEvent(self, ev):
        pt = ev.position()
        p = self.pad_rect()
        if self.hdl:
            u, v = (pt.x() - p.x()) / p.width(), (pt.y() - p.y()) / p.height()
            self.area[:] = resize_area(self.a0, self.hdl[0], self.hdl[1], u, v)
            self.update()
            self.sized.emit()
        elif self.last is not None:
            a = self.area
            a[0] = clamp(a[0] + (pt.x() - self.last.x()) / p.width(), 0, 1 - a[2])
            a[1] = clamp(a[1] + (pt.y() - self.last.y()) / p.height(), 0, 1 - a[3])
            self.last = pt
            self.update()
            self.changed.emit()
        else:
            h = self.hit(pt)
            if h:
                self.setCursor(CURS[h])
            elif self.area_rect().contains(pt):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, ev):
        if self.hdl or self.last is not None:
            self.hdl = None
            self.last = None
            self.done.emit()


class Seg(QWidget):
    changed = pyqtSignal(int)

    def __init__(self, labels, index=0):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.group = QButtonGroup(self)
        for i, t in enumerate(labels):
            b = QPushButton(t)
            b.setObjectName("seg")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.group.addButton(b, i)
            lay.addWidget(b)
        lay.addStretch()
        self.group.button(index).setChecked(True)
        self.group.idClicked.connect(self.changed.emit)

    def set(self, i):
        self.group.button(i).setChecked(True)


class Presets(QWidget):
    picked = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        g = QGridLayout(self)
        g.setContentsMargins(0, 0, 0, 0)
        g.setSpacing(8)
        self.group = QButtonGroup(self)
        for i, (t, _) in enumerate(PRESETS):
            b = QPushButton(t)
            b.setObjectName("seg")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.group.addButton(b, i)
            g.addWidget(b, i // 3, i % 3)
        self.group.idClicked.connect(self.picked.emit)

    def clear(self):
        b = self.group.checkedButton()
        if b:
            self.group.setExclusive(False)
            b.setChecked(False)
            self.group.setExclusive(True)


class Splash(QWidget):
    def __init__(self, parent, accent, pal):
        super().__init__(parent)
        self.accent = QColor(accent)
        self.pal = pal
        self.t = 0.0
        self.alpha = 1.0
        self.sweep = QVariantAnimation(self)
        self.sweep.setStartValue(0.0)
        self.sweep.setEndValue(1.0)
        self.sweep.setDuration(1300)
        self.sweep.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.sweep.valueChanged.connect(self.on_t)
        self.sweep.finished.connect(lambda: QTimer.singleShot(250, self.fade.start))
        self.fade = QVariantAnimation(self)
        self.fade.setStartValue(1.0)
        self.fade.setEndValue(0.0)
        self.fade.setDuration(450)
        self.fade.valueChanged.connect(self.on_alpha)
        self.fade.finished.connect(self.hide)

    def start(self):
        self.t = 0.0
        self.alpha = 1.0
        self.show()
        self.raise_()
        self.sweep.start()

    def on_t(self, v):
        self.t = v
        self.update()

    def on_alpha(self, v):
        self.alpha = v
        self.update()

    def paintEvent(self, ev):
        q = QPainter(self)
        q.setRenderHint(QPainter.RenderHint.Antialiasing)
        q.setOpacity(self.alpha)
        q.fillRect(self.rect(), QColor(self.pal["bg"]))
        w, cy = self.width(), self.height() / 2
        f = QFont()
        f.setBold(True)
        f.setPixelSize(64)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        q.setFont(f)
        q.setPen(QColor(self.pal["title"]))
        q.drawText(QRectF(0, cy - 90, w, 90), Qt.AlignmentFlag.AlignCenter, "Tabyam")
        f2 = QFont()
        f2.setPixelSize(18)
        q.setFont(f2)
        q.setPen(QColor(self.pal["mute"]))
        q.drawText(QRectF(0, cy + 14, w, 30), Qt.AlignmentFlag.AlignCenter, "Welcome")
        seg = w * 0.4
        head = self.t * (w + seg)
        x0 = max(head - seg, 0)
        x1 = min(head, w)
        if x1 > x0:
            g = QLinearGradient(head - seg, 0, head, 0)
            c0 = QColor(self.accent)
            c0.setAlpha(0)
            g.setColorAt(0, c0)
            g.setColorAt(1, QColor(self.accent).lighter(130))
            q.fillRect(QRectF(x0, cy + 60, x1 - x0, 4), QBrush(g))


class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("root")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle("Tabyam")
        self.conf = load_conf()
        self.pad = None
        self.proc = None
        self.rec = None
        self.lis = None
        self.t0 = 0.0
        self.err = ""
        self.pw, self.ph = 1816.0, 1101.0
        ac = ACCENTS[self.conf["accent"]]
        pal = PAL[self.conf["theme"]]
        QApplication.instance().setStyleSheet(sheet(ac, pal))
        self.setWindowIcon(make_icon(ac))

        side = QFrame()
        side.setObjectName("side")
        side.setFixedWidth(220)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(12, 12, 12, 12)
        sl.setSpacing(4)
        sl.addWidget(self.lab("Tabyam", "title"))
        self.nav = QButtonGroup(self)
        for i, t in enumerate(("Area", "Settings")):
            b = QPushButton(t)
            b.setObjectName("nav")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.nav.addButton(b, i)
            sl.addWidget(b)
        self.nav.button(0).setChecked(True)
        sl.addStretch()
        self.status = self.lab("")
        self.devlabel = self.lab("", "hint")
        self.go = QPushButton("Run")
        self.go.setObjectName("go")
        self.go.setCheckable(True)
        self.go.setCursor(Qt.CursorShape.PointingHandCursor)
        self.go.clicked.connect(self.toggle)
        sl.addWidget(self.status)
        sl.addWidget(self.devlabel)
        sl.addSpacing(6)
        sl.addWidget(self.go)

        p1 = QWidget()
        h = QHBoxLayout(p1)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(16)
        self.canvas = Canvas()
        self.canvas.accent = QColor(ac)
        self.canvas.pal = pal
        c = self.conf
        self.canvas.area = [c["x"], c["y"], c["w"], c["h"]]
        self.canvas.changed.connect(self.on_drag)
        self.canvas.sized.connect(self.on_sized)
        self.canvas.done.connect(self.commit)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(10)
        ll.addWidget(self.canvas, 1)
        tr = QHBoxLayout()
        tr.setSpacing(12)
        tr.addWidget(self.lab("Tap to click"))
        self.tap2 = Seg(["On", "Off"], 0 if c["tap"] else 1)
        self.tap2.changed.connect(self.on_tap)
        tr.addWidget(self.tap2)
        tr.addStretch()
        ll.addLayout(tr)
        self.strip = QLabel()
        self.strip.setObjectName("strip")
        ll.addWidget(self.strip)
        h.addWidget(left, 1)

        col = QWidget()
        col.setFixedWidth(270)
        cl = QVBoxLayout(col)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(6)
        cl.addWidget(self.lab("Ratio", "h"))
        self.presets = Presets()
        self.presets.picked.connect(self.on_preset)
        cl.addWidget(self.presets)
        cl.addSpacing(8)
        cl.addWidget(self.lab("Dimensions", "h"))
        self.sw = QDoubleSpinBox()
        self.sh = QDoubleSpinBox()
        for s, n in ((self.sw, "Width"), (self.sh, "Height")):
            s.setRange(10, 100)
            s.setDecimals(1)
            s.setSuffix(" %")
            s.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            s.valueChanged.connect(self.on_spin)
            r = QHBoxLayout()
            r.addWidget(self.lab(n))
            r.addStretch()
            r.addWidget(s)
            cl.addLayout(r)
        cl.addWidget(self.lab("Area can be moved around the pad by dragging.", "hint"))
        self.info = self.lab("", "hint")
        cl.addWidget(self.info)
        cl.addSpacing(8)
        cl.addWidget(self.lab("Profiles", "h"))
        self.pgrid = QGridLayout()
        self.pgrid.setSpacing(8)
        cl.addLayout(self.pgrid)
        cl.addWidget(self.lab("Right-click a profile to delete it.", "hint"))
        cl.addStretch()
        h.addWidget(col)

        p2 = QWidget()
        v = QVBoxLayout(p2)
        v.setContentsMargins(8, 4, 8, 4)
        v.setSpacing(6)
        v.addWidget(self.lab("Behavior", "h"))
        v.addSpacing(6)
        v.addWidget(self.lab("Tap to click"))
        self.tap = Seg(["On", "Off"], 0 if c["tap"] else 1)
        self.tap.changed.connect(self.on_tap)
        v.addWidget(self.tap)
        v.addWidget(self.lab("On by default, if turned off your trackpad won't click nor drag when used.", "hint"))
        v.addSpacing(18)
        v.addWidget(self.lab("Appearance", "h"))
        v.addWidget(self.lab("Theme"))
        self.theme = Seg(["Dark", "Light"], 0 if c["theme"] == "dark" else 1)
        self.theme.changed.connect(self.on_theme)
        v.addWidget(self.theme)
        v.addSpacing(6)
        v.addWidget(self.lab("Color theme"))
        row = QHBoxLayout()
        row.setSpacing(10)
        self.dots = QButtonGroup(self)
        for i, col_ in enumerate(ACCENTS):
            d = QPushButton()
            d.setCheckable(True)
            d.setFixedSize(30, 30)
            d.setCursor(Qt.CursorShape.PointingHandCursor)
            d.setStyleSheet(f"QPushButton{{background:{col_};border-radius:15px;border:3px solid transparent;}}QPushButton:checked{{border:3px solid #9a9aa2;}}")
            self.dots.addButton(d, i)
            row.addWidget(d)
        row.addStretch()
        self.dots.button(c["accent"]).setChecked(True)
        self.dots.idClicked.connect(self.on_accent)
        v.addLayout(row)
        v.addWidget(self.lab("Alternative color for the app, pick to your taste.", "hint"))
        v.addSpacing(18)
        v.addWidget(self.lab("Keybinds", "h"))
        v.addWidget(self.lab("Toggle"))
        kr = QHBoxLayout()
        kr.setSpacing(8)
        self.keybtn = QPushButton(pretty(c["stop"]))
        self.keybtn.setObjectName("seg")
        self.keybtn.setMinimumWidth(180)
        self.keybtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.keybtn.clicked.connect(self.on_record)
        clr = QPushButton("Clear")
        clr.setObjectName("seg")
        clr.setCursor(Qt.CursorShape.PointingHandCursor)
        clr.clicked.connect(self.on_clear)
        kr.addWidget(self.keybtn)
        kr.addWidget(clr)
        kr.addStretch()
        v.addLayout(kr)
        v.addWidget(self.lab("Click, then hold up to 3 keys and let go to save. Press them anytime to turn Tabyam on or off, even while a game has focus.", "hint"))
        v.addStretch()

        self.stack = QStackedWidget()
        self.stack.addWidget(p1)
        self.stack.addWidget(p2)
        self.nav.idClicked.connect(self.stack.setCurrentIndex)
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(14)
        root.addWidget(side)
        root.addWidget(self.stack, 1)

        self.sched = QTimer(self)
        self.sched.setSingleShot(True)
        self.sched.setInterval(300)
        self.sched.timeout.connect(self.restart)
        self.ticker = QTimer(self)
        self.ticker.setInterval(500)
        self.ticker.timeout.connect(self.poll)
        self.ticker.start()

        self.load_pad()
        self.sync()
        self.rebuild_profiles()
        self.update_status()
        self.start_listener()
        self.splash = Splash(self, ac, pal)
        self.splash.setGeometry(self.rect())
        self.splash.hide()

    def lab(self, text, name=None):
        l = QLabel(text)
        l.setWordWrap(True)
        if name:
            l.setObjectName(name)
        return l

    def pal(self):
        return PAL[self.conf["theme"]]

    def load_pad(self):
        self.pad = None
        try:
            r = subprocess.run([PY, CORE, "-info"], capture_output=True, text=True, timeout=10)
            if r.returncode != 0:
                lines = r.stderr.strip().splitlines()
                self.err = lines[-1] if lines else "Touchpad not detected."
                return
            self.pad = json.loads(r.stdout)
        except Exception as ex:
            self.err = str(ex)
            return
        self.err = ""
        p = self.pad
        self.pw = p["w"] / p["rx"] if p["rx"] else float(p["w"])
        self.ph = p["h"] / p["ry"] if p["ry"] else float(p["h"])
        self.canvas.aspect = self.pw / self.ph

    def sync(self):
        a = self.canvas.area
        for s, val in ((self.sw, a[2]), (self.sh, a[3])):
            s.blockSignals(True)
            s.setValue(round(val * 100, 1))
            s.blockSignals(False)
        self.canvas.update()
        self.refresh()

    def refresh(self):
        if self.pad:
            x, y, w, h = self.canvas.area
            W, H = self.pad["w"], self.pad["h"]
            self.info.setText(f"X {int(x * W)}   Y {int(y * H)}\nW {int(w * W)}   H {int(h * H)}")
        else:
            self.info.setText("")
        self.update_strip()

    def update_strip(self):
        x, y, w, h = self.canvas.area
        pd = self.pad
        if pd and pd["rx"] and pd["ry"]:
            size = f"{w * pd['w'] / pd['rx']:.0f} × {h * pd['h'] / pd['ry']:.0f} mm"
        else:
            size = f"{w * 100:.0f} × {h * 100:.0f} %"
        tap = "On" if self.conf["tap"] else "Off"
        if self.proc:
            s = int(time.monotonic() - self.t0)
            run = f"Operating {s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"
        else:
            run = "Stopped"
        self.strip.setText(f"Area {size}   ·   Tap {tap}   ·   {run}")

    def on_drag(self):
        self.refresh()
        if self.proc:
            self.sched.start()

    def on_sized(self):
        self.presets.clear()
        self.sync()
        if self.proc:
            self.sched.start()

    def commit(self):
        a = self.canvas.area
        self.conf.update(x=a[0], y=a[1], w=a[2], h=a[3])
        save_conf(self.conf)
        self.refresh()
        if self.proc:
            self.sched.start()

    def on_spin(self):
        a = self.canvas.area
        a[2] = self.sw.value() / 100
        a[3] = self.sh.value() / 100
        a[0] = min(a[0], 1 - a[2])
        a[1] = min(a[1], 1 - a[3])
        self.presets.clear()
        self.canvas.update()
        self.commit()

    def on_preset(self, i):
        r = PRESETS[i][1]
        a = self.canvas.area
        if r is None:
            fw = fh = 1.0
        elif r == "q":
            fw = fh = 0.5
        else:
            k = (r[0] / r[1]) * self.ph / self.pw
            fw, fh = (1.0, 1 / k) if k >= 1 else (k, 1.0)
        cx, cy = a[0] + a[2] / 2, a[1] + a[3] / 2
        a[2], a[3] = fw, fh
        a[0] = clamp(cx - fw / 2, 0, 1 - fw)
        a[1] = clamp(cy - fh / 2, 0, 1 - fh)
        self.sync()
        self.commit()

    def rebuild_profiles(self):
        while self.pgrid.count():
            it = self.pgrid.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        names = list(self.conf["profiles"])
        for i, n in enumerate(names):
            b = QPushButton(n)
            b.setObjectName("seg")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _, n=n: self.load_profile(n))
            b.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            b.customContextMenuRequested.connect(lambda pos, n=n, b=b: self.prof_menu(n, b, pos))
            self.pgrid.addWidget(b, i // 2, i % 2)
        add = QPushButton("+ Save")
        add.setObjectName("seg")
        add.setCursor(Qt.CursorShape.PointingHandCursor)
        add.clicked.connect(self.save_profile)
        self.pgrid.addWidget(add, len(names) // 2, len(names) % 2)

    def save_profile(self):
        name, ok = QInputDialog.getText(self, "Save profile", "Name")
        name = name.strip()[:14]
        if not ok or not name:
            return
        a = self.canvas.area
        self.conf["profiles"][name] = {"x": a[0], "y": a[1], "w": a[2], "h": a[3], "tap": self.conf["tap"]}
        save_conf(self.conf)
        self.rebuild_profiles()

    def load_profile(self, n):
        d = self.conf["profiles"].get(n)
        if not d:
            return
        try:
            w = clamp(float(d["w"]), 0.1, 1.0)
            h = clamp(float(d["h"]), 0.1, 1.0)
            x = clamp(float(d["x"]), 0.0, 1 - w)
            y = clamp(float(d["y"]), 0.0, 1 - h)
        except Exception:
            return
        self.canvas.area[:] = [x, y, w, h]
        self.presets.clear()
        self.sync()
        self.on_tap(0 if d.get("tap", True) else 1)
        self.commit()

    def prof_menu(self, n, b, pos):
        m = QMenu(self)
        act = m.addAction("Delete")
        if m.exec(b.mapToGlobal(pos)) == act:
            self.conf["profiles"].pop(n, None)
            save_conf(self.conf)
            self.rebuild_profiles()

    def on_tap(self, i):
        self.tap.set(i)
        self.tap2.set(i)
        self.conf["tap"] = i == 0
        save_conf(self.conf)
        if self.proc and self.proc.poll() is None:
            self.proc.send_signal(signal.SIGUSR1 if self.conf["tap"] else signal.SIGUSR2)
        self.update_strip()

    def apply_style(self):
        ac = ACCENTS[self.conf["accent"]]
        pal = self.pal()
        QApplication.instance().setStyleSheet(sheet(ac, pal))
        self.setWindowIcon(make_icon(ac))
        self.canvas.accent = QColor(ac)
        self.canvas.pal = pal
        self.canvas.update()
        self.update_status()

    def on_accent(self, i):
        self.conf["accent"] = i
        save_conf(self.conf)
        self.apply_style()

    def on_theme(self, i):
        self.conf["theme"] = "dark" if i == 0 else "light"
        save_conf(self.conf)
        self.apply_style()

    def start_listener(self):
        self.stop_listener()
        if not self.conf["stop"]:
            return
        self.lis = QProcess(self)
        self.lis.readyReadStandardOutput.connect(self.lis_out)
        self.lis.finished.connect(self.lis_done)
        self.lis.start(PY, [CORE, "-listen", "-keys", *self.conf["stop"]])

    def stop_listener(self):
        l, self.lis = self.lis, None
        if l:
            l.kill()
            l.waitForFinished(500)
            l.deleteLater()

    def lis_out(self):
        if not self.lis:
            return
        for line in bytes(self.lis.readAllStandardOutput()).decode().splitlines():
            if line.strip() == "toggle":
                self.hotkey()

    def lis_done(self):
        l = self.lis
        self.lis = None
        if l is None:
            return
        msg = bytes(l.readAllStandardError()).decode().strip()
        if msg:
            self.err = msg.splitlines()[-1]
            self.update_status()
        l.deleteLater()

    def hotkey(self):
        self.go.setChecked(not self.go.isChecked())
        self.toggle()

    def on_record(self):
        if self.rec:
            self.cancel_record()
            return
        self.stop_listener()
        self.rec = QProcess(self)
        self.rec.readyReadStandardOutput.connect(self.rec_out)
        self.rec.finished.connect(self.rec_done)
        self.rec.start(PY, [CORE, "-record"])
        self.keybtn.setText("Press keys…")

    def rec_out(self):
        if not self.rec:
            return
        for line in bytes(self.rec.readAllStandardOutput()).decode().splitlines():
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d["done"]:
                self.conf["stop"] = d["keys"]
                save_conf(self.conf)
            else:
                self.keybtn.setText(pretty(d["keys"]) + " …")

    def rec_done(self):
        r = self.rec
        self.rec = None
        if r is None:
            return
        msg = bytes(r.readAllStandardError()).decode().strip()
        if msg:
            self.err = msg.splitlines()[-1]
            self.update_status()
        self.keybtn.setText(pretty(self.conf["stop"]))
        r.deleteLater()
        self.start_listener()

    def cancel_record(self):
        r, self.rec = self.rec, None
        if r:
            r.kill()
            r.waitForFinished(500)
            r.deleteLater()
        self.keybtn.setText(pretty(self.conf["stop"]))
        self.start_listener()

    def on_clear(self):
        self.cancel_record()
        self.conf["stop"] = []
        save_conf(self.conf)
        self.keybtn.setText(pretty([]))
        self.start_listener()

    def toggle(self):
        if self.go.isChecked():
            self.start_core()
        else:
            self.stop_core()
        self.update_status()

    def start_core(self):
        self.err = ""
        if self.pad is None:
            self.load_pad()
            self.sync()
            if self.pad is None:
                return
        x, y, w, h = self.canvas.area
        W, H = self.pad["w"], self.pad["h"]
        cmd = [PY, CORE, "-area", str(int(x * W)), str(int(y * H)), str(int(w * W)), str(int(h * H))]
        if not self.conf["tap"]:
            cmd.append("-notap")
        self.proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True)
        self.t0 = time.monotonic()

    def stop_core(self):
        p, self.proc = self.proc, None
        if p is None:
            return
        if p.poll() is None:
            p.send_signal(signal.SIGINT)
            try:
                p.wait(2)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
        if p.stderr:
            p.stderr.close()

    def restart(self):
        if self.proc:
            self.stop_core()
            self.start_core()
            self.update_status()

    def poll(self):
        p = self.proc
        if p and p.poll() is not None:
            msg = p.stderr.read().strip() if p.stderr else ""
            self.proc = None
            if msg:
                self.err = msg.splitlines()[-1]
            elif p.returncode not in (0, -2, 130):
                self.err = "And it just stopped. Flee the divine~"
            self.update_status()
        self.update_strip()

    def update_status(self):
        pal = self.pal()
        on = self.proc is not None
        self.go.setChecked(on)
        self.go.setText("Kill" if on else "Run")
        if on:
            self.status.setText("Operating")
            self.status.setStyleSheet(f"color: {pal['ok']}; font-weight: 700;")
        elif self.err:
            self.status.setText(self.err)
            self.status.setStyleSheet(f"color: {pal['err']};")
        else:
            self.status.setText("Stopped")
            self.status.setStyleSheet(f"color: {pal['mute']}; font-weight: 700;")
        self.devlabel.setText(self.pad["name"] if self.pad else "")
        self.update_strip()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        sp = getattr(self, "splash", None)
        if sp:
            sp.setGeometry(self.rect())

    def closeEvent(self, ev):
        self.cancel_record()
        self.stop_listener()
        self.stop_core()
        super().closeEvent(ev)


app = QApplication(sys.argv)
app.setStyle("Fusion")
app.setApplicationName("Tabyam")
app.setApplicationDisplayName("Tabyam")
app.setDesktopFileName("tabyam")
win = Window()
win.resize(1040, 700)
win.setMinimumSize(860, 620)
win.show()
win.splash.start()
sys.exit(app.exec())
