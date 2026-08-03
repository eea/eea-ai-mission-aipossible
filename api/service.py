"""Application services for analysis API endpoints."""

import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from analysis.analyzer import BatchRunStats
from analysis.analyzer import run_batch as run_pages_batch
from analysis.clients.env_loader import load_env_file
from analysis.clients.factory import get_client
from analysis.excel_analyzer import run_batch as run_excel_batch
from api.models import (
    AnalysisResultDocument,
    AnalysisResultListResponse,
    AnalysisResultSummary,
    AnalysisRunItem,
    AnalysisRunRequest,
    AnalysisRunResponse,
)
from env_settings import get_str_setting
from exporters.analysis_excel_exporter import export_analysis_to_excel

RESULT_ID_PATTERN = re.compile(r"^[0-9a-f]{64}$")
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
REPO_ROOT = Path(__file__).resolve().parents[1]
SWAGGER_PLACEHOLDER_VALUES = {"string"}
DEFAULT_API_OUTPUT_DIR = "data/analysis"
DEFAULT_API_EXPORT_DIR = "data/exports"
DEFAULT_API_PROVIDER = "mock"
DEFAULT_USE_CASES_CONFIG = "config/analysis_use_cases.json"


class UseCaseConfigurationError(RuntimeError):
    """Raised when use-case preset configuration is invalid."""


@dataclass
class UseCaseConfig:
    name: str
    source_type: str
    source_path: Path
    system_prompt_path: Path
    user_prompt_path: Path
    sheet_name: str | None = None
    column_name: str | None = None
    header_row: int = 1
    row_identifier_column: str | None = None


def _resolve_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _normalize_optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.lower() in SWAGGER_PLACEHOLDER_VALUES:
        return None
    return normalized


def _require_existing_dir(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")
    if not path.is_dir():
        raise FileNotFoundError(f"{label} is not a directory: {path}")


def _require_existing_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"{label} is not a file: {path}")


def get_default_output_dir() -> str:
    return get_str_setting("OUTPUT_DIR", DEFAULT_API_OUTPUT_DIR, aliases=("API_OUTPUT_DIR",))


def get_default_export_dir() -> str:
    return get_str_setting("EXPORT_DIR", DEFAULT_API_EXPORT_DIR, aliases=("API_EXPORT_DIR",))


def get_default_provider() -> str:
    provider = get_str_setting("PROVIDER", DEFAULT_API_PROVIDER, aliases=("API_PROVIDER",)).strip().lower()
    if provider not in {"openai", "eea", "mock"}:
        raise ValueError(f"Unsupported PROVIDER: {provider}")
    return provider


def get_default_model_override() -> str:
    return get_str_setting("API_MODEL", "")


def get_default_api_key_override() -> str:
    return get_str_setting("API_API_KEY", "")


def get_default_use_cases_config() -> str:
    return get_str_setting("API_USE_CASES_CONFIG", DEFAULT_USE_CASES_CONFIG)


def _load_use_case_presets() -> dict[str, Any]:
    config_path = _resolve_path(get_default_use_cases_config())
    if not config_path.exists() or not config_path.is_file():
        raise UseCaseConfigurationError(f"Use-case config file not found: {config_path}")
    loaded = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise UseCaseConfigurationError("Use-case config must be a JSON object.")
    return loaded


def get_use_case_names() -> list[str]:
    """Return the list of configured use-case preset names."""
    try:
        return list(_load_use_case_presets().keys())
    except UseCaseConfigurationError:
        return []


def _resolve_use_case(use_case: str) -> UseCaseConfig:
    use_case_name = _normalize_optional_str(use_case)
    if not use_case_name:
        raise ValueError("Missing required field: use_case")

    presets = _load_use_case_presets()
    selected = presets.get(use_case_name)
    if not isinstance(selected, dict):
        raise ValueError(f"Unknown use_case: {use_case_name}")

    source_type = str(selected.get("source_type") or "").strip().lower()
    source_path_value = str(selected.get("source_path") or "").strip()
    system_prompt_path_value = str(selected.get("system_prompt_path") or "").strip()
    user_prompt_path_value = str(selected.get("user_prompt_path") or "").strip()
    if not source_type or not source_path_value or not system_prompt_path_value or not user_prompt_path_value:
        raise UseCaseConfigurationError(
            f"Use case '{use_case_name}' must define source_type, source_path, "
            "system_prompt_path, and user_prompt_path."
        )

    source_path = _resolve_path(source_path_value)
    system_prompt_path = _resolve_path(system_prompt_path_value)
    user_prompt_path = _resolve_path(user_prompt_path_value)
    if source_type == "pages":
        return UseCaseConfig(
            name=use_case_name,
            source_type=source_type,
            source_path=source_path,
            system_prompt_path=system_prompt_path,
            user_prompt_path=user_prompt_path,
        )
    if source_type == "excel":
        sheet_name = str(selected.get("sheet_name") or "").strip()
        column_name = str(selected.get("column_name") or "").strip()
        row_identifier_column = str(selected.get("row_identifier_column") or "").strip() or None
        header_row_raw = selected.get("header_row", 1)
        try:
            header_row = int(header_row_raw)
        except (TypeError, ValueError) as exc:
            raise UseCaseConfigurationError(
                f"Use case '{use_case_name}' has invalid header_row: {header_row_raw}"
            ) from exc
        if not sheet_name or not column_name:
            raise UseCaseConfigurationError(
                f"Use case '{use_case_name}' must define sheet_name and column_name for excel."
            )
        if header_row < 1:
            raise UseCaseConfigurationError(f"Use case '{use_case_name}' must define header_row >= 1.")
        return UseCaseConfig(
            name=use_case_name,
            source_type=source_type,
            source_path=source_path,
            system_prompt_path=system_prompt_path,
            user_prompt_path=user_prompt_path,
            sheet_name=sheet_name,
            column_name=column_name,
            header_row=header_row,
            row_identifier_column=row_identifier_column,
        )

    raise UseCaseConfigurationError(f"Use case '{use_case_name}' has unsupported source_type: {source_type}")


