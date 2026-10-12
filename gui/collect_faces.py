from insightface.app import FaceAnalysis
import sys
import time
import numpy as np
import asyncio
import cv2
import aiohttp
from qasync import QEventLoop, asyncSlot
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QGraphicsBlurEffect,
    QStackedWidget,
    QLabel,
    QPushButton,
    QMessageBox,
    QShortcut,
    QTableView,
    QAbstractItemView,
    QSizePolicy
)
from pyqtspinner.spinner import WaitingSpinner
from PyQt5.QtGui import QColor, QKeySequence, QImage, QPixmap
from PyQt5.QtCore import Qt, pyqtSignal, QAbstractTableModel, QModelIndex, QTimer
from utils import TitleBar, icon_from_svg, get_image, default_avatar
from anti_spoof import is_face_real

# Helper Classes


async def open_capture(index):
    """Open the camera in a worker thread so the UI (and spinner) stays responsive."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, cv2.VideoCapture, index)


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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self):
        if self._pixmap:
            self.setPixmap(self._pixmap.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))


# dashboard user table
class UserModel(QAbstractTableModel):
    HEADERS = ["Id", "First Name", "Last Name", "Face Status", "Actions"]

    def __init__(self):
        super().__init__()
        self._users: list[dict] = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._users)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        user = self._users[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return user["id"]
            if col == 1:
                return user["first_name"]
            if col == 2:
                return user["last_name"]
            if col == 3:
                return "Enrolled" if user.get("face_embeddings") else "Not enrolled"
            return ""

        if role == Qt.TextAlignmentRole:
            return int(Qt.AlignCenter)

        return None

    def set_users(self, users):
        self.beginResetModel()
        self._users = users
        self.endResetModel()

    def user_at(self, row):
        return self._users[row]


class ApiError(Exception):
    pass


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

        user = data["user"]  # adjust to match your printout
        self.id = user["id"]
        self.username = user["username"]
        self.email = user["email"]
        self.first_name = user["first_name"]
        self.last_name = user["last_name"]
        self.profile_pic_url = user["profile_picture"]

        self.update_headers(session)

    async def login(self, username_or_email, password, session):
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

    @asyncSlot()
    async def refresh_tokens(self, session):
        try:
            async with session.post(
                "users/refresh/", json={"refresh": self.refresh}
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except aiohttp.ClientResponseError as e:
            print(e)
            self.logout()
        finally:
            self.add_tokens(data, session)
            print(data)

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
        layout = QVBoxLayout(self)

        self.welcome_text = QLabel(f"Welcome to {self.window_.PRODUCT_NAME}")
        self.welcome_text.setAlignment(Qt.AlignCenter)
        self.welcome_text.setStyleSheet("font-size: 40px; font-weight: 400")

        self.username_or_email = QLineEdit()
        self.username_or_email.setPlaceholderText("Username or Email")

        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")

        self.error_message = QLabel("")
        self.error_message.setStyleSheet("""
            color: #d20c0c;
            font-size: 18px;
        """)

        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.on_login_click)

        self.enter_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self)
        self.enter_shortcut.activated.connect(self.on_login_click)
        # self.login_btn.
        form_widget = QWidget()
        form_widget.setMaximumWidth(560)
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)

        self.username_or_email.setFixedWidth(360)
        self.password.setFixedWidth(360)
        self.login_btn.setFixedWidth(360)
        self.login_btn.setStyleSheet("margin: 0 0 100px 0")
        self.login_btn.setCursor(Qt.PointingHandCursor)

        for w in (
            self.username_or_email,
            self.password,
            self.error_message,
            self.login_btn,
        ):
            form_layout.addWidget(w)

        layout.addWidget(self.welcome_text)
        layout.addWidget(form_widget, alignment=Qt.AlignHCenter)

    @asyncSlot()
    async def on_login_click(self):
        self.window_.show_loader()
        try:
            ok, msg = await self.window_.auth.login(
                self.username_or_email.text(),
                self.password.text(),
                self.window_.session,
            )
        finally:
            self.window_.hide_loader()
        if ok:
            self.login_successful.emit()
        else:
            self.error_message.setText(msg)


class DashboardPage(QWidget):
    enroll_requested = pyqtSignal(int)

    def __init__(self, window):
        super().__init__()
        self.window_ = window
        self.initUi()

    def initUi(self):
        layout = QHBoxLayout(self)

        # Sidebar
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        self.sidebar_dashboard_btn = QPushButton("Dashboard")
        self.sidebar_enrolled_faces_btn = QPushButton("Enrolled Faces")
        sidebar_layout.addWidget(self.sidebar_dashboard_btn)
        sidebar_layout.addWidget(self.sidebar_enrolled_faces_btn)
        sidebar_layout.addStretch()

        # Top nav
        nav_widget = QWidget()
        nav_layout = QHBoxLayout(nav_widget)
        self.nav_welcome_label = QLabel("")
        self.avatar = QLabel()
        self.avatar.setFixedSize(48, 48)
        self.avatar.setScaledContents(True)
        nav_layout.addWidget(self.nav_welcome_label)
        nav_layout.addStretch()
        nav_layout.addWidget(self.avatar)

        # Table
        self.table_model = UserModel()
        self.table = QTableView()
        self.table.setModel(self.table_model)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setDefaultSectionSize(56)
        self.table.setAlternatingRowColors(True)
        self.table.viewport().setCursor(Qt.PointingHandCursor)
        self.table.setStyleSheet("""
            QTableView { 
                background: #2f2c31; 
                alternate-background-color: #26232a;
                color: #F8FAFC; 
                font-size: 18px;
                gridline-color: #363138; 
                border: none; 
            }
            QTableView::item:selected { 
                background: #5d0b9a; 
            }
            QTableView::item:hover    { background: #3a3540; }
            QHeaderView::section { 
                background: #1d1b1e; 
                color: #F8FAFC;
                padding: 8px; 
                border: none; 
                font-size: 18px; 
            }
        """)

        # Right-hand content column
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.addWidget(nav_widget)
        content_layout.addWidget(self.table)

        layout.addWidget(sidebar_widget)
        layout.addWidget(content, 1)

    def on_enroll_clicked(self, user_id):
        self.enroll_requested.emit(user_id)

    async def load_users(self):
        try:
            async with self.window_.session.get(
                self.window_.USERS_TABLE_DATA_URL
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except aiohttp.ClientError as e:
            print(f"Failed to load users: {e}")
            return
        self.table_model.set_users(data["users"])
        self.populate_actions()

    async def refresh(self):
        auth = self.window_.auth
        await auth.get_profile_pic()

        self.nav_welcome_label.setText(f"Welcome, {auth.first_name}")
        self.avatar.setPixmap(auth.profile_pic)

        await self.load_users()

    def make_actions_widget(self, user):
        has_face = bool(user.get("face_embeddings"))

        enroll_btn = QPushButton("Re-enroll Face" if has_face else "Enroll Face")
        edit_btn = QPushButton("Edit")
        for btn in (enroll_btn, edit_btn):
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("font-size: 16px; padding: 6px 12px;")

        enroll_btn.clicked.connect(lambda _, uid=user["id"]: self.on_enroll_clicked(uid))
        edit_btn.clicked.connect(lambda _, u=user: self.on_edit_user(u))

        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignCenter)
        lay.addWidget(enroll_btn)
        lay.addWidget(edit_btn)
        return w

    def populate_actions(self):
        for row in range(self.table_model.rowCount()):
            user = self.table_model.user_at(row)
            self.table.setIndexWidget(
                self.table_model.index(row, 4), self.make_actions_widget(user)
            )

    def on_enroll_face(self, user):
        QMessageBox.information(
            self,
            "Enroll Face",
            f"Enroll face for {user['first_name']} (ID {user['id']})",
        )

    def on_edit_user(self, user):
        QMessageBox.information(
            self,
            "Edit User",
            f"Edit {user['first_name']} {user['last_name']} (ID {user['id']})",
        )


class EnrollFaceEmbeddingPage(QWidget):
    back_requested = pyqtSignal()
    buffer_full = pyqtSignal()

    def __init__(self, window):
        super().__init__()
        self.window_ = window
        self.user_id = None
        self.cap = None

        self.buffer = []  # list of face crops (BGR images)
        self.embeddings = []  # one embedding per captured face
        self.embedding = None
        self.MAX_BUFFER = 15
        self.CAPTURE_INTERVAL = 0.3  # seconds between captures
        self.MIN_DET_SCORE = 0.7
        self.MIN_FACE_SIZE = 120  # px, width of the face box
        self._last_capture = 0.0

        self.camera_label = VideoLabel()
        self.camera_label.setMinimumSize(640, 480)
        self.camera_label.setAlignment(Qt.AlignCenter)

        self.back_btn = QPushButton("Back")
        self.back_btn.clicked.connect(self.back_requested.emit)

        layout = QVBoxLayout(self)
        layout.addWidget(self.back_btn, alignment=Qt.AlignLeft)
        layout.addWidget(self.camera_label)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.cam_feed)

    def is_good_face(self, face):
        x1, y1, x2, y2 = face.bbox
        return face.det_score >= self.MIN_DET_SCORE and (x2 - x1) >= self.MIN_FACE_SIZE

    def try_capture(self, frame, face):
        x1, y1, x2, y2 = face.bbox.astype(int)

        now = time.monotonic()
        if len(self.buffer) >= self.MAX_BUFFER:
            return
        if now - self._last_capture < self.CAPTURE_INTERVAL:
            return
        if not self.is_good_face(face):
            return

        pad = int((x2 - x1) * 0.2)  # a little margin around the face
        h, w = frame.shape[:2]
        crop = frame[max(y1 - pad, 0):min(y2 + pad, h), max(x1 - pad, 0):min(x2 + pad, w)]

        self.buffer.append(crop.copy())
        self.embeddings.append(face.normed_embedding.copy())
        self._last_capture = now

    def detect_face(self, frame):
        faces = self.window_.face_app.get(frame)
        if not faces:
            return None

        return max(
            faces,
            key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
        )

    def set_user(self, user_id):
        self.user_id = user_id
        self.clear_buffer()

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

    def cam_feed(self):
        if self.cap is None:
            return None
        success, frame = self.cap.read()
        if not success:
            return None
        face = self.detect_face(frame)
        display = frame.copy()  # draw on a copy, keep the original frame clean


        if face is not None:
            self.try_capture(frame, face)
            x1, y1, x2, y2 = face.bbox.astype(int)
            color = (0, 255, 0) if self.is_good_face(face) else (0, 165, 255)  # orange = not good enough
            cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)

            if self.window_.ENABLE_ANTI_SPOOFING:
                spoof_label, spoof_confidence = is_face_real(frame, [x1, y1, x2, y2])

                if spoof_label != "Real":

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(
                        frame,
                        f"{spoof_label} {spoof_confidence * 100:.1f}%",
                        (x1, max(y1 - 10, 25)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 0, 255),
                        2,
                    )

                    self.update_frame(frame)
                    return

        cv2.putText(display, f"Captured: {len(self.buffer)}/{self.MAX_BUFFER}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
        self.update_frame(display)
        if len(self.buffer) >= self.MAX_BUFFER:
            self.stop_camera()
            self.buffer_full.emit()
        return frame

    def update_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self.camera_label.set_frame(QPixmap.fromImage(image.copy()))

    def clear_buffer(self):
        self.buffer.clear()
        self.embeddings.clear()
        self.embedding = None
        self._last_capture = 0.0

    def build_embedding(self):
        mean = np.mean(self.embeddings, axis=0)
        self.embedding = mean / np.linalg.norm(mean)
        return self.embedding


class DetectionCheckPage(QWidget):
    back_requested = pyqtSignal()
    check_requested = pyqtSignal()

    def __init__(self, window):
        super().__init__()
        self.window_ = window

        self.image_label = VideoLabel()
        self.image_label.setMinimumSize(640, 480)

        self.back_btn = QPushButton("Retake")
        self.back_btn.clicked.connect(self.back_requested.emit)

        self.check_btn = QPushButton("Check Detection")
        self.check_btn.clicked.connect(self.check_requested.emit)

        layout = QVBoxLayout(self)
        layout.addWidget(self.back_btn, alignment=Qt.AlignLeft)
        layout.addWidget(self.image_label)
        layout.addWidget(self.check_btn, alignment=Qt.AlignCenter)

    def set_image(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self.image_label.set_frame(QPixmap.fromImage(image.copy()))


class CheckEmbeddingPage(QWidget):
    back_requested = pyqtSignal()
    approved = pyqtSignal()

    def __init__(self, window):
        super().__init__()
        self.window_ = window
        self.embedding = None
        self.cap = None
        self.streak = 0
        self.verified = False

        self.camera_label = VideoLabel()
        self.camera_label.setMinimumSize(640, 480)

        self.status_label = QLabel("Look at the camera")
        self.status_label.setAlignment(Qt.AlignCenter)

        self.back_btn = QPushButton("Back")
        self.back_btn.clicked.connect(self.back_requested.emit)

        self.approve_btn = QPushButton("Approve & Save")
        self.approve_btn.setEnabled(False)
        self.approve_btn.clicked.connect(self.approved.emit)

        layout = QVBoxLayout(self)
        layout.addWidget(self.back_btn, alignment=Qt.AlignLeft)
        layout.addWidget(self.camera_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.approve_btn, alignment=Qt.AlignCenter)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.cam_feed)

    def set_embedding(self, embedding):
        self.embedding = embedding
        self.streak = 0
        self.verified = False
        self.approve_btn.setEnabled(False)
        self.status_label.setText("Look at the camera")

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

    def cam_feed(self):
        if self.cap is None:
            return
        success, frame = self.cap.read()
        if not success:
            return

        display = frame.copy()
        faces = self.window_.face_app.get(frame)

        if faces:
            face = max(
                faces,
                key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
            )
            # both vectors are normalized, so the dot product is the cosine similarity
            sim = float(np.dot(self.embedding, face.normed_embedding))
            matched = sim >= self.window_.SIMILARITY_THRESHOLD
            self.streak = self.streak + 1 if matched else 0

            color = (0, 255, 0) if matched else (0, 0, 255)
            x1, y1, x2, y2 = face.bbox.astype(int)
            cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
            cv2.putText(display, f"Similarity: {sim:.3f}", (x1, max(y1 - 10, 25)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        else:
            self.streak = 0

        needed = self.window_.STREAK_THRESHOLD
        if self.streak >= needed:
            self.verified = True  # stays verified once reached
        if self.verified:
            self.status_label.setText("Face verified")
            self.approve_btn.setEnabled(True)
        else:
            self.status_label.setText(f"Matching: {self.streak}/{needed}")

        self.update_frame(display)

    def update_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self.camera_label.set_frame(QPixmap.fromImage(image.copy()))


# Main Window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.TITLE_HEIGHT = 48
        self.closed = asyncio.Event()

        self.face_app = FaceAnalysis(
            name="buffalo_l",
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        self.face_app.prepare(ctx_id=0, det_size=(640, 640))

        self.auth = AuthContext()
        self.session = None
        self.BASE_URL = "http://localhost:8000/api/"
        self.CHECK_USER_URL = f"{self.BASE_URL}users/check/"
        self.PRODUCT_NAME = "FaceCall"
        self.USERS_TABLE_DATA_URL = "attendance/data/table"
        self.SIMILARITY_THRESHOLD = 0.50
        self.CAMERA_INDEX = 0
        self.STREAK_THRESHOLD = 20
        self.ENABLE_ANTI_SPOOFING = True

        self.setGeometry(0, 0, 1280, 720)
        self.setWindowTitle(self.PRODUCT_NAME)
        self.setWindowIcon(icon_from_svg())

        self.initUi()
        self.center()

    def initUi(self):
        container = QWidget()
        container.setObjectName("central")
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title bar on top, pages below
        layout.addWidget(TitleBar(self))
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # Loader overlay
        self.overlay = QWidget(container)
        self.overlay.setObjectName("overlay")
        self.overlay.setAttribute(Qt.WA_StyledBackground, True)
        self.overlay.setStyleSheet("#overlay { background: rgba(255, 255, 255, 10); }")
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
            color=QColor(191, 0, 255),
        )

        # Pages
        self.login_page = LoginPage(self)
        self.dashboard_page = DashboardPage(self)
        self.enroll_page = EnrollFaceEmbeddingPage(self)
        self.check_page = DetectionCheckPage(self)
        self.check_embedding_page = CheckEmbeddingPage(self)

        self.stack.addWidget(self.login_page)
        self.stack.addWidget(self.dashboard_page)
        self.stack.addWidget(self.enroll_page)
        self.stack.addWidget(self.check_page)
        self.stack.addWidget(self.check_embedding_page)

        # Navigation
        self.login_page.login_successful.connect(self.on_login_successful)
        self.dashboard_page.enroll_requested.connect(self.open_enroll_page)

        self.enroll_page.back_requested.connect(self.close_enroll_page)
        self.enroll_page.buffer_full.connect(self.on_buffer_full)

        self.check_page.back_requested.connect(
            lambda: self.open_enroll_page(self.enroll_page.user_id)
        )
        self.check_page.check_requested.connect(self.open_check_embedding)

        self.check_embedding_page.back_requested.connect(self.close_check_embedding)
        self.check_embedding_page.approved.connect(self.on_approved)

        # Title bar styles live in TitleBar itself
        self.setStyleSheet("""
            QMainWindow, QWidget#central { background: #1d1b1e; }
            QLabel { color: #F8FAFC; font-size: 24px; font-family: poppins}
            QLineEdit { background: #2f2c31; color: #F8FAFC; border: 1px solid #363138; border-radius: 6px; padding: 8px 8px 8px 16px; font-size: 20px}
            QPushButton { background: #5d0b9a; color: #fff; border-radius: 6px; padding: 8px; font-size: 18px; font-family: poppins}
            QPushButton:hover { background: #3f114e; }
            QPushButton:disabled { background: #3a3540; color: #8a8590; }
        """)

    # ---- enroll flow ----
    @asyncSlot(int)
    async def open_enroll_page(self, user_id):
        self.enroll_page.set_user(user_id)
        self.show_loader()
        try:
            await self.enroll_page.start_camera()
        finally:
            self.hide_loader()
        self.stack.setCurrentWidget(self.enroll_page)

    def close_enroll_page(self):
        self.enroll_page.stop_camera()
        self.stack.setCurrentWidget(self.dashboard_page)

    @asyncSlot()
    async def on_buffer_full(self):
        self.show_loader()
        try:
            self.enroll_page.build_embedding()
        finally:
            self.hide_loader()
        self.check_page.set_image(self.enroll_page.buffer[-1])
        self.stack.setCurrentWidget(self.check_page)

    @asyncSlot()
    async def open_check_embedding(self):
        self.check_embedding_page.set_embedding(self.enroll_page.embedding)
        self.show_loader()
        try:
            await self.check_embedding_page.start_camera()
        finally:
            self.hide_loader()
        self.stack.setCurrentWidget(self.check_embedding_page)

    def close_check_embedding(self):
        self.check_embedding_page.stop_camera()
        self.stack.setCurrentWidget(self.check_page)

    # ---- save ----
    async def save_embedding(self, user_id, embedding):
        try:
            async with self.session.post(
                f"users/face-embedding/add/{user_id}/",
                json={"face_embedding": embedding.tolist()},
            ) as resp:
                try:
                    data = await resp.json()
                except aiohttp.ContentTypeError:
                    data = {}
                if resp.status >= 400:
                    msg = data.get("error") or data.get("detail") or f"Save failed ({resp.status})"
                    return False, msg
        except aiohttp.ClientError:
            return False, "Server error"
        return True, ""

    @asyncSlot()
    async def on_approved(self):
        user_id = self.enroll_page.user_id
        embedding = self.enroll_page.embedding

        self.show_loader()
        try:
            ok, msg = await self.save_embedding(user_id, embedding)
            if ok:
                await self.dashboard_page.load_users()  # row flips to "Enrolled"
        finally:
            self.hide_loader()

        if ok:
            self.check_embedding_page.stop_camera()
            self.enroll_page.clear_buffer()
            self.stack.setCurrentWidget(self.dashboard_page)
            QMessageBox.information(self, "Face Enrollment", "Face embedding saved.")
        else:
            QMessageBox.warning(self, "Face Enrollment", msg)

    # ---- login ----
    @asyncSlot()
    async def on_login_successful(self):
        self.show_loader()
        try:
            await self.dashboard_page.refresh()
        finally:
            self.hide_loader()
        self.stack.setCurrentWidget(self.dashboard_page)

    def center(self):
        geo = self.frameGeometry()
        geo.moveCenter(QApplication.primaryScreen().availableGeometry().center())
        self.move(geo.topLeft())

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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.overlay.isVisible():
            self._layout_overlay()

    def closeEvent(self, event):
        self.enroll_page.stop_camera()
        self.check_embedding_page.stop_camera()
        self.closed.set()
        event.accept()


async def main(window):
    app_close = asyncio.Event()
    app.aboutToQuit.connect(app_close.set)

    window.session = aiohttp.ClientSession(
        base_url=window.BASE_URL,
        headers={
            "Authorization": "",
            "X-CSRFToken": "",
        },
    )

    await window.closed.wait()  # window was closed
    await window.session.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.show()

    with loop:
        loop.run_until_complete(main(window))