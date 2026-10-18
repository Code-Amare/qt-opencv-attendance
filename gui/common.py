from insightface.app import FaceAnalysis
import asyncio
import sys
from datetime import datetime

import aiohttp
import cv2
from PyQt5.QtCore import QPointF, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import (
    QColor,
    QIcon,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt5.QtWidgets import (
    QApplication,
    QGraphicsBlurEffect,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from pyqtspinner.spinner import WaitingSpinner
from qasync import QEventLoop, asyncSlot

from anti_spoof import is_face_real
from utils import TitleBar, default_avatar, get_image, icon_from_svg

# ---------------------------------------------------------------- theme
# Colors match the web frontend tokens:
# background #121215 | surface #18181C | elevated #1F1F23 | subtle #222226
# foreground #E0E0E0 | muted #B0B0B5 | subtle #6B6B73
# primary #5B21B6 | primary-hover #6D28D9
# success #10B981 | warning #F59E0B | danger #EF4444 | info #3B82F6
STYLE = """
QMainWindow, QWidget#central { background: #121215; }
QWidget { font-family: Poppins, "Segoe UI", sans-serif; }

QLabel { color: #E0E0E0; font-size: 16px; }
QLabel#h1 { font-size: 28px; font-weight: 600; }
QLabel#muted { color: #B0B0B5; font-size: 15px; }
QLabel#field { color: #B0B0B5; font-size: 14px; }
QLabel#subtle { color: #6B6B73; font-size: 13px; }

QFrame#panel {
    background: #18181C;
    border: 1px solid rgba(255, 255, 255, 25);
    border-radius: 2px;
}

QLineEdit {
    background: #1F1F23;
    color: #E0E0E0;
    border: 1px solid rgba(255, 255, 255, 25);
    border-radius: 2px;
    padding: 10px 12px;
    font-size: 16px;
    selection-background-color: #5B21B6;
}
QLineEdit:focus { border: 1px solid #6D28D9; }

QPushButton {
    background: #5B21B6;
    color: #FFFFFF;
    border: none;
    border-radius: 2px;
    padding: 10px 18px;
    font-size: 16px;
    font-weight: 500;
}
QPushButton:hover { background: #6D28D9; }
QPushButton:disabled { background: #222226; color: #6B6B73; }
QPushButton#secondary {
    background: transparent;
    color: #E0E0E0;
    border: 1px solid rgba(255, 255, 255, 25);
}
QPushButton#secondary:hover { background: #1F1F23; }

QRadioButton, QCheckBox { color: #E0E0E0; font-size: 16px; spacing: 10px; }
QRadioButton:disabled, QCheckBox:disabled { color: #6B6B73; }
QRadioButton::indicator {
    width: 16px; height: 16px; border-radius: 9px;
    border: 1px solid rgba(255, 255, 255, 60); background: #1F1F23;
}
QRadioButton::indicator:checked {
    border: 1px solid #6D28D9;
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
        stop:0 #E0E0E0, stop:0.4 #E0E0E0, stop:0.45 #5B21B6, stop:1 #5B21B6);
}
QCheckBox::indicator {
    width: 16px; height: 16px; border-radius: 2px;
    border: 1px solid rgba(255, 255, 255, 60); background: #1F1F23;
}
QCheckBox::indicator:checked { border: 1px solid #6D28D9; background: #5B21B6; }
QCheckBox::indicator:disabled { background: #18181C; }

QTableWidget, QTableView {
    background: #18181C;
    color: #E0E0E0;
    border: 1px solid rgba(255, 255, 255, 25);
    border-radius: 2px;
    font-size: 15px;
    outline: 0;
}
QTableWidget::item, QTableView::item {
    padding: 8px 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 12);
}
QTableWidget::item:hover, QTableView::item:hover { background: #1F1F23; }
QTableWidget::item:selected, QTableView::item:selected {
    background: #2B2B36;
    color: #E0E0E0;
}
QHeaderView::section {
    background: #18181C;
    color: #6B6B73;
    border: none;
    border-bottom: 1px solid rgba(255, 255, 255, 25);
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 500;
}

QScrollBar:vertical { background: #18181C; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #2B2B36; min-height: 24px; border-radius: 2px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""

MESSAGE_COLORS = {"error": "#EF4444", "warn": "#F59E0B", "ok": "#10B981"}


# -------------------------------------------------------------- helpers
def fmt_dt(value):
    """ISO string from the API -> local 'Oct 18, 09:30'."""
    if not value:
        return "—"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%b %d, %H:%M")
    except ValueError:
        return str(value)


def eye_icon(slashed=False, color="#B0B0B5"):
    """Draw an eye icon (slashed = password is visible)."""
    pix = QPixmap(32, 32)
    pix.fill(Qt.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    pen = QPen(QColor(color))
    pen.setWidthF(2.4)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)

    path = QPainterPath()
    path.moveTo(3, 16)
    path.quadTo(16, 3, 29, 16)
    path.quadTo(16, 29, 3, 16)
    p.drawPath(path)

    p.setBrush(QColor(color))
    p.drawEllipse(QPointF(16, 16), 4, 4)

    if slashed:
        p.setBrush(Qt.NoBrush)
        p.drawLine(6, 27, 26, 5)

    p.end()
    return QIcon(pix)


def frame_to_pixmap(frame):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
    return QPixmap.fromImage(image.copy())


def largest_face(faces):
    """The biggest face in the frame, or None."""
    if not faces:
        return None
    return max(
        faces,
        key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
    )


def draw_box(display, bbox, text="", color=(0, 255, 0)):
    x1, y1, x2, y2 = [int(v) for v in bbox]
    cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
    if text:
        cv2.putText(
            display,
            text,
            (x1, max(y1 - 10, 25)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2,
        )


async def open_capture(index):
    """Open the camera in a worker thread so the UI (and spinner) stays responsive."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, cv2.VideoCapture, index)


# ------------------------------------------------------------- widgets
class VideoLabel(QLabel):
    def __init__(self):
        super().__init__()
        self._pixmap = None
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

    def set_frame(self, pixmap):
        self._pixmap = pixmap
        self._rescale()

    def show_frame(self, frame):
        """Show an OpenCV (BGR) frame."""
        self.set_frame(frame_to_pixmap(frame))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self):
        if self._pixmap:
            self.setPixmap(
                self._pixmap.scaled(
                    self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )


class CameraPage(QWidget):
    """Base for every page with a live camera: owns the capture, the timer
    and the video label. Subclasses implement cam_feed()."""

    def __init__(self, window):
        super().__init__()
        self.window_ = window
        self.cap = None

        self.camera_label = VideoLabel()
        self.camera_label.setMinimumSize(640, 480)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.cam_feed)

    async def start_camera(self):
        self.cap = await open_capture(self.window_.CAMERA_INDEX)
        if not self.cap.isOpened():
            self.camera_label.setText("Unable to open camera")
            return False
        self.timer.start(30)
        return True

    def stop_camera(self):
        self.timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None

    def read_frame(self):
        if self.cap is None:
            return None
        ok, frame = self.cap.read()
        return frame if ok else None

    def update_frame(self, frame):
        self.camera_label.show_frame(frame)

    def is_spoof(self, frame, display, bbox):
        """Draws a red box + label on `display` and returns True when the
        face is not real. Always False when anti-spoofing is disabled."""
        if not self.window_.ENABLE_ANTI_SPOOFING:
            return False
        label, confidence = is_face_real(frame, [int(v) for v in bbox])
        if label == "Real":
            return False
        draw_box(display, bbox, f"{label} {confidence * 100:.1f}%", (0, 0, 255))
        return True

    def cam_feed(self):
        raise NotImplementedError


# ---------------------------------------------------------------- auth
class AuthContext:
    def __init__(self):
        self.id = None
        self.username = ""
        self.email = ""
        self.first_name = ""
        self.last_name = ""
        self.access = ""
        self.refresh = ""
        self.csrf = ""
        self.isAuthenticated = False
        self.profile_pic_url = ""
        self.profile_pic = None

    async def get_profile_pic(self):
        pix = None
        if self.profile_pic_url:
            pix = await get_image(self.profile_pic_url)
        self.profile_pic = pix or default_avatar()

    def add_tokens(self, data, session):
        tokens = data["tokens"]
        self.access = tokens["access"]
        self.refresh = tokens["refresh"]
        self.csrf = tokens["csrf"]
        self.isAuthenticated = True

        user = data["user"]
        self.id = user["id"]
        self.username = user["username"]
        self.email = user["email"]
        self.first_name = user["first_name"]
        self.last_name = user["last_name"]
        self.profile_pic_url = user.get("profile_picture") or ""

        self.update_headers(session)

    async def login(self, username_or_email, password, session, require_staff=True):
        try:
            async with session.post(
                "users/login/",
                json={
                    "username_or_email": username_or_email,
                    "password": password,
                },
            ) as resp:
                try:
                    data = await resp.json()
                except aiohttp.ContentTypeError:
                    data = {}
                if resp.status >= 400:
                    return False, data.get("error") or "Login failed"
        except aiohttp.ClientError:
            return False, "Server error"

        # e.g. two-factor: a login link was emailed, no tokens yet
        if "tokens" not in data:
            return False, data.get("error") or data.get("detail") or "Login failed"

        if require_staff and not data.get("user", {}).get("is_staff"):
            return False, "This app is only for admin users"

        self.add_tokens(data, session)
        return True, ""

    async def refresh_tokens(self, session):
        try:
            async with session.post(
                "users/refresh/", json={"refresh": self.refresh}
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except aiohttp.ClientError:
            self.logout()
            return False
        self.add_tokens(data, session)
        return True

    def logout(self):
        self.access = ""
        self.refresh = ""
        self.csrf = ""
        self.isAuthenticated = False

    def get_user(self):
        if not self.isAuthenticated:
            return None
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
        }

    def update_headers(self, session):
        session.headers.update(
            {
                "Authorization": f"Bearer {self.access}" if self.access else "",
                "X-CSRFToken": self.csrf,
            }
        )


class LoginPage(QWidget):
    login_successful = pyqtSignal()

    def __init__(self, window):
        super().__init__()
        self.window_ = window

        title = QLabel("Sign in")
        title.setObjectName("h1")
        subtitle = QLabel(f"Access your {self.window_.PRODUCT_NAME} workspace.")
        subtitle.setObjectName("muted")

        user_label = QLabel("Username or email")
        user_label.setObjectName("field")
        self.username_or_email = QLineEdit()

        pass_label = QLabel("Password")
        pass_label.setObjectName("field")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)

        # eye icon inside the password field
        self.icon_show = eye_icon(slashed=False)
        self.icon_hide = eye_icon(slashed=True)
        self.toggle_action = self.password.addAction(
            self.icon_show, QLineEdit.TrailingPosition
        )
        self.toggle_action.setToolTip("Show password")
        self.toggle_action.triggered.connect(self.toggle_password)

        self.error_message = QLabel("")
        self.error_message.setWordWrap(True)
        self.error_message.setStyleSheet(
            f"color: {MESSAGE_COLORS['error']}; font-size: 14px;"
        )

        self.login_btn = QPushButton("Login")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self.on_login_click)
        self.username_or_email.returnPressed.connect(self.on_login_click)
        self.password.returnPressed.connect(self.on_login_click)

        form = QWidget()
        form.setFixedWidth(380)
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(6)
        form_layout.addWidget(title)
        form_layout.addWidget(subtitle)
        form_layout.addSpacing(24)
        form_layout.addWidget(user_label)
        form_layout.addWidget(self.username_or_email)
        form_layout.addSpacing(8)
        form_layout.addWidget(pass_label)
        form_layout.addWidget(self.password)
        form_layout.addSpacing(8)
        form_layout.addWidget(self.error_message)
        form_layout.addWidget(self.login_btn)

        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(form, alignment=Qt.AlignHCenter)
        layout.addStretch()

    def toggle_password(self):
        if self.password.echoMode() == QLineEdit.Password:
            self.password.setEchoMode(QLineEdit.Normal)
            self.toggle_action.setIcon(self.icon_hide)
            self.toggle_action.setToolTip("Hide password")
        else:
            self.password.setEchoMode(QLineEdit.Password)
            self.toggle_action.setIcon(self.icon_show)
            self.toggle_action.setToolTip("Show password")

    @asyncSlot()
    async def on_login_click(self):
        self.error_message.setText("")
        self.window_.show_loader()
        try:
            ok, msg = await self.window_.auth.login(
                self.username_or_email.text(),
                self.password.text(),
                self.window_.session,
                self.window_.REQUIRE_STAFF,
            )
        finally:
            self.window_.hide_loader()
        if ok:
            self.password.clear()
            self.login_successful.emit()
        else:
            self.error_message.setText(msg)


