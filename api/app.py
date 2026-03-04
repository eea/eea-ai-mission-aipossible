"""FastAPI application exposing analysis endpoints."""

from datetime import datetime, timezone
from pathlib import Path
import shutil

from fastapi import BackgroundTasks
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from api.models import (
    AnalysisRunRequest,
    AnalysisRunResponse,
    HealthResponse,
)
from api.service import REPO_ROOT, get_default_output_dir, start_run
from api.service import build_excel_export_workbook, build_run_download_archive


app = FastAPI(title="Mission AIpossible Analysis API", version="0.1.0")

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Health endpoint."""
    output_dir = (REPO_ROOT / get_default_output_dir()).resolve()
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc),
        analysis_output_dir=str(output_dir),
    )


@app.post("/v1/analysis/runs", response_model=AnalysisRunResponse)
def run_analysis(request: AnalysisRunRequest) -> AnalysisRunResponse:
    """Start a synchronous analysis run."""
    try:
        return start_run(request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/analysis/runs/{run_id}/download")
def download_run_archive(run_id: str, background_tasks: BackgroundTasks) -> FileResponse:
    """Download one run output folder as a zip archive."""
    try:
        archive_path, temp_dir = build_run_download_archive(run_id=run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    background_tasks.add_task(shutil.rmtree, str(temp_dir), True)
    return FileResponse(
        path=Path(archive_path),
        media_type="application/zip",
        filename=f"{run_id}.zip",
    )


@app.get("/v1/analysis/export/excel")
def download_excel_export(
    run_id: str = Query(...),
) -> FileResponse:
    """Export one run folder to Excel and download it."""
    try:
        workbook_path = build_excel_export_workbook(run_id=run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FileResponse(
        path=Path(workbook_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=Path(workbook_path).name,
    )
