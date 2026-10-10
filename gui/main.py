import sys
import json
import asyncio

import aiohttp
import cv2
import numpy as np
import requests

from insightface.app import FaceAnalysis
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget
from qasync import QEventLoop, asyncClose

from anti_spoof import is_face_real
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QIcon, QPixmap, QPainter
from PyQt5.QtCore import Qt, QByteArray

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

svg = """
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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.EMBEDDINGS_PATH = "face_embeddings.npz"
        self.SIMILARITY_THRESHOLD = 0.50
        self.CAMERA_INDEX = 0
        self.STREAK_THRESHOLD = 100
        self.SESSION_ID = 1
        self.ENABLE_ANTI_SPOOFING = True

        self.BASE_URL = "http://127.0.0.1:8000"
        self.RECOGNITION_MAP_URL = f"{self.BASE_URL}/api/users/recognition-map/"
        self.SESSION_URL = f"{self.BASE_URL}/api/attendance/session/{self.SESSION_ID}/"
        self.RECORD_ATTENDANCE_URL = f"{self.BASE_URL}/api/attendance/"

        self.http_session = None
        self.pending_users = set()
        self.user_ids = {}
        self.names = {}
        self.recorded_users = {}

        self.state = {
            "label": None,
            "streak": 0,
            "confirmed": True,
        }

        with np.load(self.EMBEDDINGS_PATH) as data:
            self.known_embeddings = data["embeddings"].astype(np.float32)
            self.known_labels = data["labels"].astype(np.int32)

        if len(self.known_embeddings) == 0:
            raise ValueError("No face embeddings found in the NPZ file.")

        if len(self.known_embeddings) != len(self.known_labels):
            raise ValueError("The number of embeddings and labels does not match.")

        norms = np.linalg.norm(self.known_embeddings, axis=1, keepdims=True)
        self.known_embeddings /= np.maximum(norms, 1e-12)

        self.face_app = FaceAnalysis(
            name="buffalo_l",
            providers=[
                "CUDAExecutionProvider",
                "CPUExecutionProvider",
            ],
        )
        self.face_app.prepare(ctx_id=0, det_size=(640, 640))

        self.setWindowTitle("Face Recognition Attendance System")
        self.setGeometry(0, 0, 1280, 720)

        self.camera = cv2.VideoCapture(self.CAMERA_INDEX)

        self.camera_label = QLabel()
        self.camera_label.setMinimumSize(640, 480)
        self.camera_label.setScaledContents(True)

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(self.camera_label)
        self.setCentralWidget(central_widget)

        attendance_list = self.get_attendance_list()

        if attendance_list is None:
            self.camera_label.setText("Unable to get attendance details")
            self.camera_label.setAlignment(Qt.AlignCenter)

        elif not self.camera.isOpened():
            self.camera_label.setText("Unable to open camera")
            self.camera_label.setAlignment(Qt.AlignCenter)

        else:
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.recognize)
            self.timer.start(30)

    def get_status(self, user_id):
        user = self.recorded_users.get(int(user_id))

        if user is None:
            return None

        return user.get("status")

    def get_attendance_list(self):
        try:
            response = requests.get(self.SESSION_URL, timeout=5)
            response.raise_for_status()

            data = response.json()
            attendance = data.get("attendance")

            if not isinstance(attendance, list):
                print("Invalid API response: attendance list missing.")
                return None

            self.user_ids = {
                int(user["user_id"]): user
                for user in attendance
                if user.get("user_id") is not None
            }
            self.recorded_users = self.user_ids

            response = requests.get(self.RECOGNITION_MAP_URL, timeout=5)
            response.raise_for_status()

            users = response.json().get("users", [])

            self.names = {
                int(user["id"]): user["first_name"]
                for user in users
                if user.get("id") is not None
            }

            print(f"Loaded {len(self.names)} users from recognition map.")
            print(f"Loaded {len(self.user_ids)} session attendance records.")

            return self.user_ids

        except (requests.RequestException, ValueError) as e:
            print(f"Failed to fetch attendance or recognition map: {e}")
            return None

    async def record_attendance(self, user_id):
        try:
            if self.http_session is None or self.http_session.closed:
                self.http_session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=5)
                )

            async with self.http_session.post(
                self.RECORD_ATTENDANCE_URL,
                json={
                    "user_id": user_id,
                    "session_id": self.SESSION_ID,
                },
            ) as response:
                response_text = await response.text()

                if response.status not in (200, 201):
                    print(
                        f"Attendance recording failed: "
                        f"{response.status} {response_text}"
                    )
                    return False

                try:
                    result = json.loads(response_text)
                except ValueError:
                    print(f"Invalid attendance API response: {response_text}")
                    return False

            status = result.get("attendance").get("status")

            if status is None:
                print(f"Attendance API returned no status. Response: {result}")
                return False

            self.recorded_users[user_id] = {
                "user_id": user_id,
                "first_name": result.get("first_name", self.names.get(user_id, "")),
                "status": status,
            }
            print(self.recorded_users)

            print(
                f"Attendance recorded: "
                f"{result.get('first_name', self.names.get(user_id, user_id))} "
                f"({status})"
            )

            return True

        except (
            aiohttp.ClientError,
            asyncio.TimeoutError,
            ValueError,
        ) as e:
            print(f"Attendance request failed: {e}")
            return False

        finally:
            self.pending_users.discard(user_id)

            if self.state["label"] == user_id:
                self.state["label"] = None
                self.state["streak"] = 0
                self.state["confirmed"] = False

    def update_frame(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channels = rgb_frame.shape
        bytes_per_line = channels * width

        image = QImage(
            rgb_frame.data,
            width,
            height,
            bytes_per_line,
            QImage.Format_RGB888,
        )

        self.camera_label.setPixmap(QPixmap.fromImage(image.copy()))

    def streak_calculate(self, label):
        state = self.state

        if label is None:
            state["label"] = None
            state["streak"] = 0
            state["confirmed"] = False
            return None

        if state["confirmed"] and state["label"] == label:
            return None

        if state["label"] != label:
            state["label"] = label
            state["streak"] = 1
            state["confirmed"] = False
        else:
            state["streak"] += 1

        if state["streak"] >= self.STREAK_THRESHOLD:
            state["confirmed"] = True
            return state["label"]

        return None

    def is_already_attended(self, user_id):
        return self.get_status(user_id) is not None

    def get_status_color(self, status):
        status = str(status).lower()

        if status == "absent":
            return (0, 0, 255)

        if status == "late":
            return (0, 255, 255)

        return (0, 255, 0)

    def draw_face_info(self, frame, box, name, user_id, similarity, color):
        x1, y1, x2, y2 = box

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        display_name = f"{name} (ID: {user_id})" if user_id is not None else name

        cv2.putText(
            frame,
            display_name,
            (x1, max(y1 - 30, 25)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2,
        )

        cv2.putText(
            frame,
            f"Similarity: {similarity:.3f}",
            (x1, max(y1 - 8, 45)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
        )

    def recognize(self):
        success, frame = self.camera.read()

        if not success:
            return

        faces = self.face_app.get(frame)

        if not faces:
            self.streak_calculate(None)
            self.update_frame(frame)
            return

        face = max(
            faces,
            key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
        )

        x1, y1, x2, y2 = face.bbox.astype(int)
        box = (x1, y1, x2, y2)

        if self.ENABLE_ANTI_SPOOFING:
            spoof_label, spoof_confidence = is_face_real(frame, [x1, y1, x2, y2])

            if spoof_label != "Real":
                self.streak_calculate(None)

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

        embedding = face.normed_embedding.astype(np.float32)

        similarities = self.known_embeddings @ embedding

        best_index = int(np.argmax(similarities))
        best_similarity = float(similarities[best_index])

        user_id = None
        name = "Unknown"
        color = (0, 0, 255)

        if best_similarity >= self.SIMILARITY_THRESHOLD:
            candidate_id = int(self.known_labels[best_index])

            if candidate_id in self.names and candidate_id in self.recorded_users:
                user_id = candidate_id
                name = self.names[user_id]
                color = (0, 255, 0)

        if user_id is not None and self.is_already_attended(user_id):
            status = self.get_status(user_id)
            status_color = self.get_status_color(status)

            self.state["label"] = user_id
            self.state["streak"] = 0
            self.state["confirmed"] = True

            self.draw_face_info(frame, box, name, user_id, best_similarity, status_color)

            cv2.putText(
                frame,
                f"Status: {status}",
                (x1, min(y2 + 25, frame.shape[0] - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                status_color,
                2,
            )

            self.update_frame(frame)
            return

        confirmed_id = None

        if user_id is None:
            self.streak_calculate(None)

        elif user_id in self.pending_users:
            self.state["label"] = user_id
            self.state["streak"] = 0
            self.state["confirmed"] = True

        else:
            confirmed_id = self.streak_calculate(user_id)

        if confirmed_id is not None:
            if (
                not self.is_already_attended(confirmed_id)
                and confirmed_id not in self.pending_users
            ):
                self.pending_users.add(confirmed_id)
                asyncio.create_task(self.record_attendance(confirmed_id))

        self.draw_face_info(frame, box, name, user_id, best_similarity, color)

        if user_id is not None:
            if user_id in self.pending_users:
                status_text = "Recording attendance..."
            else:
                status_text = f"Streak: {self.state['streak']}/{self.STREAK_THRESHOLD}"

            cv2.putText(
                frame,
                status_text,
                (x1, min(y2 + 25, frame.shape[0] - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
            )

        self.update_frame(frame)

    @asyncClose
    async def closeEvent(self, event):
        if hasattr(self, "timer"):
            self.timer.stop()

        if self.camera.isOpened():
            self.camera.release()

        if self.http_session and not self.http_session.closed:
            await self.http_session.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.show()

    with loop:
        loop.run_forever()