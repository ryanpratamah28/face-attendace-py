"""
test_webcam.py — Manual test script for the Face Attendance API.

How to use:
  1. Make sure the API server is running: `dbos start` or `uvicorn app.main:app`
  2. Run this script:    python test_webcam.py

It will open your webcam, let you capture a photo, then hit the API for you.
Press SPACE to capture, ESC to cancel.
"""

import cv2
import requests
import time
import sys
import os

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000"

# Set path relative to this script: ../../uploads
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
UPLOAD_DIR = os.path.join(ROOT_DIR, "uploads")
CAPTURE_PATH = os.path.join(UPLOAD_DIR, "_test_capture.jpg")

os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def capture_from_webcam(window_title: str = "Press SPACE to capture | ESC to cancel") -> str | None:
    """Opens webcam, shows live feed, captures on SPACE key. Returns saved image path or None."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌  Could not open webcam. Make sure it's connected and not in use.")
        return None

    print(f"\n📷  Webcam opened. [{window_title}]")
    captured_path = None

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌  Failed to read frame from webcam.")
            break

        # Mirror the frame so it feels like a selfie
        frame = cv2.flip(frame, 1)

        # Draw instruction overlay
        cv2.putText(frame, "SPACE = capture  |  ESC = cancel",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow(window_title, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 32:  # SPACE
            cv2.imwrite(CAPTURE_PATH, frame)
            print(f"✅  Photo saved to: {CAPTURE_PATH}")
            captured_path = CAPTURE_PATH
            break
        elif key == 27:  # ESC
            print("⚠️   Capture cancelled.")
            break

    cap.release()
    cv2.destroyAllWindows()
    return captured_path


def poll_job(job_id: str, timeout: int = 30) -> dict:
    """Polls /status/{job_id} until SUCCESS/ERROR or timeout."""
    print(f"\n⏳  Polling job: {job_id}")
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(f"{API_BASE}/status/{job_id}")
        if not resp.ok:
            print(f"   ⚠️  API returned HTTP {resp.status_code}: {resp.text[:200]}")
            return {"status": "ERROR", "error": f"HTTP {resp.status_code}"}
        data = resp.json()
        status = data.get("status", "UNKNOWN")
        print(f"   → status: {status}")
        if status in ("SUCCESS", "ERROR"):
            return data
        time.sleep(1.5)
    return {"status": "TIMEOUT", "error": "Job did not complete in time."}


# ── Flows ─────────────────────────────────────────────────────────────────────

def flow_register():
    """Capture a photo and register a new user."""
    print("\n" + "="*50)
    print("  REGISTER A NEW USER")
    print("="*50)
    name = input("Enter your name: ").strip()
    if not name:
        print("❌  Name cannot be empty.")
        return

    image_path = capture_from_webcam("Registration — SPACE to capture | ESC to cancel")
    if not image_path:
        return

    print(f"\n🚀  Sending registration request for '{name}'...")
    with open(image_path, "rb") as f:
        resp = requests.post(
            f"{API_BASE}/register",
            data={"name": name, "detector_backend": "retinaface"},
            files={"file": ("capture.jpg", f, "image/jpeg")},
        )

    if resp.status_code != 200:
        print(f"❌  API error {resp.status_code}: {resp.text}")
        return

    job_id = resp.json().get("job_id")
    print(f"   Job ID: {job_id}")

    result = poll_job(job_id)
    print("\n📋  Result:")
    print(f"   Status  : {result.get('status')}")
    if result.get("result"):
        print(f"   Details : {result['result']}")
    if result.get("error"):
        print(f"   Error   : {result['error']}")


def flow_checkin():
    """Capture a photo and attempt to check in (recognize face)."""
    print("\n" + "="*50)
    print("  FACE CHECK-IN")
    print("="*50)

    image_path = capture_from_webcam("Check-in — SPACE to capture | ESC to cancel")
    if not image_path:
        return

    print("\n🚀  Sending check-in request...")
    with open(image_path, "rb") as f:
        resp = requests.post(
            f"{API_BASE}/check-in",
            data={"detector_backend": "retinaface"},
            files={"file": ("capture.jpg", f, "image/jpeg")},
        )

    if resp.status_code != 200:
        print(f"❌  API error {resp.status_code}: {resp.text}")
        return

    job_id = resp.json().get("job_id")
    print(f"   Job ID: {job_id}")

    result = poll_job(job_id)
    print("\n📋  Result:")
    print(f"   Status  : {result.get('status')}")
    if result.get("result"):
        print(f"   Details : {result['result']}")
    if result.get("error"):
        print(f"   Error   : {result['error']}")


# ── Main Menu ─────────────────────────────────────────────────────────────────

def main():
    print("\n🎭  Face Attendance — Webcam Test Script")
    print("   Make sure your API server is running at:", API_BASE)

    while True:
        print("\n  What do you want to do?")
        print("  [1] Register a new user (capture your face)")
        print("  [2] Check in (recognize your face)")
        print("  [q] Quit")
        choice = input("\n  Enter choice: ").strip().lower()

        if choice == "1":
            flow_register()
        elif choice == "2":
            flow_checkin()
        elif choice in ("q", "quit", "exit"):
            print("\n👋  Bye!\n")
            sys.exit(0)
        else:
            print("⚠️   Invalid choice, try again.")


if __name__ == "__main__":
    main()