def _build_client(
    user_prompt_override: str | None = None,
    system_prompt_override: str | None = None,
):
    provider = get_default_provider()
    env_values = load_env_file(REPO_ROOT / f".env.{provider}")
    key_path = REPO_ROOT / f".env.{provider}.keys"
    key_values = load_env_file(key_path)

    model_override = _normalize_optional_str(get_default_model_override())
    api_key_override = _normalize_optional_str(get_default_api_key_override())
    model = model_override or env_values.get("MODEL") or env_values.get("AI_MODEL") or "stub"
    api_url = env_values.get("API_URL") or ""
    api_key = api_key_override or key_values.get("API_KEY") or key_values.get("AI_API_KEY") or ""
    if provider != "mock" and not api_key:
        raise ValueError(
            "Missing API key for provider "
            f"'{provider}'. Set API_API_KEY in .env.api or add API_KEY to {key_path.name}."
        )

    prompts_dir = _resolve_path("analysis/prompts")

    client = get_client(
        provider=provider,
        api_key=api_key,
        model=model,
        api_url=api_url,
        prompts_dir=prompts_dir,
        user_prompt_template=_normalize_optional_str(user_prompt_override),
        system_prompt_template=_normalize_optional_str(system_prompt_override),
    )
    return client, provider


def _load_system_prompt_override(use_case: UseCaseConfig) -> str:
    path = use_case.system_prompt_path
    if not path.exists() or not path.is_file():
        raise UseCaseConfigurationError(f"System prompt file not found for use case '{use_case.name}': {path}")
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise UseCaseConfigurationError(f"System prompt file is empty for use case '{use_case.name}': {path}")
    return content


def _load_user_prompt_override(use_case: UseCaseConfig) -> str:
    path = use_case.user_prompt_path
    if not path.exists() or not path.is_file():
        raise UseCaseConfigurationError(f"User prompt file not found for use case '{use_case.name}': {path}")
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise UseCaseConfigurationError(f"User prompt file is empty for use case '{use_case.name}': {path}")
    return content


def _resolve_run_output_dir(output_dir: Path, timestamped_output_dir: bool) -> Path:
    if not timestamped_output_dir:
        return output_dir
    folder_name = datetime.now().strftime("%Y%m%d_%H%M%S")
    return output_dir / folder_name


def _map_run_response(
    stats: BatchRunStats,
    provider: str,
    model: str,
    output_dir: Path,
    warnings: list[str] | None = None,
) -> AnalysisRunResponse:
    items = [
        AnalysisRunItem(
            page_file=item.page_path,
            output_file=item.output_path,
            url=item.url,
            saved=item.saved,
            elapsed_seconds=item.elapsed_seconds,
        )
        for item in stats.items
    ]

    return AnalysisRunResponse(
        processed=stats.processed,
        skipped=stats.skipped,
        total_elapsed_seconds=stats.total_elapsed_seconds,
        total_elapsed_minutes=stats.total_elapsed_seconds / 60.0,
        provider=provider,
        model=model,
        run_id=output_dir.name,
        output_dir=str(output_dir),
        items=items,
        warnings=warnings or [],
    )


