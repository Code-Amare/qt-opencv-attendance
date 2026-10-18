import asyncio
import time
import common
import aiohttp
import cv2
import numpy as np
from PyQt5.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)
from qasync import asyncSlot

from common import BaseWindow, CameraPage, VideoLabel, draw_box, largest_face, run
from utils import default_avatar, get_image


class UserModel(QAbstractTableModel):
    HEADERS = ["ID", "FIRST NAME", "LAST NAME", "FACE STATUS", "ACTIONS"]

    def __init__(self):
        super().__init__()
        self._users: list[dict] = []
        self._avatars: dict = {}

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
        enrolled = bool(user.get("face_embeddings"))

        if role == Qt.DisplayRole:
            if col == 0:
                return user["id"]
            if col == 1:
                return user["first_name"]
            if col == 2:
                return user["last_name"]
            if col == 3:
                return "Enrolled" if enrolled else "Not enrolled"
            return ""

        if role == Qt.DecorationRole and col == 1:
            return self._avatars.get(user["id"])

        if role == Qt.ForegroundRole and col == 3:
            return QColor("#10B981") if enrolled else QColor("#F59E0B")

        if role == Qt.TextAlignmentRole:
            return int(Qt.AlignLeft | Qt.AlignVCenter)

        return None

    def set_users(self, users, avatars):
        self.beginResetModel()
        self._users = users
        self._avatars = avatars
        self.endResetModel()

    def user_at(self, row):
        return self._users[row]