# -------------------------------------------------------------- window
class BaseWindow(QMainWindow):
    """Frameless window with title bar, page stack, loader overlay, auth,
    HTTP session and the face model. Apps subclass it and implement
    build_pages() and on_login_successful()."""

    PRODUCT_NAME = "FaceCall"
    BASE_URL = "https://localhost:8000/api/"
    SIMILARITY_THRESHOLD = 0.50
    CAMERA_INDEX = 0
    STREAK_THRESHOLD = 20
    ENABLE_ANTI_SPOOFING = True
    REQUIRE_STAFF = True
    TITLE_HEIGHT = 48

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.closed = asyncio.Event()

        self.auth = AuthContext()
        self.session = None  # created in run()

        self.face_app = FaceAnalysis(
            name="buffalo_l",
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        self.face_app.prepare(ctx_id=0, det_size=(640, 640))

        self.setGeometry(0, 0, 1280, 720)
        self.setWindowTitle(self.PRODUCT_NAME)
        self.setWindowIcon(icon_from_svg())

        self._build_shell()
        self.build_pages()
        self.setStyleSheet(STYLE)
        self.center()

    # ---- to implement in each app ----
    def build_pages(self):
        raise NotImplementedError

    def on_login_successful(self):
        raise NotImplementedError

    # ---- shell ----
    def _build_shell(self):
        container = QWidget()
        container.setObjectName("central")
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(TitleBar(self))
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        self.overlay = QWidget(container)
        self.overlay.setObjectName("overlay")
        self.overlay.setAttribute(Qt.WA_StyledBackground, True)
        self.overlay.setStyleSheet("#overlay { background: rgba(18, 18, 21, 120); }")
        self.overlay.hide()

        self.spinner = WaitingSpinner(
            self.overlay,
            roundness=100.0,
            fade=80.0,
            radius=20,
            lines=20,
            line_length=10,
            line_width=4,
            speed=1.0,
            color=QColor(109, 40, 217),
        )

        self.login_page = self.add_page(LoginPage(self))
        self.login_page.login_successful.connect(self.on_login_successful)

    def add_page(self, page):
        self.stack.addWidget(page)
        return page

    def show_page(self, page):
        self.stack.setCurrentWidget(page)

    # ---- loader ----
    def _layout_overlay(self):
        rect = self.centralWidget().rect()
        self.overlay.setGeometry(
            0, self.TITLE_HEIGHT, rect.width(), rect.height() - self.TITLE_HEIGHT
        )
        self.spinner.move(
            (self.overlay.width() - self.spinner.width()) // 2,
            (self.overlay.height() - self.spinner.height()) // 2,
        )

    def show_loader(self):
        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(2)

        self.stack.setGraphicsEffect(blur)
        self.stack.setEnabled(False)

        self._layout_overlay()
        self.overlay.show()
        self.overlay.raise_()
        self.spinner.start()

    def hide_loader(self):
        self.spinner.stop()
        self.overlay.hide()
        self.stack.setGraphicsEffect(None)
        self.stack.setEnabled(True)

    # ---- window ----
    def center(self):
        geo = self.frameGeometry()
        geo.moveCenter(QApplication.primaryScreen().availableGeometry().center())
        self.move(geo.topLeft())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.overlay.isVisible():
            self._layout_overlay()

    def closeEvent(self, event):
        for i in range(self.stack.count()):
            page = self.stack.widget(i)
            if isinstance(page, CameraPage):
                page.stop_camera()
        self.closed.set()
        event.accept()


# ---------------------------------------------------------------- run
async def _serve(window):
    window.session = aiohttp.ClientSession(
        base_url=window.BASE_URL,
        headers={"Authorization": "", "X-CSRFToken": ""},
    )
    await window.closed.wait()
    await window.session.close()


def run(window_cls):
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = window_cls()
    window.show()

    with loop:
        loop.run_until_complete(_serve(window))
