"""Pydantic schemas for the public and admin APIs."""
from __future__ import annotations

import uuid
from datetime import time

from pydantic import BaseModel, ConfigDict


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    day_of_week: int
    start_time: time
    end_time: time
    course_name_raw: str
    course_code_raw: str | None
    lecturer_raw: str | None
    venue_raw: str | None
    session_type: str | None
    confidence: str
    source_page: int
    is_shared: bool


class VersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    period_id: uuid.UUID
    label: str
    status: str
    is_active: bool


class ImportResult(BaseModel):
    version_id: str
    sessions: int
    with_code: int
    issues: int
    errors: int
    warnings: int
