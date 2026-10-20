from insightface.app import FaceAnalysis
import asyncio
import ctypes
import sys
from datetime import datetime
from string import Template

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
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
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
from utils import TitleBar, app_icon, default_avatar, get_image

# Windows groups taskbar buttons by this id. Without it, running as
# `python app.py` shows the Python icon instead of ours.
APP_USER_MODEL_ID = "facecall.app"

# ---------------------------------------------------------------- font sizes (px)
# Change these numbers to resize the text everywhere.
FONT = {
    "h1": 34,  # page titles
    "body": 18,  # default text (QLabel, radio/checkbox)
    "muted": 17,  # subtitles / secondary text
    "field": 16,  # form labels
    "subtle": 15,  # hints, ids
    "input": 18,  # text inputs
    "button": 18,  # buttons
    "message": 16,  # error / info messages under forms
    "table": 17,  # table cells
    "table_header": 14,  # table column headers
    "small_button": 16,  # buttons inside table rows
    "dialog": 17,  # message boxes
}

# ---------------------------------------------------------------- theme
# Colors match the web frontend tokens:
# background #121215 | surface #18181C | elevated #1F1F23 | subtle #222226
# foreground #E0E0E0 | muted #B0B0B5 | subtle #6B6B73
# primary #5B21B6 | primary-hover #6D28D9
# success #10B981 | warning #F59E0B | danger #EF4444 | info #3B82F6
STYLE = Template("""
QMainWindow, QWidget#central { background: #252525; }
QWidget { font-family: Poppins, "Segoe UI", sans-serif; }

QLabel { color: #E0E0E0; font-size: $bodypx; }
QLabel#h1 { font-size: $h1px; font-weight: 600; }
QLabel#muted { color: #B0B0B5; font-size: $mutedpx; }
QLabel#field { color: #B0B0B5; font-size: $fieldpx; }
QLabel#subtle { color: #6B6B73; font-size: $subtlepx; }

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
    font-size: $inputpx;
    selection-background-color: #5B21B6;
}
QLineEdit:focus { border: 1px solid #6D28D9; }

QPushButton {
    background: #5B21B6;
    color: #FFFFFF;
    border: none;
    border-radius: 2px;
    padding: 10px 18px;
    font-size: $buttonpx;
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

QListWidget {
    background: #18181C;
    color: #E0E0E0;
    border: 1px solid rgba(255, 255, 255, 25);
    border-radius: 2px;
    font-size: $bodypx;
    outline: 0;
}
QListWidget::item { padding: 10px 12px; }
QListWidget::item:hover { background: #1F1F23; }
QListWidget::item:selected { background: #2B2B36; color: #E0E0E0; }

QRadioButton, QCheckBox { color: #E0E0E0; font-size: $bodypx; spacing: 10px; }
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
    background: #1f1f1f;
    color: #E0E0E0;
    border: 1px solid rgba(255, 255, 255, 25);
    border-radius: 2px;
    font-size: $tablepx;
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
    font-size: $table_headerpx;
    font-weight: 500;
}

QScrollBar:vertical { background: #18181C; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #2B2B36; min-height: 24px; border-radius: 2px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }


QDialog, QMessageBox { background: #18181C; }
QMessageBox QLabel { color: #E0E0E0; font-size: $dialogpx; min-width: 280px; }
QMessageBox QPushButton { min-width: 80px; }
""").substitute({f"{k}px": f"{v}px" for k, v in FONT.items()})

MESSAGE_COLORS = {
    "error": "#EF4444",
    "warn": "#F59E0B",
    "ok": "#10B981",
    "info": "#3B82F6",
}


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


def _video_capture(index):
    """Same backend everywhere so scanned indices match the ones we open.
    DirectShow on Windows is much faster than MSMF."""
    if sys.platform == "win32":
        return cv2.VideoCapture(index, cv2.CAP_DSHOW)
    return cv2.VideoCapture(index)


