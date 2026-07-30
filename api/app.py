"""FastAPI application exposing analysis endpoints."""

import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from analysis.clients.base import ProviderRequestError
from api.models import (
    AnalysisRunRequest,
    AnalysisRunResponse,
    HealthResponse,
)
from api.service import (
    REPO_ROOT,
    UseCaseConfigurationError,
    build_excel_export_workbook,
    build_run_download_archive,
    get_default_output_dir,
    get_use_case_names,
    start_run,
)

app = FastAPI(
    title="Mission AIpossible Analysis API",
    version="0.2.0",
    description=(
        "API for running climate-analysis jobs from preset use cases, "
        "downloading run archives, and exporting run results to Excel."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PROMPT_FILE_PARAM = File(...)
USE_CASE_FORM = Form(
    ...,
    description="The use-case name (must match a key in config/analysis_use_cases.json).",
)
MAX_ITEMS_FORM = Form(
    default=None,
    ge=1,
    description="Optional limit on how many items (rows/pages) to process.",
)


@app.get(
    "/v1/analysis/use-cases",
    response_model=list[str],
    tags=["Analysis Runs"],
    summary="List Use Cases",
    description="Returns the names of all configured use-case presets.",
)
def list_use_cases() -> list[str]:
    """Return available use-case preset names from config."""
    return get_use_case_names()


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health Check",
    description="Returns service health status and the resolved analysis output directory.",
)
def health() -> HealthResponse:
    """Health endpoint."""
    output_dir = (REPO_ROOT / get_default_output_dir()).resolve()
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc),
        analysis_output_dir=str(output_dir),
    )


@app.post(
    "/v1/analysis/runs",
    response_model=AnalysisRunResponse,
    tags=["Analysis Runs"],
    summary="Run Analysis (JSON Request)",
    description=(
        "Starts a synchronous analysis run for the selected use case. "
        "Use this endpoint when sending request data as JSON."
    ),
    responses={
        400: {"description": "Bad request (for example unknown use_case)."},
        404: {"description": "Configured input/output path not found."},
        500: {"description": "Server-side use-case configuration error."},
    },
)
def run_analysis(request: AnalysisRunRequest) -> AnalysisRunResponse:
    """Start a synchronous analysis run."""
    try:
        return start_run(request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderRequestError as exc:
        raise HTTPException(status_code=502, detail=exc.detail) from exc
    except UseCaseConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/v1/analysis/runs/upload-prompt",
    response_model=AnalysisRunResponse,
    tags=["Analysis Runs"],
    summary="Run Analysis (Prompt File Upload)",
    description=(
        "Starts a synchronous analysis run by uploading a UTF-8 .txt user prompt. "
        "Use this endpoint for non-technical users who prefer file upload."
    ),
    responses={
        400: {"description": "Invalid prompt file or invalid request values."},
        404: {"description": "Configured input/output path not found."},
        500: {"description": "Server-side use-case configuration error."},
    },
)
async def run_analysis_with_prompt_file(
    prompt_file: UploadFile = PROMPT_FILE_PARAM,
    use_case: str = USE_CASE_FORM,
    max_items: int | None = MAX_ITEMS_FORM,
) -> AnalysisRunResponse:
    """Start a synchronous analysis run using a user prompt uploaded as a .txt file."""
    filename = (prompt_file.filename or "").strip()
    if not filename.lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt prompt files are supported")

    payload = await prompt_file.read()
    try:
        user_prompt = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Prompt file must be UTF-8 text") from exc

    normalized_prompt = user_prompt.strip()
    if not normalized_prompt:
        raise HTTPException(status_code=400, detail="Prompt file is empty")

    request = AnalysisRunRequest(
        use_case=use_case,
        max_items=max_items,
        user_prompt=normalized_prompt,
    )
    try:
        return start_run(request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderRequestError as exc:
        raise HTTPException(status_code=502, detail=exc.detail) from exc
    except UseCaseConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get(
    "/v1/analysis/runs/{run_id}/download",
    tags=["Analysis Runs"],
    summary="Download Run Archive",
    description="Downloads all JSON outputs of a run as a ZIP file.",
)
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


@app.get(
    "/v1/analysis/export/excel",
    tags=["Exports"],
    summary="Download Excel Export",
    description="Builds and downloads an Excel workbook for a given run_id.",
)
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
