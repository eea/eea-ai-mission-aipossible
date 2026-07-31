"""Module for analyzing saved web pages using AI and outputting structured results."""

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from analysis.utils import (
    build_prompt,
    load_page_json,
    normalize_text,
    output_path_for_url,
    parse_answers,
)
from env_settings import get_bool_setting


def iter_pages(input_dir: Path) -> Iterator[Path]:
    """Yield page JSON files from the input directory."""
    yield from sorted(input_dir.glob("*.json"))


def should_skip(output_path: Path) -> bool:
    """Return True when analysis output already exists and is non-empty."""
    return output_path.exists() and output_path.stat().st_size > 0


def analyze_page(
    page_path: Path,
    output_dir: Path,
    client,
    overwrite: bool = False,
    use_case: str | None = None,
    source_type: str = "pages",
    source_path: str | None = None,
) -> tuple[Path, bool, float | None]:
    """Analyze a single page and write output JSON, returning (path, saved, elapsed)."""
    page = load_page_json(page_path)
    url = page.get("url")
    if not url:
        raise ValueError(f"Missing url in {page_path}")

    output_path = output_path_for_url(output_dir, url)
    if not overwrite and should_skip(output_path):
        return output_path, False, None

    title = normalize_text(page.get("title") or "")
    summary = normalize_text(page.get("document_description") or "")
    prompt_text = build_prompt(page)
    analysis_started_at = datetime.now(timezone.utc)
    analysis_start_perf = time.perf_counter()
    ai_payload = client.analyze(prompt_text) if client else {}
    analysis_completed_at = datetime.now(timezone.utc)
    analysis_elapsed_seconds = time.perf_counter() - analysis_start_perf

    raw_result = ai_payload.get("result") or ""
    answers = parse_answers(raw_result)

    analysis = {
        "url": url,
        "title": title or "",
        "summary": summary or "",
        "provider": ai_payload.get("provider"),
        "model": getattr(client, "model", "stub"),
        "analyzed_at": analysis_completed_at.isoformat(),
        "analysis_started_at": analysis_started_at.isoformat(),
        "analysis_completed_at": analysis_completed_at.isoformat(),
        "analysis_elapsed_seconds": analysis_elapsed_seconds,
        "prompt": ai_payload.get("user_prompt", prompt_text),
        "system_prompt": ai_payload.get("system_prompt"),
        "prompt_version": ai_payload.get("prompt_version"),
        "ai_result": raw_result,
        "answers": answers,
        "source": {
            "use_case": use_case,
            "source_type": source_type,
            "source_path": source_path,
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_ascii = get_bool_setting("JSON_ENSURE_ASCII", default=False)
    output_path.write_text(json.dumps(analysis, ensure_ascii=ensure_ascii, indent=2), encoding="utf-8")
    return output_path, True, analysis_elapsed_seconds


@dataclass
class BatchItemResult:
    """Per-page batch execution details."""

    page_path: str
    output_path: str
    url: str
    saved: bool
    elapsed_seconds: float | None


@dataclass
class BatchRunStats:
    """Summary metrics for a batch run."""

    processed: int
    skipped: int
    total_elapsed_seconds: float
    items: list[BatchItemResult]


def _build_dry_run_item(
    page_path: Path,
    output_dir: Path,
    overwrite: bool,
    verbose: bool,
) -> tuple[BatchItemResult, bool]:
    page = load_page_json(page_path)
    url = str(page.get("url") or "")
    output_path = output_path_for_url(output_dir, url)
    is_skip = not overwrite and should_skip(output_path)
    if verbose:
        print(f"skip: {output_path.name}" if is_skip else f"would save: {output_path.name}")
    item = BatchItemResult(
        page_path=str(page_path),
        output_path=str(output_path),
        url=url,
        saved=False,
        elapsed_seconds=None,
    )
    return item, is_skip


def _build_processed_item(
    page_path: Path,
    output_dir: Path,
    client,
    overwrite: bool,
    verbose: bool,
    use_case: str | None,
    source_type: str,
    source_path: str | None,
) -> tuple[BatchItemResult, bool, float | None]:
    page = load_page_json(page_path)
    url = str(page.get("url") or "")
    output_path, saved, elapsed = analyze_page(
        page_path,
        output_dir,
        client,
        overwrite=overwrite,
        use_case=use_case,
        source_type=source_type,
        source_path=source_path,
    )
    if verbose:
        print(f"saved: {output_path.name}" if saved else f"skip: {output_path.name}")
    item = BatchItemResult(
        page_path=str(page_path),
        output_path=str(output_path),
        url=url,
        saved=saved,
        elapsed_seconds=elapsed,
    )
    return item, not saved, elapsed


def run_batch(
    input_dir: Path,
    output_dir: Path,
    client,
    max_items: int | None = None,
    verbose: bool = True,
    overwrite: bool = False,
    dry_run: bool = False,
    use_case: str | None = None,
    source_type: str = "pages",
    source_path: str | None = None,
) -> BatchRunStats:
    """Run analysis over a batch of saved pages with minimal console output."""
    count = 0
    skipped = 0
    total_elapsed_seconds = 0.0
    items: list[BatchItemResult] = []
    for page_path in iter_pages(input_dir):
        if dry_run:
            item, is_skip = _build_dry_run_item(page_path, output_dir, overwrite, verbose)
            elapsed = None
        else:
            item, is_skip, elapsed = _build_processed_item(
                page_path,
                output_dir,
                client,
                overwrite,
                verbose,
                use_case,
                source_type,
                source_path or str(input_dir),
            )
        items.append(item)
        if is_skip:
            skipped += 1
        if elapsed is not None:
            total_elapsed_seconds += elapsed
        count += 1
        if max_items and count >= max_items:
            break
    if verbose:
        total_minutes = total_elapsed_seconds / 60.0
        print(
            "done: "
            f"processed={count} skipped={skipped} "
            f"total_elapsed_seconds={total_elapsed_seconds:.2f} "
            f"total_elapsed_minutes={total_minutes:.2f}"
        )
    return BatchRunStats(
        processed=count,
        skipped=skipped,
        total_elapsed_seconds=total_elapsed_seconds,
        items=items,
    )
