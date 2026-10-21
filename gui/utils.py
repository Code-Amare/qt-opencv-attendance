import sys
from pathlib import Path
import os
import aiohttp
from PyQt5.QtCore import Qt, QByteArray, QSize
from PyQt5.QtGui import QIcon, QPixmap, QPainter
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QToolButton


def resource_path(rel: str) -> Path:
    """Path to a bundled file: works from source and inside a PyInstaller exe."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / rel


def data_path(name: str) -> Path:
    """Writable per-user folder for files the app saves (survives updates)."""
    folder = Path(os.environ.get("APPDATA", Path.home())) / "FaceCall"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / name


# assets/FaceCall.ico (bundled with --add-data "assets;assets")
ICON_PATH = resource_path("assets/FaceCall.ico")

# Size (px) of the icon in the title bar. Change this number to resize it.
# The title bar is 48px tall, so keep it at 40 or less.
TITLE_ICON_SIZE = 32

DEFAULT_AVATAR_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <circle cx="128" cy="128" r="128" fill="#2f2c31"/>
  <circle cx="128" cy="100" r="44" fill="#9CA3AF"/>
  <path d="M40 216 C40 164 80 150 128 150 C176 150 216 164 216 216 A128 128 0 0 1 40 216 Z"
        fill="#9CA3AF"/>
</svg>
"""
TITLEBAR_QSS = """
#titlebar { background: #444444; }
#titlebar QLabel { color: #F8FAFC; font-weight: 400; }
#titlebar QToolButton { background: transparent; border: none; }
#titlebar QToolButton:hover { background: #334155; }
#titlebar QToolButton#closeBtn:hover { background: #E81123; }
"""


def icon_from_svg(svg_text, sizes=(16, 24, 32, 48, 64, 128, 256)):
    renderer = QSvgRenderer(QByteArray(svg_text.strip().encode("utf-8")))
    icon = QIcon()
    for s in sizes:
        pix = QPixmap(s, s)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        renderer.render(painter)
        painter.end()
        icon.addPixmap(pix)
    return icon


def app_icon():
    """The app icon: the image at assets/FaceCall.ico (no SVG involved)."""
    icon = QIcon(str(ICON_PATH))  # keeps every size stored inside the .ico
    if icon.isNull():
        print(f"Could not load app icon: {ICON_PATH}")
        return icon
    biggest = max((s.width() for s in icon.availableSizes()), default=0)
    if biggest < 256:
        print(
            f"Warning: {ICON_PATH.name} only goes up to {biggest}px, so it will "
            "look blurry. Rebuild it with make_icon.py (needs a 256px+ source)."
        )
    return icon


def _line_icon(inner, color="#F8FAFC", size=16):
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" '
        f'fill="none" stroke="{color}" stroke-width="1">{inner}</svg>'
    )
    return icon_from_svg(svg, sizes=(size, size * 2))


ICON_MIN = '<path d="M1 5.5 H9"/>'
ICON_MAX = '<rect x="1.5" y="1.5" width="7" height="7"/>'
ICON_RESTORE = (
    '<path d="M3 3 V1.5 H8.5 V7 H7"/><rect x="1.5" y="3" width="5.5" height="5.5"/>'
)
ICON_CLOSE = '<path d="M1.5 1.5 L8.5 8.5 M8.5 1.5 L1.5 8.5"/>'


class TitleBar(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window_ = window
        self.setObjectName("titlebar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(self.window_.TITLE_HEIGHT)
        self.setStyleSheet(TITLEBAR_QSS)
        self._drag = None

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 0, 0, 0)
        row.setSpacing(8)

        # app icon on the left of the title
        self.icon_lbl = QLabel()
        self.icon_lbl.setPixmap(app_icon().pixmap(TITLE_ICON_SIZE, TITLE_ICON_SIZE))
        row.addWidget(self.icon_lbl)

        self.title = QLabel(window.windowTitle())
        window.windowTitleChanged.connect(self.title.setText)  # stays in sync
        row.addWidget(self.title)
        row.addStretch()

        def make_btn(icon_inner, slot, name):
            b = QToolButton()
            b.setObjectName(name)
            b.setIcon(_line_icon(icon_inner))
            b.setIconSize(QSize(14, 14))
            b.setFixedSize(46, self.window_.TITLE_HEIGHT)
            b.clicked.connect(slot)
            row.addWidget(b)
            return b

        make_btn(ICON_MIN, window.showMinimized, "minBtn")
        self.max_btn = make_btn(ICON_MAX, self.toggle_max, "maxBtn")
        make_btn(ICON_CLOSE, window.close, "closeBtn")

    def toggle_max(self):
        w = self.window_
        if w.isMaximized():
            w.showNormal()
            self.max_btn.setIcon(_line_icon(ICON_MAX))
        else:
            w.showMaximized()
            self.max_btn.setIcon(_line_icon(ICON_RESTORE))

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = e.globalPos() - self.window_.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag is not None and e.buttons() & Qt.LeftButton:
            self.window_.move(e.globalPos() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None

    def mouseDoubleClickEvent(self, e):
        self.toggle_max()


def pixmap_from_bytes(data: bytes, size: int = 256):
    """Raster (png/jpg/webp/gif...) or SVG bytes -> QPixmap, or None if invalid."""
    head = data[:512].lstrip().lower()
    if head.startswith(b"<svg") or b"<svg" in head:
        renderer = QSvgRenderer(QByteArray(data))
        if not renderer.isValid():
            return None
        ds = renderer.defaultSize()
        h = int(size * ds.height() / ds.width()) if ds.width() else size
        pix = QPixmap(size, h)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        renderer.render(painter)
        painter.end()
        return pix

    pix = QPixmap()
    return pix if pix.loadFromData(data) else None


def default_avatar(size=128):
    return pixmap_from_bytes(DEFAULT_AVATAR_SVG.encode("utf-8"), size)


async def get_image(
    source: str, session: aiohttp.ClientSession = None, size: int = 256
):
    try:
        if source.lower().startswith(("http://", "https://")):
            if session is None:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as s:
                    async with s.get(source) as resp:
                        resp.raise_for_status()
                        data = await resp.read()
            else:
                async with session.get(source) as resp:
                    resp.raise_for_status()
                    data = await resp.read()
        else:
            with open(source, "rb") as f:
                data = f.read()
    except (aiohttp.ClientError, OSError, TimeoutError):
        return None

    return pixmap_from_bytes(data, size)
