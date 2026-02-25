"""Exporter for analysis results to Markdown format."""

import json
from pathlib import Path


def export_analysis_to_md(
    input_dir: Path,
    output_dir: Path,
    combine: bool = False,
    include_header: bool = True,
    overwrite: bool = False,
    verbose: bool = True,
    dry_run: bool = False,
) -> None:
    """Export analysis results from JSON files to Markdown format.
    Args:
        input_dir: Directory containing analysis JSON files.
        output_dir: Directory to save exported Markdown files.
        combine: If True, combine all analyses into a single Markdown file.
        include_header: If True, include metadata header in each Markdown file.
        overwrite: If True, overwrite existing files.
        verbose: If True, print progress messages.
        dry_run: If True, simulate the export without writing files.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(input_dir.glob("*.json"))

    combined_lines = []
    saved = 0
    skipped = 0
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        ai_result = data.get("ai_result") or ""
        header = _build_header(data) if include_header else ""
        if header:
            content = header + "\n" + ai_result.strip() + "\n"
        else:
            content = ai_result.strip() + "\n"

        if combine:
            combined_lines.append(content)
        else:
            output_path = output_dir / (path.stem + ".md")
            if output_path.exists() and not overwrite:
                skipped += 1
                if verbose:
                    print(f"skip: {output_path.name}")
                continue
            if dry_run:
                saved += 1
                if verbose:
                    print(f"would save: {output_path.name}")
                continue
            output_path.write_text(content, encoding="utf-8")
            saved += 1
            if verbose:
                print(f"saved: {output_path.name}")

    if combine:
        combined_path = output_dir / "all.md"
        if combined_path.exists() and not overwrite:
            skipped += 1
            if verbose:
                print(f"skip: {combined_path.name}")
            return
        if dry_run:
            saved += 1
            if verbose:
                print(f"would save: {combined_path.name}")
        else:
            combined_path.write_text("\n\n".join(combined_lines).strip() + "\n", encoding="utf-8")
            saved += 1
            if verbose:
                print(f"saved: {combined_path.name}")

    if verbose:
        print(f"done: saved={saved} skipped={skipped}")


def _build_header(data: dict) -> str:
    parts = []
    url = data.get("url")
    model = data.get("model")
    provider = data.get("provider")
    analyzed_at = data.get("analyzed_at")
    analysis_started_at = data.get("analysis_started_at")
    analysis_completed_at = data.get("analysis_completed_at")
    analysis_elapsed_seconds = data.get("analysis_elapsed_seconds")
    prompt_version = data.get("prompt_version")

    if url:
        parts.append(f"URL: {url}")
    if provider:
        parts.append(f"Provider: {provider}")
    if model:
        parts.append(f"Model: {model}")
    if analyzed_at:
        parts.append(f"Analyzed At: {analyzed_at}")
    if analysis_started_at:
        parts.append(f"Analysis Started At: {analysis_started_at}")
    if analysis_completed_at:
        parts.append(f"Analysis Completed At: {analysis_completed_at}")
    if analysis_elapsed_seconds is not None:
        parts.append(f"Analysis Elapsed Seconds: {analysis_elapsed_seconds}")
    if prompt_version:
        parts.append(f"Prompt Version: {prompt_version}")

    if not parts:
        return ""
    return "\n".join(parts)
