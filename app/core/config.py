import os

# DeepFace / TensorFlow compatibility: Force legacy Keras 2.
# TensorFlow 2.16+ defaults to Keras 3, which breaks DeepFace's ArcFace and RetinaFace models.
# MUST be set before any TensorFlow / Keras imports happen elsewhere in the app.
os.environ["TF_USE_LEGACY_KERAS"] = "1"

from pathlib import Path
from dotenv import load_dotenv

# Load variables from .env into the process environment.
# override=False so real env vars (e.g. set at the shell / CI) always win.
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=_ENV_FILE, override=False)

# ─────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────
DATABASE_URL: str = os.environ["DBOS_SYSTEM_DATABASE_URL"]

# ─────────────────────────────────────────────
# DBOS
# ─────────────────────────────────────────────
DBOS_APP_NAME: str = os.environ.get("DBOS_APP_NAME", "face-attendance-app")

# ─────────────────────────────────────────────
# File Upload
# ─────────────────────────────────────────────
UPLOAD_DIR: str = os.environ.get("UPLOAD_DIR", "./uploads")

# ─────────────────────────────────────────────
# Face Recognition
# ─────────────────────────────────────────────
DEFAULT_DETECTOR_BACKEND: str = os.environ.get("DEFAULT_DETECTOR_BACKEND", "retinaface")
RECOGNITION_MODEL: str = os.environ.get("RECOGNITION_MODEL", "ArcFace")
EMBEDDING_DIM: int = int(os.environ.get("EMBEDDING_DIM", "512"))
COSINE_DISTANCE_THRESHOLD: float = float(os.environ.get("COSINE_DISTANCE_THRESHOLD", "0.68"))

# ─────────────────────────────────────────────
# Liveness Detection  (MediaPipe Tasks API)
# ─────────────────────────────────────────────
MAX_LIVENESS_FRAMES: int = int(os.environ.get("MAX_LIVENESS_FRAMES", "60"))
MEDIAPIPE_MIN_DETECTION_CONFIDENCE: float = float(
    os.environ.get("MEDIAPIPE_MIN_DETECTION_CONFIDENCE", "0.5")
)
# Path to the face_landmarker.task model bundle.
# Download from: https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
FACE_LANDMARKER_MODEL_PATH: str = os.environ.get(
    "FACE_LANDMARKER_MODEL_PATH",
    "./models/face_landmarker.task",
)
