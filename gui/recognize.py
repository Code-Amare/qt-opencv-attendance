
from ultralytics import YOLO
import cv2
import time
import requests

from anti_spoof import is_face_real


# Models
face_recognizer = cv2.face.LBPHFaceRecognizer_create()
face_recognizer.read("face_recognizer.yml")

face_model = YOLO("models/yolov11m-face.pt").to("cuda")


# Configuration
CAMERA_INDEX = 0
MAX_DISTANCE = 45
STREAK_THRESHOLD = 20
SESSION_ID = 1

BASE_URL = "http://127.0.0.1:8000"
SESSION_URL = f"{BASE_URL}/api/attendance/session/{SESSION_ID}/"

# Adjust this to match your actual POST endpoint.
RECOGNIZE_URL = (
    f"{BASE_URL}/api/attendance/sessions/"
    f"{SESSION_ID}/recognize/"
)

SESSION_REFRESH_INTERVAL = 3

prev_time = time.perf_counter()
last_session_refresh = 0

track_states = {}
attendance_data = {}
session_finalized = False


def get_attendance_list():
    try:
        response = requests.get(SESSION_URL, timeout=5)
        response.raise_for_status()

        data = response.json()

        if "attendance" not in data:
            print("Invalid API response: attendance field missing.")
            return None

        return data

    except (requests.RequestException, ValueError) as e:
        print(f"Failed to fetch attendance: {e}")
        return None


def refresh_attendance(force=False):
    global attendance_data, session_finalized
    global last_session_refresh

    now = time.perf_counter()

    if (
        not force
        and now - last_session_refresh < SESSION_REFRESH_INTERVAL
    ):
        return True

    data = get_attendance_list()

    if data is None:
        return False

    session_finalized = (
        data.get("finalized", False)
        or data.get("session_status") in ("completed", "cancelled")
    )

    attendance_data = {
        item["user_id"]: item
        for item in data["attendance"]
    }

    last_session_refresh = now

    return True


def is_already_recorded(user_id):
    """
    True when this user already has a successful attendance status.
    """
    record = attendance_data.get(user_id)

    if not record:
        return False

    return record.get("status") in (
        "present",
        "attended",
        "late",
    )


