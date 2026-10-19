import common
import asyncio
import io
import os
import zipfile
from datetime import datetime
import aiohttp
import numpy as np
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qasync import asyncSlot
from common import (
    FONT,
    MESSAGE_COLORS,
    BaseWindow,
    CameraPage,
    draw_box,
    fmt_dt,
    largest_face,
    run,
)


class SessionsPage(QWidget):
    session_loaded = pyqtSignal()
    EMBEDDINGS_PATH = "face_embeddings.npz"
    STATUS_COLORS = {
        "active": "#10B981",
        "completed": "#3B82F6",
        "cancelled": "#EF4444",
    }

    def __init__(self, window):
        super().__init__()
        self.window_ = window
        self.sessions = []

        title = QLabel("Start attendance")
        title.setObjectName("h1")
        subtitle = QLabel("Choose a session and where to load face embeddings from.")
        subtitle.setObjectName("muted")

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("secondary")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(4)
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles)
        header.addStretch()
        header.addWidget(self.refresh_btn, alignment=Qt.AlignTop)

        # ---- sessions table ----
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["NAME", "STARTS", "ENDS", "STATUS"])
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(52)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setShowGrid(False)
        head = self.table.horizontalHeader()
        head.setHighlightSections(False)
        head.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in (1, 2, 3):
            head.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.table.itemSelectionChanged.connect(self.update_start_state)
        self.table.cellDoubleClicked.connect(lambda *_: self.on_start_clicked())

        # ---- embeddings source ----
        self.local_radio = QRadioButton("Use local file")
        self.download_radio = QRadioButton("Download latest from server")
        group = QButtonGroup(self)
        group.addButton(self.local_radio)
        group.addButton(self.download_radio)

        self.local_hint = QLabel("")
        self.local_hint.setObjectName("subtle")

        self.save_check = QCheckBox("Save a local copy after downloading")
        self.download_radio.toggled.connect(self.save_check.setEnabled)

        panel = QFrame()
        panel.setObjectName("panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(16, 14, 16, 14)
        panel_layout.setSpacing(8)
        source_label = QLabel("Face embeddings")
        source_label.setObjectName("field")
        panel_layout.addWidget(source_label)
        panel_layout.addWidget(self.local_radio)
        panel_layout.addWidget(self.local_hint)
        panel_layout.addWidget(self.download_radio)
        panel_layout.addWidget(self.save_check)

        # ---- footer ----
        self.message = QLabel("")
        self.message.setWordWrap(True)

        self.start_btn = QPushButton("Start attendance")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.on_start_clicked)

        footer = QHBoxLayout()
        footer.addWidget(self.message, stretch=1)
        footer.addWidget(self.start_btn)

        content = QWidget()
        content.setMaximumWidth(960)
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)
        content_layout.addLayout(header)
        content_layout.addWidget(self.table, stretch=1)
        content_layout.addWidget(panel)
        content_layout.addLayout(footer)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.addWidget(content, alignment=Qt.AlignHCenter)

        self.update_local_state()
        self.save_check.setEnabled(self.download_radio.isChecked())

    # ---------- helpers ----------
    def set_message(self, text, kind="error"):
        color = MESSAGE_COLORS.get(kind, MESSAGE_COLORS["error"])
        self.message.setStyleSheet(f"color: {color}; font-size: {FONT['message']}px;")
        self.message.setText(text)

    def update_local_state(self):
        if os.path.exists(self.EMBEDDINGS_PATH):
            updated = datetime.fromtimestamp(
                os.path.getmtime(self.EMBEDDINGS_PATH)
            ).strftime("%b %d, %H:%M")
            self.local_radio.setEnabled(True)
            self.local_hint.setText(f"{self.EMBEDDINGS_PATH} · updated {updated}")
            if not self.download_radio.isChecked():
                self.local_radio.setChecked(True)
        else:
            self.local_radio.setEnabled(False)
            self.local_hint.setText(f"{self.EMBEDDINGS_PATH} not found")
            self.download_radio.setChecked(True)

    def selected_session(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        row = rows[0].row()
        return self.sessions[row] if 0 <= row < len(self.sessions) else None

    def update_start_state(self):
        session = self.selected_session()
        if session is None:
            self.start_btn.setEnabled(False)
            self.set_message("")
        elif str(session.get("status")).lower() != "active":
            self.start_btn.setEnabled(False)
            self.set_message("Only active sessions can record attendance.", "warn")
        else:
            self.start_btn.setEnabled(True)
            self.set_message("")

    def fill_table(self):
        self.table.setRowCount(len(self.sessions))
        for row, s in enumerate(self.sessions):
            status = str(s.get("status", "")).lower()
            cells = [
                s.get("name", ""),
                fmt_dt(s.get("started_at")),
                fmt_dt(s.get("ended_at")),
                status.capitalize(),
            ]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if col == 3:
                    item.setForeground(
                        QColor(self.STATUS_COLORS.get(status, "#B0B0B5"))
                    )
                self.table.setItem(row, col, item)

    # ---------- API ----------
    async def fetch_sessions(self):
        async with self.window_.session.get("admin/sessions/") as resp:
            if resp.status == 404:  # the backend answers 404 when there are none
                return []
            try:
                data = await resp.json()
            except aiohttp.ContentTypeError:
                data = {}
            if resp.status >= 400:
                raise ValueError(
                    data.get("error") or data.get("detail") or "Failed to load sessions"
                )
        sessions = data.get("sessions")
        if not isinstance(sessions, list):
            raise ValueError("Invalid sessions response")
        return sessions

    async def fetch_recorded(self, session_id):
        async with self.window_.session.get(
            f"attendance/session/{session_id}/"
        ) as resp:
            try:
                data = await resp.json()
            except aiohttp.ContentTypeError:
                data = {}
            if resp.status >= 400:
                raise ValueError(
                    data.get("error") or data.get("detail") or "Invalid session"
                )
        attendance = data.get("attendance")
        if not isinstance(attendance, list):
            raise ValueError(data.get("error") or "Invalid session response")
        return {
            int(u["user_id"]): u for u in attendance if u.get("user_id") is not None
        }

    async def fetch_embeddings(self):
        async with self.window_.session.get(
            self.window_.DOWNLOAD_FACE_EMBEDDINGS
        ) as resp:
            resp.raise_for_status()
            return await resp.read()

    def read_local(self):
        with np.load(self.EMBEDDINGS_PATH) as data:
            self.window_.set_embeddings(data["embeddings"], data["labels"])

    def read_bytes(self, content):
        with np.load(io.BytesIO(content)) as data:
            self.window_.set_embeddings(data["embeddings"], data["labels"])

    # ---------- actions ----------
    @asyncSlot()
    async def refresh(self):
        previous = self.selected_session()
        self.set_message("")
        self.update_local_state()

        self.window_.show_loader()
        try:
            self.sessions = await self.fetch_sessions()
        except (aiohttp.ClientError, ValueError) as e:
            self.sessions = []
            self.set_message(str(e))
        finally:
            self.window_.hide_loader()

        self.fill_table()
        if previous:
            for row, s in enumerate(self.sessions):
                if s.get("id") == previous.get("id"):
                    self.table.selectRow(row)
                    break
        self.update_start_state()

    @asyncSlot()
    async def on_start_clicked(self):
        session = self.selected_session()
        if session is None:
            self.set_message("Select a session first.", "warn")
            return
        if str(session.get("status")).lower() != "active":
            self.set_message("Only active sessions can record attendance.", "warn")
            return

        use_download = self.download_radio.isChecked()
        self.window_.show_loader()
        try:
            recorded = await self.fetch_recorded(session["id"])
            if use_download:
                content = await self.fetch_embeddings()
                self.read_bytes(content)  # validates before anything is saved
                if self.save_check.isChecked():
                    with open(self.EMBEDDINGS_PATH, "wb") as f:
                        f.write(content)
            else:
                self.read_local()
        except (
            aiohttp.ClientError,
            OSError,
            KeyError,
            ValueError,
            zipfile.BadZipFile,
        ) as e:
            self.set_message(str(e))
            return
        finally:
            self.window_.hide_loader()

        self.update_local_state()
        self.window_.session_id = session["id"]
        self.window_.session_name = session.get("name", "")
        self.window_.recorded_users = recorded
        self.set_message("")
        self.session_loaded.emit()


class RecordAttendancePage(CameraPage):
    back_requested = pyqtSignal()

    def __init__(self, window):
        super().__init__(window)
        self.label = None
        self.streak = 0
        self.pending = set()
        self._tasks = set()

        self.back_btn = QPushButton("← Back")
        self.back_btn.setObjectName("secondary")
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.back_requested.emit)

        self.title_label = QLabel("")
        self.title_label.setObjectName("h1")
        self.id_label = QLabel("")
        self.id_label.setObjectName("subtle")

        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.addWidget(self.title_label)
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

        self.status_label = QLabel("Look at the camera")
        self.status_label.setObjectName("muted")
        self.status_label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)
        layout.addLayout(header)
        layout.addWidget(panel, stretch=1)
        layout.addWidget(self.status_label)

    def reset(self):
        self.label = None
        self.streak = 0
        self.pending.clear()
        self.title_label.setText(self.window_.session_name or "Session")
        self.id_label.setText(f"Session ID: {self.window_.session_id}")
        self.status_label.setText("Look at the camera")

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
        frame = self.read_frame()
        if frame is None:
            return

        display = frame.copy()
        face = largest_face(self.window_.face_app.get(frame))

        if face is None:
            self.update_streak(None)
            self.update_frame(display)
            return

        if self.is_spoof(frame, display, face.bbox):
            self.update_streak(None)
            self.update_frame(display)
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

        draw_box(display, face.bbox, text, color)
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
                        data.get("error")
                        or data.get("detail")
                        or f"Failed ({resp.status})"
                    )
                    return

            status = (data.get("attendance") or {}).get("status")
            if status is None:
                self.status_label.setText("Server returned no status")
                return

            name = data.get("first_name") or self.name(user_id)
            self.window_.recorded_users[user_id] = {
                "user_id": user_id,
                "first_name": name,
                "status": status,
            }
            self.status_label.setText(f"Recorded: {name} ({status})")

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self.status_label.setText(f"Request failed: {e}")
        finally:
            self.pending.discard(user_id)
            if self.label == user_id:
                self.label, self.streak = None, 0


class CheckInWindow(BaseWindow):
    PRODUCT_NAME = "FaceCall Check-in"
    SET_ATTENDANCE = "attendance/"
    DOWNLOAD_FACE_EMBEDDINGS = "users/face-embedding/download/"

    def __init__(self):
        super().__init__()
        self.session_id = None
        self.session_name = ""
        self.recorded_users = {}
        self.known_embeddings = None
        self.known_labels = None

    def build_pages(self):
        self.sessions_page = self.add_page(SessionsPage(self))
        self.record_page = self.add_page(RecordAttendancePage(self))

        self.sessions_page.session_loaded.connect(self.open_record_attendance)
        self.record_page.back_requested.connect(self.close_record_attendance)

    def on_login_successful(self):
        self.show_page(self.sessions_page)
        self.sessions_page.refresh()

    @asyncSlot()
    async def open_record_attendance(self):
        self.record_page.reset()
        self.show_loader()
        try:
            await self.record_page.start_camera()
        finally:
            self.hide_loader()
        self.show_page(self.record_page)

    def close_record_attendance(self):
        self.record_page.stop_camera()
        self.show_page(self.sessions_page)
        self.sessions_page.refresh()

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


if __name__ == "__main__":
    run(CheckInWindow)
