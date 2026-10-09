
import sys
import asyncio

import aiohttp
import cv2
import numpy as np

from insightface.app import FaceAnalysis
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget
from qasync import QEventLoop, asyncClose

from anti_spoof import is_face_real


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Configuration
        self.EMBEDDINGS_PATH = "face_embeddings.npz"
        self.SIMILARITY_THRESHOLD = 0.50
        self.CAMERA_INDEX = 0
        self.STREAK_THRESHOLD = 20
        self.SESSION_ID = 1
        self.ENABLE_ANTI_SPOOFING = False

        self.BASE_URL = "http://127.0.0.1:8000"
        self.SESSION_URL = (
            f"{self.BASE_URL}/api/attendance/session/{self.SESSION_ID}/"
        )
        self.RECORD_ATTENDANCE_URL = f"{self.BASE_URL}/api/attendance/"

        self.http_session = None
        self.pending_users = set()
        self.user_ids = {}
        self.recorded_users = {}

        # Consecutive-frame recognition state
        self.state = {
            "label": None,
            "streak": 0,
            "confirmed": False,
        }

        # Load saved ArcFace embeddings
        with np.load(self.EMBEDDINGS_PATH) as data:
            self.known_embeddings = data["embeddings"].astype(np.float32)
            self.known_labels = data["labels"].astype(np.int32)

            # The training script saves names as "ID=Name".
            self.names = {}
            if "names" in data:
                for item in data["names"]:
                    user_id, name = str(item).split("=", 1)
                    self.names[int(user_id)] = name

        if len(self.known_embeddings) == 0:
            raise ValueError("No face embeddings found in the NPZ file.")

        # Normalize embeddings for cosine similarity.
        norms = np.linalg.norm(
            self.known_embeddings, axis=1, keepdims=True
        )
        self.known_embeddings /= np.maximum(norms, 1e-12)

        # Initialize InsightFace (ArcFace recognition model).
        self.face_app = FaceAnalysis(
            name="buffalo_l",
            providers=[
                "CUDAExecutionProvider",
                "CPUExecutionProvider",
            ],
        )
        self.face_app.prepare(ctx_id=0, det_size=(640, 640))

        # Window and camera
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

        # Fetch attendance session users
        attendance_list = self.get_attendance_list()

        if attendance_list is None:
            self.camera_label.setText(
                "Unable to get attendance details"
            )
            self.camera_label.setAlignment(Qt.AlignCenter)
        elif not self.camera.isOpened():
            self.camera_label.setText("Unable to open camera")
            self.camera_label.setAlignment(Qt.AlignCenter)
        else:
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.recognize)
            self.timer.start(30)

    def get_attendance_list(self):
        try:
            response = requests.get(
                self.SESSION_URL,
                timeout=5,
            )
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

            return self.user_ids

        except (requests.RequestException, ValueError) as e:
            print(f"Failed to fetch attendance: {e}")
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
                if response.status not in (200, 201):
                    print(
                        f"Attendance recording failed: "
                        f"{response.status} {await response.text()}"
                    )
                    self.state["confirmed"] = False
                    return False

                result = await response.json()

            self.recorded_users[user_id] = {
                "user_id": user_id,
                "first_name": result.get("first_name", ""),
                "status": result.get("status"),
            }

            print(
                f"Attendance recorded: "
                f"{result.get('first_name', user_id)} "
                f"({result.get('status')})"
            )

            return True

        except (
            aiohttp.ClientError,
            asyncio.TimeoutError,
            ValueError,
        ) as e:
            print(f"Attendance request failed: {e}")
            self.state["confirmed"] = False
            return False

        finally:
            self.pending_users.discard(user_id)

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

        self.camera_label.setPixmap(
            QPixmap.fromImage(image.copy())
        )

    def streak_calculate(self, label):
        state = self.state

        if label is None:
            state["label"] = None
            state["streak"] = 0
            state["confirmed"] = False
            return None

        if state["label"] != label:
            state["label"] = label
            state["streak"] = 1
            state["confirmed"] = False
        else:
            state["streak"] += 1

        if (
            state["streak"] >= self.STREAK_THRESHOLD
            and not state["confirmed"]
        ):
            state["confirmed"] = True
            return state["label"]

        return None

    def is_already_attended(self, user_id):
        user_id = int(user_id)

        if user_id in self.recorded_users:
            return True

        user = self.user_ids.get(user_id)

        return user is not None and user.get("status") is not None

    def recognize(self):
        success, frame = self.camera.read()

        if not success:
            return

        faces = self.face_app.get(frame)

        # No face: reset the consecutive-frame streak.
        if not faces:
            self.streak_calculate(None)
            self.update_frame(frame)
            return

        # Without tracking, process only the largest face in each frame.
        face = max(
            faces,
            key=lambda f: (
                (f.bbox[2] - f.bbox[0])
                * (f.bbox[3] - f.bbox[1])
            ),
        )

        x1, y1, x2, y2 = face.bbox.astype(int)

        # Optional anti-spoofing check.
        if self.ENABLE_ANTI_SPOOFING:
            spoof_label, spoof_confidence = is_face_real(
                frame, {x1, y1, x2, y2}
            )

            if spoof_label != "Real":
                self.streak_calculate(None)

                cv2.rectangle(
                    frame, (x1, y1), (x2, y2), (0, 0, 255), 2
                )
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

        # Extract the normalized ArcFace embedding.
        embedding = face.normed_embedding.astype(np.float32)

        # Compare against all stored embeddings using cosine similarity.
        similarities = self.known_embeddings @ embedding

        best_index = int(np.argmax(similarities))
        best_similarity = float(similarities[best_index])

        user_id = None
        name = "Unknown"
        color = (0, 0, 255)

        if best_similarity >= self.SIMILARITY_THRESHOLD:
            user_id = int(self.known_labels[best_index])

            user = self.user_ids.get(user_id, {})
            name = (
                user.get("first_name")
                or self.names.get(user_id)
                or "Unknown"
            )

            color = (0, 255, 0)

        # Update recognition streak.
        confirmed_id = self.streak_calculate(user_id)

        # Record attendance only after recognition is confirmed.
        if confirmed_id is not None:
            if (
                not self.is_already_attended(confirmed_id)
                and confirmed_id not in self.pending_users
            ):
                self.pending_users.add(confirmed_id)

                asyncio.create_task(
                    self.record_attendance(confirmed_id)
                )

        # Display identity, similarity, and streak.
        cv2.rectangle(
            frame, (x1, y1), (x2, y2), color, 2
        )

        cv2.putText(
            frame,
            f"{name} (ID: {user_id})" if user_id is not None else name,
            (x1, max(y1 - 30, 25)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2,
        )

        cv2.putText(
            frame,
            f"Similarity: {best_similarity:.3f}",
            (x1, max(y1 - 8, 45)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
        )

        if user_id is not None:
            cv2.putText(
                frame,
                f"Streak: {self.state['streak']}/{self.STREAK_THRESHOLD}",
                (x1, y2 + 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
            )

            if self.is_already_attended(user_id):
                cv2.putText(
                    frame,
                    "Attendance recorded",
                    (x1, y2 + 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
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
    import requests

    app = QApplication(sys.argv)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.show()

    with loop:
        loop.run_forever()
