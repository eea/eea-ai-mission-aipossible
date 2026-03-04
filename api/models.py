"""Pydantic models for the analysis API."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Health probe response."""

    status: str = "ok"
    timestamp: datetime
    analysis_output_dir: str


class AnalysisRunRequest(BaseModel):
    """Request payload for starting a run."""

    model_config = ConfigDict(extra="forbid")

    max_items: int | None = Field(default=None, ge=1)


class AnalysisRunItem(BaseModel):
    """Per-item run details."""

    page_file: str
    output_file: str
    url: str
    saved: bool
    elapsed_seconds: float | None = None


class AnalysisRunResponse(BaseModel):
    """Summary response for run endpoint."""

    processed: int
    skipped: int
    total_elapsed_seconds: float
    total_elapsed_minutes: float
    provider: str
    model: str
    run_id: str
    output_dir: str
    items: list[AnalysisRunItem]
    warnings: list[str] = Field(default_factory=list)


class AnalysisResultSummary(BaseModel):
    """Summary list item for stored analysis result."""

    id: str
    file_name: str
    url: str | None = None
    title: str | None = None
    provider: str | None = None
    model: str | None = None
    analyzed_at: str | None = None
    analysis_elapsed_seconds: float | None = None


class AnalysisResultListResponse(BaseModel):
    """Paginated list response."""

    total: int
    limit: int
    offset: int
    items: list[AnalysisResultSummary]


class AnalysisResultDocument(BaseModel):
    """Full analysis document payload."""

    id: str
    file_name: str
    data: dict[str, Any]
