"""Data schema definitions for mission scraper analysis module."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PageInput:
    """Normalized input fields used for AI analysis."""

    url: str
    title: Optional[str]
    subtitle: Optional[str]
    document_description: Optional[str]
    sections: list


@dataclass
class AnalysisOutput:
    """Structured AI output stored per page."""

    url: str
    summary: str
    model: str
    analyzed_at: str
    analysis_started_at: Optional[str] = None
    analysis_completed_at: Optional[str] = None
    analysis_elapsed_seconds: Optional[float] = None
    answers: Optional[dict[str, str]] = None