def record_attendance(user_id):
    """
    Submit attendance to Django.

    Update local state only when the server confirms success.
    """
    try:
        response = requests.post(
            RECOGNIZE_URL,
            json={"user_id": user_id},
            timeout=5,
        )

        if response.status_code not in (200, 201):
            print(
                f"Attendance recording failed: "
                f"{response.status_code} {response.text}"
            )
            return False

        result = response.json()

        attendance_data[user_id] = {
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

    except (requests.RequestException, ValueError) as e:
        print(f"Attendance request failed: {e}")
        return False


def recognize_face(face_recognizer, processed_image, frame, box):
    """
    Recognize a face using LBPH and draw its result.
    """
    left, top, right, bottom = box

    height, width = frame.shape[:2]

    left = max(0, min(left, width))
    right = max(0, min(right, width))
    top = max(0, min(top, height))
    bottom = max(0, min(bottom, height))

    if right <= left or bottom <= top:
        return None, float("inf"), processed_image

    face = frame[top:bottom, left:right]

    if face.size == 0:
        return None, float("inf"), processed_image

    face = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    face = cv2.resize(face, (200, 200))

    label, distance = face_recognizer.predict(face)

    if distance > MAX_DISTANCE:
        display_name = "Unknown"
        label = None
    else:
        display_name = str(label)

    cv2.rectangle(
        processed_image,
        (left, top),
        (right, bottom),
        (255, 0, 0),
        2,
    )

    cv2.putText(
        processed_image,
        f"{display_name} | {int(distance)}",
        (left, max(top - 10, 20)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
    )

    return label, distance, processed_image


def streak_calculate(label, distance, track_id):
    """
    Count consecutive valid recognition frames per track.

    Returns the confirmed LBPH label after the threshold is reached.
    """
    state = track_states.setdefault(
        track_id,
        {
            "tracked_streak": 0,
            "reco_label": None,
            "reco_streak": 0,
            "confirmed": False,
        },
    )

    state["tracked_streak"] += 1

    if label is None or distance > MAX_DISTANCE:
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
        state["tracked_streak"] > STREAK_THRESHOLD
        and state["reco_streak"] > STREAK_THRESHOLD
        and not state["confirmed"]
    ):
        state["confirmed"] = True
        return label

    return None


def recognizer(users_id, frame):
    """
    Process one frame.

    users_id must map LBPH labels to Django user IDs.
    Example: {1: 12, 2: 18}
    """
    global prev_time

    processed_image = frame.copy()

    # Check the session before running YOLO tracking.
    if not refresh_attendance():
        cv2.putText(
            processed_image,
            "Attendance server unavailable",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2,
        )
        cv2.imshow("cam", processed_image)
        return processed_image

    if session_finalized:
        cv2.putText(
            processed_image,
            "Attendance session completed",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )
        cv2.imshow("cam", processed_image)
        return processed_image

    result = face_model.track(
        frame,
        persist=True,
        verbose=False,
    )

    boxes = result[0].boxes

    if boxes is None or boxes.id is None:
        # Strict consecutive-frame behavior: no tracked faces
        # means all existing streaks are invalidated.
        track_states.clear()
        cv2.imshow("cam", processed_image)
        return processed_image

    detected_track_ids = set()

    for box, track_id_tensor in zip(boxes.xyxy, boxes.id):
        track_id = int(track_id_tensor.item())
        detected_track_ids.add(track_id)

        left, top, right, bottom = map(int, box.tolist())

        # Anti-spoofing must pass before recognition.
        spoof_label, spoof_confidence = is_face_real(frame, box)

        if spoof_label != "Real":
            state = track_states.get(track_id)

            if state:
                state["tracked_streak"] = 0
                state["reco_label"] = None
                state["reco_streak"] = 0
                state["confirmed"] = False

            cv2.rectangle(
                processed_image,
                (left, top),
                (right, bottom),
                (0, 0, 255),
                2,
            )

            cv2.putText(
                processed_image,
                f"{spoof_label} {spoof_confidence * 100:.1f}%",
                (left, max(top - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2,
            )
            continue

        # If a track has already been confirmed, don't run LBPH again.
        state = track_states.get(track_id)

        if state and state["confirmed"]:
            continue

        label, distance, processed_image = recognize_face(
            face_recognizer,
            processed_image,
            frame,
            (left, top, right, bottom),
        )

        confirmed_label = streak_calculate(
            label,
            distance,
            track_id,
        )

        if confirmed_label is None:
            continue

        # Map the LBPH label to the Django user ID.
        user_id = users_id.get(int(confirmed_label))

        if user_id is None:
            print(f"No Django user mapping for label {confirmed_label}")
            continue

        user_id = int(user_id)

        # Attendance might already have been recorded for this user
        # by another track or another camera.
        if is_already_recorded(user_id):
            continue

        # Only mark the track as finished after successful submission.
        if record_attendance(user_id):
            print(
                f"Confirmed label: {confirmed_label} | "
                f"Django user ID: {user_id} | "
                f"Track ID: {track_id}"
            )

    # Discard streaks belonging to tracks that disappeared this frame.
    for track_id in list(track_states):
        if track_id not in detected_track_ids:
            del track_states[track_id]

    # FPS display
    now = time.perf_counter()
    fps = 1 / max(now - prev_time, 1e-9)
    prev_time = now

    cv2.putText(
        processed_image,
        f"FPS: {fps:.1f}",
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2,
    )

    cv2.imshow("cam", processed_image)

    return processed_image



if __name__ == "__main__":
    # Example: LBPH label -> Django user ID
    users_id = {
        1: 1,
        2: 2,
        3: 3,
    }

    if refresh_attendance(force=True):
        if not session_finalized:
            print("This attendance session is already completed.")
        else:
            camera = cv2.VideoCapture(CAMERA_INDEX)

            try:
                while camera.isOpened():
                    success, frame = camera.read()

                    if not success:
                        print("Failed to read camera frame.")
                        break

                    recognizer(users_id, frame)

                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

            finally:
                camera.release()
                cv2.destroyAllWindows()
