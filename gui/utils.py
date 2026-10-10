from PyQt5.QtCore import Qt, QByteArray
from PyQt5.QtGui import QIcon, QPixmap, QPainter
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QToolButton

APP_ICON_SVG  = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%">
  <defs>
    <!-- Dark Tech Background Gradient -->
    <linearGradient id="bgGlow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0F172A"/>
      <stop offset="100%" stop-color="#1E293B"/>
    </linearGradient>

    <!-- Scan Reticle & Face Glow -->
    <linearGradient id="cyanCyan" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#06B6D4"/>
      <stop offset="100%" stop-color="#3B82F6"/>
    </linearGradient>

    <!-- Checkmark Success Green -->
    <linearGradient id="greenCheck" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#10B981"/>
      <stop offset="100%" stop-color="#059669"/>
    </linearGradient>

    <!-- Subtle Drop Shadow -->
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="8" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>

  <!-- App Background (Rounded Square / App Tile) -->
  <rect x="32" y="32" width="448" height="448" rx="96" fill="url(#bgGlow)" stroke="#334155" stroke-width="4"/>

  <!-- Camera / Recognition Reticle (Corners) -->
  <g stroke="url(#cyanCyan)" stroke-width="12" stroke-linecap="round" fill="none">
    <!-- Top-Left Corner -->
    <path d="M 120 180 V 140 A 20 20 0 0 1 140 120 H 180" />
    <!-- Top-Right Corner -->
    <path d="M 332 120 H 372 A 20 20 0 0 1 392 140 V 180" />
    <!-- Bottom-Left Corner -->
    <path d="M 120 332 V 372 A 20 20 0 0 0 140 392 H 180" />
    <!-- Bottom-Right Corner -->
    <path d="M 332 392 H 372 A 20 20 0 0 0 392 372 V 332" />
  </g>

  <!-- Stylized Biometric Face Contour -->
  <g fill="none" stroke="#F8FAFC" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" opacity="0.95">
    <!-- Head Outline -->
    <path d="M 196 220 C 196 160, 316 160, 316 220 C 316 270, 290 310, 256 320 C 222 310, 196 270, 196 220 Z" />
    <!-- Eyes -->
    <circle cx="226" cy="215" r="7" fill="#F8FAFC"/>
    <circle cx="286" cy="215" r="7" fill="#F8FAFC"/>
    <!-- Nose Line -->
    <path d="M 256 220 V 245 H 250" stroke-width="8"/>
    <!-- Subtle Smile / Mouth -->
    <path d="M 236 270 Q 256 282 276 270" stroke-width="8"/>
  </g>

  <!-- Anti-Spoofing / Verified Attendance Badge (Bottom Right Checkmark) -->
  <g filter="url(#glow)">
    <circle cx="360" cy="360" r="52" fill="url(#greenCheck)" stroke="#0F172A" stroke-width="8"/>
    <path d="M 336 360 L 352 376 L 384 344" fill="none" stroke="#FFFFFF" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
</svg>

"""

TITLEBAR_QSS = """
#titlebar { background: #3b0762;}
#titlebar QLabel { color: #F8FAFC; font-weight: semi-bold; }
#titlebar QToolButton { background: transparent; color: #F8FAFC; border: none; }
#titlebar QToolButton:hover { background: #334155; }
"""


def icon_from_svg(svg_text=APP_ICON_SVG, sizes=(16, 24, 32, 48, 64, 128, 256)):
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


class TitleBar(QWidget):
    def __init__(self, window, height=58):
        super().__init__()
        self.window_ = window
        self.setObjectName("titlebar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(height)
        self.setStyleSheet(TITLEBAR_QSS)
        self._drag = None

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 0, 0, 0)

        self.title = QLabel(window.windowTitle())
        window.windowTitleChanged.connect(self.title.setText)  # stays in sync
        row.addWidget(self.title)
        row.addStretch()

        for text, slot in (("–", window.showMinimized),
                           ("☐", self.toggle_max),
                           ("✕", window.close)):
            b = QToolButton()
            b.setText(text)
            b.setFixedSize(46, height)
            b.clicked.connect(slot)
            row.addWidget(b)

    def toggle_max(self):
        w = self.window_
        w.showNormal() if w.isMaximized() else w.showMaximized()

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