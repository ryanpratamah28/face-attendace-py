from pydantic import BaseModel
from typing import Any, Optional


# ─────────────────────────────────────────────
# API Response Models
# ─────────────────────────────────────────────

class JobStartedResponse(BaseModel):
    message: str
    job_id: str


class JobStatusResponse(BaseModel):
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None


# ─────────────────────────────────────────────
# Internal Domain Models
# ─────────────────────────────────────────────

class UserMatch(BaseModel):
    found: bool
    user_id: Optional[int] = None
    name: Optional[str] = None
    distance: Optional[float] = None


class WorkflowResult(BaseModel):
    status: str                      # "success" | "error"
    message: Optional[str] = None
    user: Optional[str] = None
    user_id: Optional[int] = None
    name: Optional[str] = None
