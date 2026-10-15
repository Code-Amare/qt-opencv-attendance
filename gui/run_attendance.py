from insightface.app import FaceAnalysis
import sys
import io
import cv2
import numpy as np
import qasync
import aiohttp
import asyncio
from qasync import QEventLoop, asyncSlot
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QHBoxLayout,
    QGraphicsBlurEffect,
    QVBoxLayout,
    QApplication,
    QMainWindow,
    QPushButton,
    QShortcut,
    QStackedWidget,
    QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QAbstractTableModel, QModelIndex, QTimer
from pyqtspinner.spinner import WaitingSpinner
from utils import TitleBar, icon_from_svg
from PyQt5.QtGui import QColor, QKeySequence, QImage, QPixmap
from anti_spoof import is_face_real


async def open_capture(index):
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

class LoadFaceEmbeddingPage(QWidget):
    face_embedding_loaded = pyqtSignal()
    EMBEDDINGS_PATH = "face_embeddings.npz"

    def __init__(self, window):
        super().__init__()
        self.window_ = window

        self.session_input = QLineEdit()
        self.session_input.setPlaceholderText("Session ID")

        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("color: #d20c0c; font-size: 18px;")

        self.local_btn = QPushButton("Load embedding locally")
        self.django_btn = QPushButton("Load new embedding")
        self.save_btn = QPushButton("Download && save .npz")
        self.local_btn.clicked.connect(self.on_local_clicked)
        self.django_btn.clicked.connect(self.on_django_clicked)
        self.save_btn.clicked.connect(self.on_save_clicked)

        for w in (self.session_input, self.local_btn, self.django_btn, self.save_btn):
            w.setFixedWidth(360)

        layout = QVBoxLayout(self)
        layout.addStretch()
        for w in (
            self.session_input,
            self.local_btn,
            self.django_btn,
            self.save_btn,
            self.error_label,
        ):
            layout.addWidget(w, alignment=Qt.AlignHCenter)
        layout.addStretch()

    @asyncSlot()
    async def on_local_clicked(self):
        await self.load(self.read_local)

    @asyncSlot()
    async def on_django_clicked(self):
        await self.load(self.download)

    def set_message(self, text, error=True):
        color = "#d20c0c" if error else "#2ecc71"
        self.error_label.setStyleSheet(f"color: {color}; font-size: 18px;")
        self.error_label.setText(text)

    async def read_local(self, path=None):
        with np.load(path or self.EMBEDDINGS_PATH) as data:
            self.window_.set_embeddings(data["embeddings"], data["labels"])

    async def fetch_embeddings(self):
        async with self.window_.session.get(
            self.window_.DOWNLOAD_FACE_EMBEDDINGS
        ) as resp:
            resp.raise_for_status()
            return await resp.read()

    async def download(self):
        content = await self.fetch_embeddings()
        with np.load(io.BytesIO(content)) as data:
            self.window_.set_embeddings(data["embeddings"], data["labels"])

    @asyncSlot()
    async def on_save_clicked(self):
        self.window_.show_loader()
        try:
            content = await self.fetch_embeddings()
            with np.load(io.BytesIO(content)) as data:
                if len(data["embeddings"]) == 0 or len(data["embeddings"]) != len(data["labels"]):
                    raise ValueError("Invalid embeddings file.")
            with open(self.EMBEDDINGS_PATH, "wb") as f:
                f.write(content)
        except (aiohttp.ClientError, OSError, KeyError, ValueError) as e:
            self.set_message(str(e))
            return
        finally:
            self.window_.hide_loader()
        self.set_message(f"Saved {self.EMBEDDINGS_PATH}", error=False)

    async def fetch_session(self, session_id):
        async with self.window_.session.get(f"attendance/session/{session_id}/") as resp:
            try:
                data = await resp.json()
            except aiohttp.ContentTypeError:
                data = {}
            if resp.status >= 400:
                raise ValueError(data.get("error") or data.get("detail") or "Invalid session")
        attendance = data.get("attendance")
        if not isinstance(attendance, list):
            raise ValueError("Invalid session response")
        return {int(u["user_id"]): u for u in attendance if u.get("user_id") is not None}

    async def load(self, load_embeddings):
        text = self.session_input.text().strip()
        if not text.isdigit():
            self.set_message("Enter a valid session ID")
            return
        session_id = int(text)

        self.window_.show_loader()
        try:
            recorded = await self.fetch_session(session_id)
            await load_embeddings()
        except (aiohttp.ClientError, OSError, KeyError, ValueError) as e:
            self.set_message(str(e))
            return
        finally:
            self.window_.hide_loader()

        self.window_.session_id = session_id
        self.window_.recorded_users = recorded
        self.set_message("", error=False)
        self.face_embedding_loaded.emit()