def start_run(request: AnalysisRunRequest) -> AnalysisRunResponse:
    """Run analysis for a batch and return execution details."""
    output_dir_value = get_default_output_dir()
    timestamped_output_dir = True
    overwrite = False
    dry_run = False
    quiet = True

    use_case = _resolve_use_case(request.use_case)
    base_output_dir = _resolve_path(output_dir_value)
    _require_existing_dir(base_output_dir, "Output directory")

    output_dir = _resolve_run_output_dir(base_output_dir, timestamped_output_dir)
    warnings: list[str] = []
    system_prompt_override = _load_system_prompt_override(use_case)
    user_prompt_override = _normalize_optional_str(request.user_prompt) or _load_user_prompt_override(use_case)
    client, provider = _build_client(
        user_prompt_override=user_prompt_override,
        system_prompt_override=system_prompt_override,
    )

    if use_case.source_type == "pages":
        _require_existing_dir(use_case.source_path, "Input directory")
        stats = run_pages_batch(
            input_dir=use_case.source_path,
            output_dir=output_dir,
            client=client,
            max_items=request.max_items,
            verbose=not quiet,
            overwrite=overwrite,
            dry_run=dry_run,
            use_case=use_case.name,
            source_type=use_case.source_type,
            source_path=str(use_case.source_path),
        )
    elif use_case.source_type == "excel":
        _require_existing_file(use_case.source_path, "Input file")
        try:
            stats = run_excel_batch(
                input_file=use_case.source_path,
                sheet_name=use_case.sheet_name or "",
                column_name=use_case.column_name or "",
                header_row=use_case.header_row,
                output_dir=output_dir,
                client=client,
                max_items=request.max_items,
                verbose=not quiet,
                overwrite=overwrite,
                dry_run=dry_run,
                use_case=use_case.name,
                source_type=use_case.source_type,
                source_path=str(use_case.source_path),
                row_identifier_column=use_case.row_identifier_column,
            )
        except ValueError as exc:
            raise UseCaseConfigurationError(str(exc)) from exc
    else:
        raise UseCaseConfigurationError(
            f"Unsupported source_type for use case '{use_case.name}': {use_case.source_type}"
        )
    return _map_run_response(
        stats=stats,
        provider=provider,
        model=getattr(client, "model", "stub"),
        output_dir=output_dir,
        warnings=warnings,
    )


def build_run_download_archive(run_id: str, output_root: str | None = None) -> tuple[Path, Path]:
    """Create a temporary zip archive for a run folder and return (archive_path, temp_dir)."""
    if not RUN_ID_PATTERN.match(run_id):
        raise ValueError("Invalid run id")

    effective_output_root = output_root or get_default_output_dir()
    base_dir = _resolve_path(effective_output_root)
    run_dir = (base_dir / run_id).resolve()
    if not run_dir.exists() or not run_dir.is_dir():
        raise FileNotFoundError(f"Run folder not found: {run_id}")

    temp_dir = Path(tempfile.mkdtemp(prefix="analysis_run_"))
    archive_base = temp_dir / run_id
    archive_path = Path(shutil.make_archive(str(archive_base), "zip", root_dir=str(run_dir)))
    return archive_path, temp_dir


def build_excel_export_workbook(run_id: str) -> Path:
    """Create an Excel export under API_EXPORT_DIR/<run_id>/ and return workbook path."""
    if not RUN_ID_PATTERN.match(run_id):
        raise ValueError("Invalid run id")

    output_root = _resolve_path(get_default_output_dir())
    input_dir = (output_root / run_id).resolve()
    if not input_dir.exists() or not input_dir.is_dir():
        raise FileNotFoundError(f"Run folder not found: {run_id}")

    export_root = _resolve_path(get_default_export_dir())
    export_dir = (export_root / run_id).resolve()
    export_dir.mkdir(parents=True, exist_ok=True)
    output_path = export_dir / f"analysis_{run_id}.xlsx"
    export_analysis_to_excel(
        input_dir=input_dir,
        output_path=output_path,
        overwrite=True,
        verbose=False,
        dry_run=False,
    )
    return output_path


def _parse_result_file(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return {str(key): value for key, value in loaded.items()}


def list_results(output_dir: str | None, limit: int, offset: int) -> AnalysisResultListResponse:
    """List stored analysis results from the output directory."""
    output_dir_value = output_dir or get_default_output_dir()
    result_dir = _resolve_path(output_dir_value)
    if not result_dir.exists():
        return AnalysisResultListResponse(total=0, limit=limit, offset=offset, items=[])

    files = sorted(
        result_dir.glob("*.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    total = len(files)
    selected = files[offset : offset + limit]

    items: list[AnalysisResultSummary] = []
    for file_path in selected:
        payload = _parse_result_file(file_path)
        items.append(
            AnalysisResultSummary(
                id=file_path.stem,
                file_name=file_path.name,
                url=payload.get("url"),
                title=payload.get("title"),
                provider=payload.get("provider"),
                model=payload.get("model"),
                analyzed_at=payload.get("analyzed_at"),
                analysis_elapsed_seconds=payload.get("analysis_elapsed_seconds"),
            )
        )

    return AnalysisResultListResponse(total=total, limit=limit, offset=offset, items=items)


def get_result(output_dir: str | None, result_id: str) -> AnalysisResultDocument | None:
    """Fetch one stored result by id."""
    if not RESULT_ID_PATTERN.match(result_id):
        return None

    output_dir_value = output_dir or get_default_output_dir()
    result_dir = _resolve_path(output_dir_value)
    result_path = result_dir / f"{result_id}.json"
    if not result_path.exists() or not result_path.is_file():
        return None

    payload = _parse_result_file(result_path)
    return AnalysisResultDocument(id=result_id, file_name=result_path.name, data=payload)
