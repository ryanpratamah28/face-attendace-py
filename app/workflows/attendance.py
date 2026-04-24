import os
from dbos import DBOS

from app.operations import external, database


# ─────────────────────────────────────────────
# Registration Workflow
# ─────────────────────────────────────────────

@DBOS.workflow()
def register_user_workflow(name: str, image_path: str, detector_backend: str = "retinaface") -> dict:
    best_frame_path = ""
    try:
        # Step 1: Liveness check — extract best frontal frame
        best_frame_path = external.step_check_liveness(image_path)

        # Step 2: Extract ArcFace embedding
        embedding = external.step_extract_embedding(best_frame_path, detector_backend)

        # Step 3: Persist user embedding in pgvector
        user_id = database.step_register_user(name, embedding)

        return {"status": "success", "user_id": user_id, "name": name}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if best_frame_path and os.path.exists(best_frame_path):
            os.remove(best_frame_path)
        if os.path.exists(image_path):
            os.remove(image_path)


# ─────────────────────────────────────────────
# Attendance Check-in Workflow
# ─────────────────────────────────────────────

@DBOS.workflow()
def process_attendance_workflow(file_path: str, detector_backend: str = "retinaface") -> dict:
    best_frame_path = ""
    try:
        # Step 1: Liveness check — extract best frontal frame
        best_frame_path = external.step_check_liveness(file_path)

        # Step 2: Extract ArcFace embedding
        embedding = external.step_extract_embedding(best_frame_path, detector_backend)

        # Step 3: Query pgvector for the closest matching user
        match_result = database.step_find_user(embedding)

        if match_result.get("found"):
            user_id = match_result["user_id"]
            name = match_result["name"]

            # Step 4: Log successful attendance
            database.step_log_attendance(user_id, "PRESENT", "Verified via Face Recognition")
            return {"status": "success", "message": f"Welcome {name}", "user": name}
        else:
            return {"status": "error", "message": "Face not recognized in database"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        # Cleanup temp files
        if best_frame_path and os.path.exists(best_frame_path):
            os.remove(best_frame_path)
        if os.path.exists(file_path):
            os.remove(file_path)
