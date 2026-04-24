import os
import psycopg2
from pgvector.psycopg2 import register_vector
import numpy as np
from dbos import DBOS

from app.core.config import DATABASE_URL, COSINE_DISTANCE_THRESHOLD


# ─────────────────────────────────────────────
# Connection Helper
# ─────────────────────────────────────────────

def get_connection():
    if not DATABASE_URL:
        raise Exception("DBOS_SYSTEM_DATABASE_URL is not set. Please set it to your postgres URL.")
    conn = psycopg2.connect(DATABASE_URL)
    register_vector(conn)
    return conn


def init_db():
    conn = get_connection()
    schema_path = os.path.join(os.path.dirname(__file__), "..", "..", "schema.sql")
    with conn.cursor() as cur:
        with open(schema_path, "r") as f:
            cur.execute(f.read())
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# DBOS Steps — Database Operations
# ─────────────────────────────────────────────

@DBOS.step()
def step_register_user(name: str, embedding: list) -> int:
    conn = get_connection()
    user_id = None
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (name, embedding) VALUES (%s, %s::vector) RETURNING id;",
            (name, np.array(embedding).tolist())
        )
        user_id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return user_id


@DBOS.step()
def step_find_user(embedding: list) -> dict:
    conn = get_connection()
    match = None
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, embedding <=> %s::vector AS distance 
            FROM users 
            ORDER BY distance ASC 
            LIMIT 1;
            """,
            (np.array(embedding).tolist(),)
        )
        row = cur.fetchone()
        if row and row[2] <= COSINE_DISTANCE_THRESHOLD:
            match = {"found": True, "user_id": row[0], "name": row[1], "distance": row[2]}
    conn.close()
    return match if match else {"found": False}


@DBOS.step()
def step_log_attendance(user_id: int, status: str, message: str) -> None:
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO attendance_logs (user_id, status, message) VALUES (%s, %s, %s);",
            (user_id, status, message)
        )
    conn.commit()
    conn.close()