class DashboardPage(QWidget):
    enroll_requested = pyqtSignal(int)
    AVATAR_SIZE = 36
    ACTIONS_WIDTH = 190
    COLUMN_PADDING = 24
    HEADER_STYLE = """
        QHeaderView::section {
            background: #18181C;
            color: #6B6B73;
            border: none;
            border-right: 1px solid rgba(255, 255, 255, 25);
            border-bottom: 1px solid rgba(255, 255, 255, 25);
            padding: 8px 12px;
            font-size: 12px;
            font-weight: 500;
        }
    """

    def __init__(self, window):
        super().__init__()
        self.window_ = window
        self.needs_fit = False
        self.initUi()

    def initUi(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        nav_widget = QWidget()
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_welcome_label = QLabel("")
        self.nav_welcome_label.setObjectName("muted")
        self.avatar = QLabel()
        self.avatar.setFixedSize(48, 48)
        self.avatar.setScaledContents(True)
        nav_layout.addWidget(self.nav_welcome_label)
        nav_layout.addStretch()
        nav_layout.addWidget(self.avatar)

        title = QLabel("Users")
        title.setObjectName("h1")

        self.table_model = UserModel()
        self.table = QTableView()
        self.table.setModel(self.table_model)
        self.table.setIconSize(QSize(self.AVATAR_SIZE, self.AVATAR_SIZE))
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setDefaultSectionSize(56)
        self.table.setShowGrid(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        header.setMinimumSectionSize(70)
        header.setHighlightSections(False)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setStyleSheet(self.HEADER_STYLE)

        layout.addWidget(nav_widget)
        layout.addWidget(title)
        layout.addWidget(self.table)

    def showEvent(self, event):
        super().showEvent(event)
        if self.needs_fit:
            QTimer.singleShot(0, self.fit_columns)

    def fit_columns(self):
        self.needs_fit = False
        count = self.table_model.columnCount()
        self.table.resizeColumnsToContents()

        widths = [
            self.table.columnWidth(col) + self.COLUMN_PADDING
            for col in range(count - 1)
        ]
        extra = self.table.viewport().width() - self.ACTIONS_WIDTH - sum(widths)
        if extra > 0:
            widths[1] += extra // 2
            widths[2] += extra - extra // 2

        for col, width in enumerate(widths):
            self.table.setColumnWidth(col, width)
        self.table.setColumnWidth(count - 1, self.ACTIONS_WIDTH)

    def on_enroll_clicked(self, user_id):
        self.enroll_requested.emit(user_id)

    def scale_avatar(self, pixmap):
        return pixmap.scaled(
            self.AVATAR_SIZE,
            self.AVATAR_SIZE,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

    async def load_avatar(self, user, fallback):
        url = user.get("profile_picture")
        if not url:
            return fallback
        try:
            pixmap = await get_image(url)
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError):
            return fallback
        if pixmap is None or pixmap.isNull():
            return fallback
        return self.scale_avatar(pixmap)

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

        users = data["users"]
        fallback = self.scale_avatar(default_avatar())
        pixmaps = await asyncio.gather(
            *(self.load_avatar(user, fallback) for user in users)
        )
        avatars = {user["id"]: pix for user, pix in zip(users, pixmaps)}

        self.table_model.set_users(users, avatars)
        self.populate_actions()

        self.needs_fit = True
        if self.isVisible():
            self.fit_columns()

    async def refresh(self):
        auth = self.window_.auth
        await auth.get_profile_pic()

        self.nav_welcome_label.setText(f"Welcome, {auth.first_name}")
        self.avatar.setPixmap(auth.profile_pic)

        await self.load_users()

    def make_actions_widget(self, user):
        has_face = bool(user.get("face_embeddings"))

        enroll_btn = QPushButton("Re-enroll Face" if has_face else "Enroll Face")
        enroll_btn.setCursor(Qt.PointingHandCursor)
        enroll_btn.setStyleSheet("font-size: 14px; padding: 6px 12px;")
        enroll_btn.clicked.connect(
            lambda _, uid=user["id"]: self.on_enroll_clicked(uid)
        )

        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lay.addWidget(enroll_btn)
        return w

    def populate_actions(self):
        for row in range(self.table_model.rowCount()):
            user = self.table_model.user_at(row)
            self.table.setIndexWidget(
                self.table_model.index(row, 4), self.make_actions_widget(user)
            )


class EnrollFaceEmbeddingPage(CameraPage):
    back_requested = pyqtSignal()
    buffer_full = pyqtSignal()

    def __init__(self, window):
        super().__init__(window)
        self.user_id = None

        self.buffer = []
        self.embeddings = []
        self.embedding = None
        self.MAX_BUFFER = 15
        self.CAPTURE_INTERVAL = 0.3
        self.MIN_DET_SCORE = 0.7
        self.MIN_FACE_SIZE = 120
        self._last_capture = 0.0

        self.back_btn = QPushButton("← Back")
        self.back_btn.setObjectName("secondary")
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.back_requested.emit)

        title = QLabel("Enroll face")
        title.setObjectName("h1")
        self.id_label = QLabel("")
        self.id_label.setObjectName("subtle")

        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.addWidget(title)
        titles.addWidget(self.id_label)

        header = QHBoxLayout()
        header.addWidget(self.back_btn, alignment=Qt.AlignTop)
        header.addSpacing(12)
        header.addLayout(titles)
        header.addStretch()

        panel = QFrame()
        panel.setObjectName("panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(8, 8, 8, 8)
        panel_layout.addWidget(self.camera_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)
        layout.addLayout(header)
        layout.addWidget(panel, stretch=1)

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

        pad = int((x2 - x1) * 0.2)
        h, w = frame.shape[:2]
        crop = frame[
            max(y1 - pad, 0) : min(y2 + pad, h), max(x1 - pad, 0) : min(x2 + pad, w)
        ]

        self.buffer.append(crop.copy())
        self.embeddings.append(face.normed_embedding.copy())
        self._last_capture = now

    def set_user(self, user_id):
        self.user_id = user_id
        self.id_label.setText(f"User ID: {user_id}")
        self.clear_buffer()

    def cam_feed(self):
        frame = self.read_frame()
        if frame is None:
            return

        display = frame.copy()
        face = largest_face(self.window_.face_app.get(frame))

        if face is not None:
            if self.is_spoof(frame, display, face.bbox):
                self.update_frame(display)
                return

            self.try_capture(frame, face)
            good = self.is_good_face(face)
            draw_box(display, face.bbox, color=(0, 255, 0) if good else (0, 165, 255))

        cv2.putText(
            display,
            f"Captured: {len(self.buffer)}/{self.MAX_BUFFER}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 0, 0),
            2,
        )
        self.update_frame(display)

        if len(self.buffer) >= self.MAX_BUFFER:
            self.stop_camera()
            self.buffer_full.emit()

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

        self.back_btn = QPushButton("← Retake")
        self.back_btn.setObjectName("secondary")
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.back_requested.emit)

        title = QLabel("Review capture")
        title.setObjectName("h1")

        header = QHBoxLayout()
        header.addWidget(self.back_btn, alignment=Qt.AlignTop)
        header.addSpacing(12)
        header.addWidget(title)
        header.addStretch()

        self.image_label = VideoLabel()
        self.image_label.setMinimumSize(640, 480)

        panel = QFrame()
        panel.setObjectName("panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(8, 8, 8, 8)
        panel_layout.addWidget(self.image_label)

        self.check_btn = QPushButton("Check Detection")
        self.check_btn.setCursor(Qt.PointingHandCursor)
        self.check_btn.clicked.connect(self.check_requested.emit)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)
        layout.addLayout(header)
        layout.addWidget(panel, stretch=1)
        layout.addWidget(self.check_btn, alignment=Qt.AlignCenter)

    def set_image(self, frame):
        self.image_label.show_frame(frame)


class CheckEmbeddingPage(CameraPage):
    back_requested = pyqtSignal()
    approved = pyqtSignal()

    def __init__(self, window):
        super().__init__(window)
        self.embedding = None
        self.streak = 0
        self.verified = False

        self.back_btn = QPushButton("← Back")
        self.back_btn.setObjectName("secondary")
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.back_requested.emit)

        title = QLabel("Verify face")
        title.setObjectName("h1")

        header = QHBoxLayout()
        header.addWidget(self.back_btn, alignment=Qt.AlignTop)
        header.addSpacing(12)
        header.addWidget(title)
        header.addStretch()

        panel = QFrame()
        panel.setObjectName("panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(8, 8, 8, 8)
        panel_layout.addWidget(self.camera_label)

        self.status_label = QLabel("Look at the camera")
        self.status_label.setObjectName("muted")
        self.status_label.setAlignment(Qt.AlignCenter)

        self.approve_btn = QPushButton("Approve && Save")
        self.approve_btn.setCursor(Qt.PointingHandCursor)
        self.approve_btn.setEnabled(False)
        self.approve_btn.clicked.connect(self.approved.emit)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)
        layout.addLayout(header)
        layout.addWidget(panel, stretch=1)
        layout.addWidget(self.status_label)
        layout.addWidget(self.approve_btn, alignment=Qt.AlignCenter)

    def set_embedding(self, embedding):
        self.embedding = embedding
        self.streak = 0
        self.verified = False
        self.approve_btn.setEnabled(False)
        self.status_label.setText("Look at the camera")

    def cam_feed(self):
        frame = self.read_frame()
        if frame is None:
            return

        display = frame.copy()
        face = largest_face(self.window_.face_app.get(frame))

        if face is not None:
            sim = float(np.dot(self.embedding, face.normed_embedding))
            matched = sim >= self.window_.SIMILARITY_THRESHOLD
            self.streak = self.streak + 1 if matched else 0

            color = (0, 255, 0) if matched else (0, 0, 255)
            draw_box(display, face.bbox, f"Similarity: {sim:.3f}", color)
        else:
            self.streak = 0

        needed = self.window_.STREAK_THRESHOLD
        if self.streak >= needed:
            self.verified = True
        if self.verified:
            self.status_label.setText("Face verified")
            self.approve_btn.setEnabled(True)
        else:
            self.status_label.setText(f"Matching: {self.streak}/{needed}")

        self.update_frame(display)


