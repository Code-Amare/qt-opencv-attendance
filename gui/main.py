import cv2
import sys
import requests
from ultralytics import YOLO
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QMainWindow,
)
import asyncio
import aiohttp
from qasync import QEventLoop, asyncClose
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
from datetime import datetime
from anti_spoof import is_face_real


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.pending_users = set()
        self.http_session = None

        # Configuration
        self.CAMERA_INDEX = 0
        self.MAX_DISTANCE = 45
        self.STREAK_THRESHOLD = 20
        self.SESSION_ID = 1
        self.user_ids = {}
        self.track_states = {}
        self.recorded_users = {}

        # models
        self.face_recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.face_recognizer.read("face_recognizer.yml")
        self.face_model = YOLO("models/yolov11m-face.pt").to("cuda")

        self.BASE_URL = "http://127.0.0.1:8000"
        self.SESSION_URL = f"{self.BASE_URL}/api/attendance/session/{self.SESSION_ID}/"
        self.RECORD_ATTENDANCE_URL = f"{self.BASE_URL}/api/attendance/"

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

        self.get_attendance_list()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.recognize)
        self.timer.start(30)

    def get_attendance_list(self):
        try:
            response = requests.get(self.SESSION_URL, timeout=5)
            response.raise_for_status()

            data = response.json()

            attendance = data.get("attendance")

            if "attendance" not in data:
                print("Invalid API response: attendance field missing.")
                return None
            self.user_ids = {
                int(user["user_id"]): user
                for user in attendance
                if user.get("user_id") is not None
            }
            return

        except (requests.RequestException, ValueError) as e:
            print(f"Failed to fetch attendance: {e}")
            return None

    async def record_attendance(self, user_id, track_id):
        try:
            # Reuse one asynchronous HTTP session.
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

                    state = self.track_states.get(track_id)
                    if state:
                        state["confirmed"] = False

                    return False

                result = await response.json()

            # Update local state only after a successful API response.
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

        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
            print(f"Attendance request failed: {e}")

            state = self.track_states.get(track_id)
            if state:
                state["confirmed"] = False

            return False

        finally:
            self.pending_users.discard(user_id)

    def update_frame(self, frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channels = frame.shape
        bytes_per_line = channels * width

        image = QImage(
            frame.data,
            width,
            height,
            bytes_per_line,
            QImage.Format_RGB888,
        )
        self.camera_label.setPixmap(QPixmap.fromImage(image.copy()))

    def streak_calculate(self, label, distance, track_id):

        state = self.track_states.setdefault(
            track_id,
            {
                "tracked_streak": 0,
                "reco_label": None,
                "reco_streak": 0,
                "confirmed": False,
            },
        )

        state["tracked_streak"] += 1

        if label is None or distance > self.MAX_DISTANCE:
            state["reco_label"] = None
            state["reco_streak"] = 0
            return None

        if state["reco_label"] != label:
            state["reco_label"] = label
            state["reco_streak"] = 1
            state["confirmed"] = False
        else:
            state["reco_streak"] += 1

        if (
            state["tracked_streak"] > self.STREAK_THRESHOLD
            and state["reco_streak"] > self.STREAK_THRESHOLD
            and not state["confirmed"]
        ):
            state["confirmed"] = True
            return label

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
        processed_image = frame.copy()

        result = self.face_model.track(frame, persist=True, verbose=False)
        boxes = result[0].boxes.xyxy
        track_ids = result[0].boxes.id

        if track_ids is None:
            self.update_frame(processed_image)
            return
        for box, track_id in zip(boxes, track_ids):
            left, top, right, bottom = map(int, box)

            spoof_label, spoof_confidence = is_face_real(frame, box)
            if not spoof_label == "Real":
                cv2.rectangle(
                    processed_image,
                    (left, top),
                    (right, bottom),
                    (0, 0, 255),  # BGR = Green
                    2,
                )
                cv2.putText(
                    processed_image,
                    f"{spoof_label} {spoof_confidence * 100:.1f}%",
                    (left, bottom + 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    2,
                )
                self.update_frame(processed_image)
                continue

            face = frame[top:bottom, left:right]
            face = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
            face = cv2.resize(face, (200, 200))
            label, distance = self.face_recognizer.predict(face)

            track_id = int(track_id.item())

            if distance > self.MAX_DISTANCE:
                name = "Unknown"
                user_id = None
                streak_label = None
                is_already_recorded = False
            else:
                label = int(label)

                user_id = label

                streak_label = self.streak_calculate(
                    label, distance, track_id
                )

                user = self.user_ids.get(user_id, {})
                name = user.get("first_name") or "Not set"

                is_already_recorded = self.is_already_attended(user_id)

                if streak_label is not None and not is_already_recorded:
                    if user_id not in self.pending_users:
                        self.pending_users.add(user_id)

                        asyncio.create_task(
                            self.record_attendance(user_id, track_id)
                        )

            if is_already_recorded:
                cv2.rectangle(
                    processed_image,
                    (left, top),
                    (right, bottom),
                    (0, 255, 0),
                    2,
                )
            else:
                cv2.rectangle(
                    processed_image,
                    (left, top),
                    (right, bottom),
                    (255, 0, 0),
                    2,
                )

            cv2.putText(
                processed_image,
                name + " | " + str(int(distance)) + " | track_id=" + str(int(track_id)),
                (left, bottom + 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2,
            )
        self.update_frame(processed_image)

    @asyncClose
    async def closeEvent(self, event):
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
