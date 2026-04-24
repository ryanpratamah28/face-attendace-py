# Face Attendance API

A fault-tolerant, asynchronous Face Recognition and Liveness Detection backend built with Python, FastAPI, and DBOS. This application securely processes video and image uploads to verify user identities and prevent spoofing during attendance check-ins.

## Key Features

- **Asynchronous AI Processing**: Heavy AI tasks (video processing, face extraction) run safely in the background using DBOS durable workflows, preventing HTTP timeouts.
- **Liveness Detection**: Utilizes MediaPipe Face Mesh to scan video frames for consistent 3D facial structures, preventing spoofing (e.g., holding up a photo).
- **High-Accuracy Recognition**: Leverages DeepFace with RetinaFace (detection) and ArcFace (recognition) for state-of-the-art biometric accuracy.
- **Lightning-Fast Vector Search**: Stores 512-dimensional facial embeddings in PostgreSQL and performs ultra-fast 1:N similarity searches using the `pgvector` extension.

---

## Tech Stack

- **Language**: Python 3.10+
- **Framework**: FastAPI
- **Workflow Orchestration**: [DBOS](https://docs.dbos.dev/)
- **Database**: PostgreSQL with `pgvector`
- **AI/ML Core**: DeepFace, MediaPipe, OpenCV
- **Models**: ArcFace (Recognition), RetinaFace (Detection)

---

## Prerequisites

- Python 3.10 or higher
- PostgreSQL with the `pgvector` extension installed (or use Docker)
- A webcam or video source for testing

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/face-attendance-app.git
cd face-attendance-app
```

### 2. Install Dependencies

Create a virtual environment (recommended) and install the requirements:

```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Environment Setup

Copy the example environment file:

```bash
cp .env.example .env
```

Configure the following variables in your `.env` file:

| Variable                    | Description                      | Example                                    |
| --------------------------- | -------------------------------- | ------------------------------------------ |
| `DBOS_SYSTEM_DATABASE_URL`  | PostgreSQL connection string     | `postgres://user:pass@localhost:5432/face` |
| `DEFAULT_DETECTOR_BACKEND`  | The primary face detection model | `retinaface`                               |
| `COSINE_DISTANCE_THRESHOLD` | Distance threshold for matching  | `0.68`                                     |

### 4. Database Setup

Ensure PostgreSQL is running and the `pgvector` extension is available. You can start a local PostgreSQL container with pgvector using Docker:

```bash
docker run --name pgvector -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d ankane/pgvector:latest
```

Create the `face` database inside PostgreSQL. The application will automatically execute `schema.sql` to create the required tables and enable the `vector` extension on startup.

### 5. Start the Server

Run the application:

```bash
python -m app.main
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser to view the interactive API documentation (Swagger UI).

---

## Architecture

This project strictly adheres to a layered architecture using DBOS workflows and steps to separate concerns and guarantee determinism.

### Directory Structure

```text
├── app/
│   ├── api/                 # Presentation Layer
│   │   └── endpoints.py     # FastAPI Routers (HTTP request/response)
│   ├── workflows/           # Orchestration Layer
│   │   └── attendance.py    # DBOS @workflow (Macro business logic)
│   ├── operations/          # Execution Layer
│   │   ├── database.py      # DBOS @step (Direct DB interaction/pgvector)
│   │   └── external.py      # DBOS @step (External AI service calls)
│   ├── domain/              # Core Domain Layer
│   │   └── models.py        # Entity, Pydantic Models, Enums
│   ├── core/                # Configuration Layer
│   │   └── config.py        # Environment variables, constants
│   ├── testing/             # Test Suite
│   │   └── test_webcam.py   # Interactive webcam test script
│   └── main.py              # Application Entrypoint
├── .env.example             # Environment variables template
├── requirements.txt         # Python dependencies
└── schema.sql               # Database schema definition
```

### Request Lifecycle (Attendance Check-in)

1. Client `POST`s a video file to `/check-in` (`app/api/endpoints.py`).
2. FastAPI temporarily saves the video to disk and dispatches a background DBOS workflow, immediately returning a `job_id` to the client.
3. DBOS executes `process_attendance_workflow` (`app/workflows/attendance.py`).
4. **Step 1:** `step_check_liveness` runs MediaPipe against the video frames. If a consistent 3D face mesh is detected, it saves the best frame (`app/operations/external.py`).
5. **Step 2:** `step_extract_embedding` runs DeepFace to extract the 512-dim ArcFace vector from the frame.
6. **Step 3:** `step_find_user` queries PostgreSQL via `pgvector` (`<=>` cosine distance) to find the matching user (`app/operations/database.py`).
7. **Step 4:** `step_log_attendance` records the result in the `attendance_logs` table.
8. The client polls `GET /status/{job_id}` to retrieve the final biometric verification result.

### Database Schema

```text
users
├── id (serial, PK)
├── name (varchar, not null)
├── embedding (vector(512))
└── created_at (timestamp)

attendance_logs
├── id (serial, PK)
├── user_id (integer, FK -> users)
├── status (varchar, not null)
├── message (text)
└── created_at (timestamp)
```

---

## API Usage Example

### 1. Register a User

```bash
curl -X 'POST' \
  'http://localhost:8000/register' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'name=John Doe' \
  -F 'file=@photo.jpg' \
  -F 'detector_backend=retinaface'
```

### 2. Check-in (Submit Video)

```bash
curl -X 'POST' \
  'http://localhost:8000/check-in' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@selfie_video.mp4' \
  -F 'detector_backend=retinaface'
```

### 3. Check Job Status

```bash
curl -X 'GET' 'http://localhost:8000/status/YOUR_JOB_ID_HERE' -H 'accept: application/json'
```

---

## Testing

There are two ways to test the API if you don't have a frontend ready:

### 1. Interactive API Docs (Swagger UI)
FastAPI automatically generates an interactive dashboard where you can test every endpoint directly from your browser.
- **URL**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **How to use**: Click on an endpoint (e.g., `/register`), click **"Try it out"**, upload your file, and click **Execute**.

### 2. Live Webcam Test Script
An interactive Python script is provided to capture photos directly from your laptop camera and send them to the API.
- **Location**: `app/testing/test_webcam.py`
- **How to run**:
  ```bash
  python app/testing/test_webcam.py
  ```
- **Controls**:
  - `[1]` to Register (Capture face + enter name)
  - `[2]` to Check-in (Capture face to verify)
  - **SPACE** to capture photo in the camera window.
  - **ESC** to cancel capture.

---

## Troubleshooting

### DeepFace Model Downloads

On the first run, DeepFace will automatically download the pre-trained weights for ArcFace and RetinaFace (several hundred megabytes). This may cause the first workflow execution to take significantly longer. Subsequent runs will use the cached models.

### Database Connection Refused

**Error:** `could not connect to server: Connection refused`

**Solution:**
Ensure PostgreSQL is running and your `.env` file contains the correct `DBOS_SYSTEM_DATABASE_URL` format.

### Pgvector Extension Missing

**Error:** `type "vector" does not exist`

**Solution:**
Ensure your PostgreSQL instance has the `pgvector` extension installed. If using Docker, ensure you are using the `ankane/pgvector` image, not the standard `postgres` image.

### MediaPipe Liveness Failures

**Error:** `Liveness Check Failed: No consistent 3D face mesh detected.`

**Solution:**
Ensure the uploaded video is well-lit, the face is fully visible, and the user makes slight movements (to prove 3D depth). Adjust `MAX_LIVENESS_FRAMES` in `.env` if videos require more scanning time.