class RecordAttendancePage(QWidget):
    back_requested = pyqtSignal()

    def __init__(self, window):
        super().__init__()
        self.window_ = window
        self.cap = None
        self.label = None
        self.streak = 0
        self.pending = set()
        self._tasks = set()

        self.camera_label = VideoLabel()
        self.camera_label.setMinimumSize(640, 480)

        self.status_label = QLabel("Look at the camera")
        self.status_label.setAlignment(Qt.AlignCenter)

        self.back_btn = QPushButton("Back")
        self.back_btn.clicked.connect(self.back_requested.emit)

        layout = QVBoxLayout(self)
        layout.addWidget(self.back_btn, alignment=Qt.AlignLeft)
        layout.addWidget(self.camera_label)
        layout.addWidget(self.status_label)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.cam_feed)

    def reset(self):
        self.label = None
        self.streak = 0
        self.pending.clear()
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

    def name(self, user_id):
        user = self.window_.recorded_users.get(user_id, {})
        return user.get("first_name") or f"ID {user_id}"

    @staticmethod
    def status_color(status):
        return {"absent": (0, 0, 255), "late": (0, 255, 255)}.get(
            str(status).lower(), (0, 255, 0)
        )

    def update_streak(self, user_id):
        if user_id is None:
            self.label, self.streak = None, 0
            return False
        if user_id == self.label:
            self.streak += 1
        else:
            self.label, self.streak = user_id, 1
        return self.streak >= self.window_.STREAK_THRESHOLD

    def spawn(self, coro):
        task = asyncio.ensure_future(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def cam_feed(self):
        if self.cap is None:
            return
        success, frame = self.cap.read()
        if not success:
            return

        display = frame.copy()
        faces = self.window_.face_app.get(frame)

        if not faces:
            self.update_streak(None)
            self.update_frame(display)
            return

        face = max(
            faces,
            key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
        )
        x1, y1, x2, y2 = face.bbox.astype(int)
        if self.window_.ENABLE_ANTI_SPOOFING:
            spoof_label, spoof_confidence = is_face_real(frame, [x1, y1, x2, y2])

            if spoof_label != "Real":
                self.update_streak(None)

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
        user_id, score = self.window_.match_face(face)
        users = self.window_.recorded_users
        needed = self.window_.STREAK_THRESHOLD

        if user_id is None:
            self.update_streak(None)
            text, color = f"Unknown ({score:.2f})", (0, 0, 255)

        elif user_id not in users:
            self.update_streak(None)
            text, color = f"ID {user_id}: not in this session", (0, 165, 255)

        elif users[user_id].get("status") is not None:
            self.update_streak(None)
            status = users[user_id]["status"]
            text, color = f"{self.name(user_id)}: {status}", self.status_color(status)

        else:
            confirmed = self.update_streak(user_id)
            color = (0, 255, 0)
            if user_id in self.pending:
                text = f"{self.name(user_id)}: recording..."
            else:
                text = f"{self.name(user_id)}  {self.streak}/{needed}"
                if confirmed:
                    self.pending.add(user_id)
                    self.spawn(self.record_attendance(user_id))

        cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
        cv2.putText(display, text, (x1, max(y1 - 10, 25)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        self.update_frame(display)

    async def record_attendance(self, user_id):
        try:
            async with self.window_.session.post(
                self.window_.SET_ATTENDANCE,
                json={"user_id": user_id, "session_id": self.window_.session_id},
            ) as resp:
                try:
                    data = await resp.json()
                except aiohttp.ContentTypeError:
                    data = {}
                if resp.status not in (200, 201):
                    self.status_label.setText(
                        data.get("error") or data.get("detail") or f"Failed ({resp.status})"
                    )
                    return

            status = (data.get("attendance") or {}).get("status")
            if status is None:
                self.status_label.setText("Server returned no status")
                return

            name = data.get("first_name") or self.name(user_id)
            self.window_.recorded_users[user_id] = {
                "user_id": user_id, "first_name": name, "status": status,
            }
            self.status_label.setText(f"Recorded: {name} ({status})")

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self.status_label.setText(f"Request failed: {e}")
        finally:
            self.pending.discard(user_id)
            if self.label == user_id:
                self.label, self.streak = None, 0

    def update_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self.camera_label.set_frame(QPixmap.fromImage(image.copy()))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.TITLE_HEIGHT = 48
        self.closed = asyncio.Event()

        self.session_id = None
        self.recorded_users = {}

        self.known_embeddings = None
        self.known_labels = None

        self.face_app = FaceAnalysis(
            name="buffalo_l",
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        self.face_app.prepare(ctx_id=0, det_size=(640, 640))

        self.auth = AuthContext()
        self.session = None
        self.BASE_URL = "https://localhost:8000/api/"
        self.SET_ATTENDANCE = "attendance/"
        self.DOWNLOAD_FACE_EMBEDDINGS = "users/face-embedding/download/"
        self.PRODUCT_NAME = "FaceCall | Attendance"
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

        layout.addWidget(TitleBar(self))
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

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

        self.login_page = LoginPage(self)
        self.record_attendance_page = RecordAttendancePage(self)

        self.stack.addWidget(self.login_page)
        self.stack.addWidget(self.record_attendance_page)
        self.load_page = LoadFaceEmbeddingPage(self)
        self.stack.addWidget(self.load_page)

        self.load_page.face_embedding_loaded.connect(self.open_record_attendance)
        self.record_attendance_page.back_requested.connect(self.close_record_attendance)

        self.login_page.login_successful.connect(self.on_login_successful)

        self.setStyleSheet("""
                    QMainWindow, QWidget#central { background: #1d1b1e; }
                    QLabel { color: #F8FAFC; font-size: 24px; font-family: poppins}
                    QLineEdit { background: #2f2c31; color: #F8FAFC; border: 1px solid #363138; border-radius: 6px; padding: 8px 8px 8px 16px; font-size: 20px}
                    QPushButton { background: #5d0b9a; color: #fff; border-radius: 6px; padding: 8px; font-size: 18px; font-family: poppins}
                    QPushButton:hover { background: #3f114e; }
                    QPushButton:disabled { background: #3a3540; color: #8a8590; }
                """)

    @asyncSlot()
    async def open_record_attendance(self):
        self.record_attendance_page.reset()
        self.show_loader()
        try:
            await self.record_attendance_page.start_camera()
        finally:
            self.hide_loader()
        self.stack.setCurrentWidget(self.record_attendance_page)

    def close_record_attendance(self):
        self.record_attendance_page.stop_camera()
        self.stack.setCurrentWidget(self.load_page)

    def on_login_successful(self):
        self.stack.setCurrentWidget(self.load_page)

    def closeEvent(self, event):
        self.record_attendance_page.stop_camera()
        self.closed.set()
        event.accept()

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

    def set_embeddings(self, embeddings, labels):
        if len(embeddings) == 0 or len(embeddings) != len(labels):
            raise ValueError("Invalid embeddings file.")
        embeddings = embeddings.astype(np.float32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        self.known_embeddings = embeddings / np.maximum(norms, 1e-12)
        self.known_labels = labels.astype(np.int32)

    def match_face(self, face):
        similarities = self.known_embeddings @ face.normed_embedding
        best = int(np.argmax(similarities))
        score = float(similarities[best])
        if score >= self.SIMILARITY_THRESHOLD:
            return int(self.known_labels[best]), score
        return None, score


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

    await window.closed.wait()
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