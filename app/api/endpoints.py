import os
import shutil
from fastapi import FastAPI, File, UploadFile, Form
from dbos import DBOS

from app.core.config import UPLOAD_DIR, DEFAULT_DETECTOR_BACKEND
from app.domain.models import JobStartedResponse, JobStatusResponse
from app.workflows import attendance

app = FastAPI(title="Face Attendance API with DBOS")

os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─────────────────────────────────────────────
# Registration
# ─────────────────────────────────────────────

@app.post("/register", response_model=JobStartedResponse)
async def register_user(
    name: str = Form(...),
    file: UploadFile = File(...),
    detector_backend: str = Form(DEFAULT_DETECTOR_BACKEND),
):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Start the DBOS workflow asynchronously — client receives job_id immediately
    handle = DBOS.start_workflow(attendance.register_user_workflow, name, file_path, detector_backend)
    return JobStartedResponse(message="Registration job started", job_id=handle.workflow_id)


# ─────────────────────────────────────────────
# Check-in
# ─────────────────────────────────────────────

@app.post("/check-in", response_model=JobStartedResponse)
async def check_in(
    file: UploadFile = File(...),
    detector_backend: str = Form(DEFAULT_DETECTOR_BACKEND),
):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Start the DBOS workflow asynchronously — client receives job_id immediately
    handle = DBOS.start_workflow(attendance.process_attendance_workflow, file_path, detector_backend)
    return JobStartedResponse(message="Attendance check-in job started", job_id=handle.workflow_id)

# ─────────────────────────────────────────────
# Job Status Polling
# ─────────────────────────────────────────────

@app.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    # Use async variants — this endpoint runs inside an async event loop
    status = await DBOS.get_workflow_status_async(job_id)
    if not status:
        return JobStatusResponse(status="NOT_FOUND", error="Job not found")

    print("status is: ", status.status)

    response = JobStatusResponse(status=status.status)

    if status.status == "SUCCESS":
        handle = await DBOS.retrieve_workflow_async(job_id)
        response.result = await handle.get_result()

    return response
    