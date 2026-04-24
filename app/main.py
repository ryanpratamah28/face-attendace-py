import os

# Remove log message oneDNN
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

# Remove log message from TensorFlow (Optional)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from dbos import DBOS
from app.api.endpoints import app
from app.core.config import DATABASE_URL, DBOS_APP_NAME
from app.operations.database import init_db
import uvicorn

if __name__ == "__main__":
    # Ensure env variable is set for DBOS and psycopg2
    os.environ.setdefault("DBOS_SYSTEM_DATABASE_URL", DATABASE_URL)

    # Initialize DB schema (idempotent via CREATE IF NOT EXISTS)
    try:
        init_db()
        print("✅ Database initialized successfully.")
    except Exception as e:
        print(f"⚠️  Error initializing database: {e}")

    # Configure and launch DBOS — MUST happen before uvicorn.run
    config = {
        "name": DBOS_APP_NAME,
        "system_database_url": os.environ.get("DBOS_SYSTEM_DATABASE_URL"),
    }
    DBOS(config=config)
    DBOS.launch()

    # Start FastAPI
    uvicorn.run(app, host="0.0.0.0", port=8000)
