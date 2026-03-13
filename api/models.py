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

    use_case: str = Field(
        min_length=1,
        description="Use-case preset key defined in config/analysis_use_cases.json.",
        examples=["adaptation_stories", "question_2_1_1_column_7", "question_4_8_column_7"],
    )
    max_items: int | None = Field(
        default=None,
        ge=1,
        description="Optional maximum number of source items to analyze.",
    )
    user_prompt: str | None = Field(
        default=None,
        max_length=50000,
        description="Optional user prompt override for this run.",
    )


class AnalysisRunItem(BaseModel):
    """Per-item run details."""

    page_file: str = Field(description="Input item identifier/path processed for this row.")
    output_file: str = Field(description="Output JSON file path written for this item.")
    url: str = Field(description="Source URL or synthetic excel:// identifier.")
    saved: bool = Field(description="True when output was written, false when skipped.")
    elapsed_seconds: float | None = Field(default=None, description="Item processing duration in seconds.")


class AnalysisRunResponse(BaseModel):
    """Summary response for run endpoint."""

    processed: int = Field(description="Total items visited by the run.")
    skipped: int = Field(description="Total items skipped.")
    total_elapsed_seconds: float = Field(description="Total execution time in seconds.")
    total_elapsed_minutes: float = Field(description="Total execution time in minutes.")
    provider: str = Field(description="AI provider used for this run.")
    model: str = Field(description="Model name used for this run.")
    run_id: str = Field(description="Run identifier (timestamp-based folder name).")
    output_dir: str = Field(description="Absolute output folder path for this run.")
    items: list[AnalysisRunItem] = Field(description="Per-item processing details.")
    warnings: list[str] = Field(default_factory=list, description="Non-fatal warnings emitted during execution.")


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