class EnrollWindow(BaseWindow):
    PRODUCT_NAME = "FaceCall Enroll"
    USERS_TABLE_DATA_URL = "admin/users/gui-table/"

    def build_pages(self):
        self.dashboard_page = self.add_page(DashboardPage(self))
        self.enroll_page = self.add_page(EnrollFaceEmbeddingPage(self))
        self.check_page = self.add_page(DetectionCheckPage(self))
        self.check_embedding_page = self.add_page(CheckEmbeddingPage(self))

        self.dashboard_page.enroll_requested.connect(self.open_enroll_page)

        self.enroll_page.back_requested.connect(self.close_enroll_page)
        self.enroll_page.buffer_full.connect(self.on_buffer_full)

        self.check_page.back_requested.connect(
            lambda: self.open_enroll_page(self.enroll_page.user_id)
        )
        self.check_page.check_requested.connect(self.open_check_embedding)

        self.check_embedding_page.back_requested.connect(self.close_check_embedding)
        self.check_embedding_page.approved.connect(self.on_approved)

    @asyncSlot()
    async def on_login_successful(self):
        self.show_loader()
        try:
            await self.dashboard_page.refresh()
        finally:
            self.hide_loader()
        self.show_page(self.dashboard_page)

    @asyncSlot(int)
    async def open_enroll_page(self, user_id):
        self.enroll_page.set_user(user_id)
        self.show_loader()
        try:
            await self.enroll_page.start_camera()
        finally:
            self.hide_loader()
        self.show_page(self.enroll_page)

    def close_enroll_page(self):
        self.enroll_page.stop_camera()
        self.show_page(self.dashboard_page)

    @asyncSlot()
    async def on_buffer_full(self):
        self.show_loader()
        try:
            self.enroll_page.build_embedding()
        finally:
            self.hide_loader()
        self.check_page.set_image(self.enroll_page.buffer[-1])
        self.show_page(self.check_page)

    @asyncSlot()
    async def open_check_embedding(self):
        self.check_embedding_page.set_embedding(self.enroll_page.embedding)
        self.show_loader()
        try:
            await self.check_embedding_page.start_camera()
        finally:
            self.hide_loader()
        self.show_page(self.check_embedding_page)

    def close_check_embedding(self):
        self.check_embedding_page.stop_camera()
        self.show_page(self.check_page)

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
                    msg = (
                        data.get("error")
                        or data.get("detail")
                        or f"Save failed ({resp.status})"
                    )
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
                await self.dashboard_page.load_users()
        finally:
            self.hide_loader()

        if ok:
            self.check_embedding_page.stop_camera()
            self.enroll_page.clear_buffer()
            self.show_page(self.dashboard_page)
            QMessageBox.information(self, "Face Enrollment", "Face embedding saved.")
        else:
            QMessageBox.warning(self, "Face Enrollment", msg)


if __name__ == "__main__":
    run(EnrollWindow)