async def open_capture(index):
    """Open the camera in a worker thread so the UI (and spinner) stays responsive."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _video_capture, index)


def probe_cameras(max_index=6):
    """Indices that open AND deliver a frame. Blocking: run in a worker thread."""
    found = []
    for i in range(max_index):
        cap = _video_capture(i)
        if cap.isOpened():
            ok, _ = cap.read()
            if ok:
                found.append(i)
        cap.release()
    return found


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

    def clear_frame(self):
        self._pixmap = None
        self.clear()

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


class CameraSelectPage(CameraPage):
    """Shown right after login: detect cameras, preview one, pick it.
    Sets window.CAMERA_INDEX and emits `confirmed` on Continue."""

    confirmed = pyqtSignal()

    def __init__(self, window):
        super().__init__(window)
        self._token = 0  # ignores stale previews when the user clicks fast

        title = QLabel("Select camera")
        title.setObjectName("h1")
        subtitle = QLabel("Choose the camera to use for face recognition.")
        subtitle.setObjectName("muted")

        self.list = QListWidget()
        self.list.setFixedWidth(220)
        self.list.currentRowChanged.connect(self.on_select)

        self.scan_btn = QPushButton("Rescan")
        self.scan_btn.setObjectName("secondary")
        self.scan_btn.setCursor(Qt.PointingHandCursor)
        self.scan_btn.clicked.connect(self.scan)

        self.camera_label.setMinimumSize(480, 360)
        self.status = QLabel("")
        self.status.setObjectName("muted")

        self.continue_btn = QPushButton("Continue")
        self.continue_btn.setCursor(Qt.PointingHandCursor)
        self.continue_btn.setEnabled(False)
        self.continue_btn.clicked.connect(self.on_continue)

        left = QVBoxLayout()
        left.addWidget(self.list, 1)
        left.addWidget(self.scan_btn)

        right = QVBoxLayout()
        right.addWidget(self.camera_label, 1)
        right.addWidget(self.status)
        right.addWidget(self.continue_btn)

        body = QHBoxLayout()
        body.setSpacing(20)
        body.addLayout(left)
        body.addLayout(right, 1)

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 30, 40, 30)
        root.setSpacing(6)
        root.addWidget(title)
        root.addWidget(subtitle)
        root.addSpacing(16)
        root.addLayout(body, 1)

    # ---- entry point (called by the window after login) ----
    def begin(self):
        self.scan()

    # ---- scanning ----
    @asyncSlot()
    async def scan(self):
        self._stop_preview()
        self.list.clear()
        self.camera_label.clear_frame()
        self.continue_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.status.setText("Scanning for cameras...")

        loop = asyncio.get_running_loop()
        found = await loop.run_in_executor(None, probe_cameras)

        for i in found:
            item = QListWidgetItem(f"Camera {i}")
            item.setData(Qt.UserRole, i)
            self.list.addItem(item)

        self.scan_btn.setEnabled(True)
        if not found:
            self.status.setText("No cameras found. Plug one in and press Rescan.")
            return
        self.status.setText(f"Found {len(found)} camera(s).")
        current = self.window_.CAMERA_INDEX
        self.list.setCurrentRow(found.index(current) if current in found else 0)

    # ---- preview ----
    @asyncSlot(int)
    async def on_select(self, row):
        self._stop_preview()
        self.continue_btn.setEnabled(False)
        if row < 0:
            return
        index = self.list.item(row).data(Qt.UserRole)
        token = self._token

        cap = await open_capture(index)
        if token != self._token or not cap.isOpened():  # user moved on / failed
            cap.release()
            if token == self._token:
                self.status.setText(f"Unable to open camera {index}.")
            return
        self.cap = cap
        self.status.setText(f"Camera {index}")
        self.continue_btn.setEnabled(True)
        self.timer.start(30)

    def cam_feed(self):
        frame = self.read_frame()
        if frame is not None:
            self.update_frame(frame)

    def _stop_preview(self):
        self._token += 1
        self.stop_camera()

    # ---- continue ----
    def on_continue(self):
        item = self.list.currentItem()
        if item is None:
            return
        self.window_.CAMERA_INDEX = item.data(Qt.UserRole)
        self._stop_preview()
        self.confirmed.emit()


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

    def _finish(self, data, session, require_staff):
        if "tokens" not in data or "user" not in data:
            return "error", data.get("error") or "Login failed"
        if require_staff and not data["user"].get("is_staff"):
            return "error", "This app is only for admin users"
        self.add_tokens(data, session)
        return "ok", ""

    async def _post(self, session, url, payload):
        try:
            async with session.post(url, json=payload) as resp:
                try:
                    data = await resp.json()
                except aiohttp.ContentTypeError:
                    data = {}
                return resp.status, data
        except aiohttp.ClientError:
            return None, {}

    async def login(self, username_or_email, password, session, require_staff=True):
        status, data = await self._post(
            session,
            "users/login/gui/",
            {"username_or_email": username_or_email, "password": password},
        )
        if status is None:
            return "error", "Server error"
        if status >= 400:
            return "error", data.get("error") or "Login failed"

        # 2FA step: a code was emailed. This is info, not an error.
        if data.get("twofa_required"):
            return "code", data.get("detail") or data.get("error") or (
                "A login code has been sent to your email."
            )
        return self._finish(data, session, require_staff)

    async def verify_code(self, username_or_email, code, session, require_staff=True):
        status, data = await self._post(
            session,
            "users/login/verify/",
            {"username_or_email": username_or_email, "code": code},
        )
        if status is None:
            return "error", "Server error"
        if status >= 400:
            return "error", data.get("error") or "Verification failed"
        return self._finish(data, session, require_staff)

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
        self.awaiting_code = False

        title = QLabel("Sign in")
        title.setObjectName("h1")
        subtitle = QLabel(f"Access your {self.window_.PRODUCT_NAME} workspace.")
        subtitle.setObjectName("muted")

        self.user_label = QLabel("Username or email")
        self.user_label.setObjectName("field")
        self.username_or_email = QLineEdit()

        self.pass_label = QLabel("Password")
        self.pass_label.setObjectName("field")
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

        # verification code (hidden until the server asks for it)
        self.code_label = QLabel("Verification code")
        self.code_label.setObjectName("field")
        self.code = QLineEdit()
        self.code.setPlaceholderText("Enter the code from your email")

        self.message = QLabel("")
        self.message.setWordWrap(True)

        self.login_btn = QPushButton("Login")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self.on_submit)

        self.back_btn = QPushButton("Back")
        self.back_btn.setObjectName("secondary")
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.reset_to_credentials)

        for field in (self.username_or_email, self.password, self.code):
            field.returnPressed.connect(self.on_submit)

        form = QWidget()
        form.setFixedWidth(380)
        fl = QVBoxLayout(form)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(6)
        fl.addWidget(title)
        fl.addWidget(subtitle)
        fl.addSpacing(24)
        fl.addWidget(self.user_label)
        fl.addWidget(self.username_or_email)
        fl.addSpacing(8)
        fl.addWidget(self.pass_label)
        fl.addWidget(self.password)
        fl.addWidget(self.code_label)
        fl.addWidget(self.code)
        fl.addSpacing(8)
        fl.addWidget(self.message)
        fl.addWidget(self.login_btn)
        fl.addWidget(self.back_btn)

        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(form, alignment=Qt.AlignHCenter)
        layout.addStretch()

        self.reset_to_credentials()

    # ---- helpers ----
    def set_message(self, text, kind="error"):
        color = MESSAGE_COLORS.get(kind, MESSAGE_COLORS["error"])
        self.message.setStyleSheet(f"color: {color}; font-size: {FONT['message']}px;")
        self.message.setText(text)

    def _set_step(self, awaiting_code):
        self.awaiting_code = awaiting_code
        for w in (
            self.user_label,
            self.username_or_email,
            self.pass_label,
            self.password,
        ):
            w.setVisible(not awaiting_code)
        for w in (self.code_label, self.code, self.back_btn):
            w.setVisible(awaiting_code)
        self.login_btn.setText("Verify" if awaiting_code else "Login")
        (self.code if awaiting_code else self.username_or_email).setFocus()

    def reset_to_credentials(self):
        self.code.clear()
        self.set_message("")
        self._set_step(False)

    def toggle_password(self):
        if self.password.echoMode() == QLineEdit.Password:
            self.password.setEchoMode(QLineEdit.Normal)
            self.toggle_action.setIcon(self.icon_hide)
            self.toggle_action.setToolTip("Hide password")
        else:
            self.password.setEchoMode(QLineEdit.Password)
            self.toggle_action.setIcon(self.icon_show)
            self.toggle_action.setToolTip("Show password")

    # ---- submit ----
    @asyncSlot()
    async def on_submit(self):
        self.set_message("")
        auth, win = self.window_.auth, self.window_
        win.show_loader()
        try:
            if self.awaiting_code:
                status, msg = await auth.verify_code(
                    self.username_or_email.text().strip(),
                    self.code.text().strip(),
                    win.session,
                    win.REQUIRE_STAFF,
                )
            else:
                status, msg = await auth.login(
                    self.username_or_email.text().strip(),
                    self.password.text(),
                    win.session,
                    win.REQUIRE_STAFF,
                )
        finally:
            win.hide_loader()

        if status == "ok":
            self.password.clear()
            self.reset_to_credentials()
            self.login_successful.emit()
        elif status == "code":
            self._set_step(True)
            self.set_message(msg, "info")  # info, not error
        else:
            self.set_message(msg, "error")


# -------------------------------------------------------------- window
class BaseWindow(QMainWindow):
    """Frameless window with title bar, page stack, loader overlay, auth,
    HTTP session and the face model. Apps subclass it and implement
    build_pages() and on_login_successful().

    Flow: login -> camera select page -> on_login_successful()."""

    PRODUCT_NAME = "FaceCall"
    BASE_URL = "https://localhost:8000/api/"
    SIMILARITY_THRESHOLD = 0.50
    CAMERA_INDEX = 1  # default; overwritten by the camera select page
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
        self.setWindowIcon(app_icon())

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
        self.camera_select_page = self.add_page(CameraSelectPage(self))

        # login -> camera select -> app's own on_login_successful()
        self.login_page.login_successful.connect(self.show_camera_select)
        self.camera_select_page.confirmed.connect(self.on_login_successful)

    def show_camera_select(self):
        self.show_page(self.camera_select_page)
        self.camera_select_page.begin()

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
    # Must happen before the QApplication / first window is created.
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)

    # Sharp icons/pixmaps on scaled (125%/150%) Windows displays.
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(app_icon())

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = window_cls()
    window.show()

    with loop:
        loop.run_until_complete(_serve(window))
