import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from deepface import DeepFace
from dbos import DBOS

from app.core.config import (
    MAX_LIVENESS_FRAMES,
    MEDIAPIPE_MIN_DETECTION_CONFIDENCE,
    FACE_LANDMARKER_MODEL_PATH,
    RECOGNITION_MODEL,
    DEFAULT_DETECTOR_BACKEND,
)

# ─────────────────────────────────────────────
# MediaPipe Tasks — FaceLandmarker (new API)
# mp.solutions.* is no longer supported; use mp.tasks.* instead.
# Docs: https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker/python
# ─────────────────────────────────────────────

BaseOptions = mp_python.BaseOptions
FaceLandmarker = mp_vision.FaceLandmarker
FaceLandmarkerOptions = mp_vision.FaceLandmarkerOptions
VisionRunningMode = mp_vision.RunningMode


def _build_face_landmarker() -> FaceLandmarker:
    """
    Constructs a FaceLandmarker configured for VIDEO mode.
    VIDEO mode lets us pass a monotonically-increasing timestamp per frame
    without needing a live callback, which mirrors the old FaceMesh context-manager.
    """
    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=FACE_LANDMARKER_MODEL_PATH),
        running_mode=VisionRunningMode.VIDEO,
        num_faces=1,
        min_face_detection_confidence=MEDIAPIPE_MIN_DETECTION_CONFIDENCE,
        min_face_presence_confidence=MEDIAPIPE_MIN_DETECTION_CONFIDENCE,
        min_tracking_confidence=MEDIAPIPE_MIN_DETECTION_CONFIDENCE,
    )
    return FaceLandmarker.create_from_options(options)


# ─────────────────────────────────────────────
# DBOS Steps — External AI Service Calls
# ─────────────────────────────────────────────

@DBOS.step()
def step_check_liveness(file_path: str) -> str:
    """
    Uses MediaPipe FaceLandmarker (Tasks API) to perform liveness detection
    on a video or image. Scans up to MAX_LIVENESS_FRAMES, selects the
    clearest frontal face frame, saves it as a temp JPEG, and returns its path.
    Raises ValueError if no consistent 3D face mesh is detected.
    """
    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        raise ValueError("Cannot open video/image file for liveness detection.")

    # Retrieve the video FPS once; used to compute per-frame timestamps (ms).
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    best_frame = None
    max_face_area = 0
    frames_processed = 0
    face_detected_count = 0

    with _build_face_landmarker() as landmarker:
        while True:
            ret, frame = cap.read()
            if not ret or frames_processed > MAX_LIVENESS_FRAMES:
                break

            frames_processed += 1

            # Build a MediaPipe Image from the BGR OpenCV frame (converted to RGB).
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb_frame,
            )

            # detect_for_video requires a monotonically-increasing timestamp in ms.
            frame_timestamp_ms = int((frames_processed / fps) * 1000)
            result = landmarker.detect_for_video(mp_image, frame_timestamp_ms)

            if result.face_landmarks:
                face_detected_count += 1

                # Basic liveness heuristic: consistent 3D face mesh across frames.
                # We select the frame where the bounding box of landmarks is largest.
                h, w, _ = frame.shape
                landmarks = result.face_landmarks[0]  # NormalizedLandmark list
                x_coords = [lm.x * w for lm in landmarks]
                y_coords = [lm.y * h for lm in landmarks]

                area = (max(x_coords) - min(x_coords)) * (max(y_coords) - min(y_coords))
                if area > max_face_area:
                    max_face_area = area
                    best_frame = frame.copy()

    cap.release()

    # If no face found in enough frames, fail liveness
    if face_detected_count == 0 or best_frame is None:
        raise ValueError("Liveness Check Failed: No consistent 3D face mesh detected.")

    # Save the best frame to a temp file
    frame_path = f"{file_path}_best_frame.jpg"
    cv2.imwrite(frame_path, best_frame)
    return frame_path


@DBOS.step()
def step_extract_embedding(image_path: str, detector_backend: str = DEFAULT_DETECTOR_BACKEND) -> list:
    """
    Extracts the 512-dim ArcFace embedding from the given image.
    detector_backend defaults to 'retinaface' for high accuracy,
    but can be switched to 'opencv' for faster/simpler tests.
    """
    try:
        embeddings = DeepFace.represent(
            img_path=image_path,
            model_name=RECOGNITION_MODEL,
            detector_backend=detector_backend,
            enforce_detection=True,
        )

        if len(embeddings) == 0:
            raise ValueError("No face detected by DeepFace.")

        # Return the embedding vector of the first (best) face found
        return embeddings[0]["embedding"]
    except Exception as e:
        raise ValueError(f"Face extraction failed: {str(e)}")
