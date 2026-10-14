# FaceCall

Desktop face-recognition attendance system. A PyQt5 client talks to a local Django REST API. Face detection and embeddings come from InsightFace (`buffalo_l`).

## Project structure

```
qt-opencv-attendance/
├── backend/              Django REST API
│   ├── api/
│   ├── attendance/
│   ├── core/
│   ├── users/
│   ├── manage.py
│   └── .env
├── gui/                  PyQt5 desktop apps
│   ├── collect_faces.py  Enrollment app
│   ├── run_attendance.py Attendance app
│   ├── main.py           Standalone prototype (no login)
│   ├── utils.py          TitleBar, icon_from_svg, get_image, default_avatar
│   ├── anti_spoof.py     is_face_real(frame, bbox)
│   ├── assets/
│   └── face_embeddings.npz   Created by "Download & save .npz"
└── LICENSE
```

## Apps

| File | Purpose |
|------|---------|
| `gui/collect_faces.py` | Log in, view users, capture a face, verify it, and save the embedding to the backend. |
| `gui/run_attendance.py` | Log in, load a session and the embeddings, then record attendance from the camera. |
| `gui/main.py` | Prototype with no login. Reads a local `.npz` and has a hardcoded `SESSION_ID`. |

## Features

- Login with username or email, using JWT and CSRF tokens
- Enrollment: captures 15 good face crops, averages them into one normalized embedding, then verifies live before saving
- Attendance: the same face must match for 20 consecutive frames before it is recorded
- Optional anti-spoofing (`ENABLE_ANTI_SPOOFING`)
- Load embeddings from the server or from a local `face_embeddings.npz`
- "Download & save .npz" button to keep an offline copy

## Requirements

- Python 3.10+
- A webcam
- The backend running at `http://localhost:8000/api/`

```bash
pip install insightface onnxruntime opencv-python numpy PyQt5 qasync aiohttp pyqtspinner requests
```

For GPU use, install `onnxruntime-gpu` instead. It falls back to CPU automatically.

### Based on your GPU version

If it is still falling to CPU use this command `python -m pip install --upgrade "onnxruntime-gpu[cuda,cudnn]==1.31.0"`

## Run

Start the backend:

```bash
cd backend
python manage.py runserver
```

Start an app (run from `gui/`, since file paths are relative):

```bash
cd gui
python collect_faces.py
python run_attendance.py
```

The first launch downloads the `buffalo_l` model (about 280 MB).

## Configuration

Edit the constants in `MainWindow.__init__`:

| Setting | Default | Meaning |
|---------|---------|---------|
| `BASE_URL` | `http://localhost:8000/api/` | Backend root |
| `CAMERA_INDEX` | `0` | Which camera to use |
| `SIMILARITY_THRESHOLD` | `0.50` | Minimum cosine similarity for a match |
| `STREAK_THRESHOLD` | `20` | Consecutive matching frames needed |
| `ENABLE_ANTI_SPOOFING` | `True` / `False` | Reject printed photos and screens |

## Usage

**Enroll a face**

1. Log in.
2. Click **Enroll Face** on a user row.
3. Look at the camera until 15 captures are collected.
4. Click **Check Detection**, then look at the camera until it says "Face verified".
5. Click **Approve & Save**.

**Record attendance**

1. Log in.
2. Enter a session ID.
3. Choose how to load embeddings:
   - **Load embedding locally** reads `face_embeddings.npz`.
   - **Load new embedding** downloads from the server.
   - **Download & save .npz** saves a fresh local copy.
4. Face the camera. A person is recorded after 20 consecutive matching frames.

Box colors: green is a match or recorded, yellow is late, red is unknown or absent, orange is a user not in this session.

## API endpoints

| Method | Endpoint | Used for |
|--------|----------|----------|
| POST | `users/login/` | Login |
| POST | `users/refresh/` | Token refresh |
| GET | `attendance/data/table` | Users table |
| POST | `users/face-embedding/add/<user_id>/` | Save an embedding |
| GET | `users/face-embedding/download/` | Download the `.npz` (`embeddings`, `labels`) |
| GET | `attendance/session/<id>/` | Session attendance list |
| POST | `attendance/` | Record attendance (`user_id`, `session_id`) |
| GET | `users/recognition-map/` | `main.py` only |

## License

See [LICENSE](LICENSE).
