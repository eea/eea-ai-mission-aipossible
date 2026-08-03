"""Markdown reporting for pre-analysis runs."""

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def _collect_counts(rows: list[dict]) -> tuple[Counter[str], Counter[str], dict[str, list[int]]]:
    status_counts: Counter[str] = Counter()
    pattern_counts: Counter[str] = Counter()
    pattern_lengths: dict[str, list[int]] = {}
    for row in rows:
        status = row.get("status", {})
        status_key = "processed" if status.get("processed") else status.get("skip_reason", "skipped")
        status_counts[status_key] += 1
        pattern = row.get("pattern")
        if pattern:
            pattern_counts[pattern] += 1
            length = len(row.get("normalized", "") or "")
            pattern_lengths.setdefault(pattern, []).append(length)
    return status_counts, pattern_counts, pattern_lengths


def _render_metadata_section(run_meta: dict, now: str) -> list[str]:
    lines = ["# Pre-analysis Report", "", "## Run Metadata", f"- Generated At: {now}"]
    for key, value in run_meta.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    return lines


def _render_summary_section(rows: list[dict], status_counts: Counter[str], pattern_counts: Counter[str]) -> list[str]:
    lines = ["## Summary", f"- Total Rows: {len(rows)}"]
    for key, count in status_counts.items():
        lines.append(f"- {key}: {count}")
    if pattern_counts:
        lines.append("- Patterns:")
        for key, count in pattern_counts.most_common():
            lines.append(f"  - {key}: {count}")
    lines.append("")
    return lines


def _render_quantification_section(
    rows: list[dict], pattern_counts: Counter[str], pattern_lengths: dict[str, list[int]]
) -> list[str]:
    if not pattern_counts:
        return []
    lines = ["## Quantification Ideas"]
    total_rows = len(rows) if rows else 1
    for pattern, count in pattern_counts.most_common():
        lengths = pattern_lengths.get(pattern, [])
        avg_len = (sum(lengths) / len(lengths)) if lengths else 0
        percent = (count / total_rows) * 100
        lines.append(f"- {pattern}:")
        lines.append(f"  - Count: {count}")
        lines.append(f"  - Share of rows: {percent:.1f}%")
        lines.append(f"  - Avg text length: {avg_len:.1f} chars")
    lines.append("")
    return lines


def _render_prompts_section(rows: list[dict], pattern_counts: Counter[str]) -> list[str]:
    lines = ["## Generated Prompts"]
    if not pattern_counts:
        lines.append("- No patterns detected; use generic quantification prompts.")
        lines.append("")
        return lines

    total_rows = len(rows) if rows else 1
    threshold = 0.1
    lines.append(f"- Criteria: patterns appearing in >= {threshold * 100:.0f}% of rows.")
    for pattern, count in pattern_counts.most_common():
        if (count / total_rows) < threshold:
            continue
        lines.append(f"- Pattern: {pattern}")
        lines.append(
            f"  - Extract numeric quantities with units related to '{pattern}', and map each value to its subject."
        )
        lines.append(
            f"  - Extract budgets, counts, and thresholds mentioned within '{pattern}', "
            "including currency, units, and timelines."
        )
    lines.append("")
    return lines


def _render_row_ai_output(row: dict) -> list[str]:
    pattern = row.get("pattern") or ""
    explanation = row.get("explanation") or ""
    confidence = row.get("confidence")
    if not (pattern or explanation or confidence is not None):
        return []
    payload = {"pattern": pattern, "explanation": explanation, "confidence": confidence}
    return [
        "- AI Output:",
        "",
        "```json",
        json.dumps(payload, ensure_ascii=False, indent=2),
        "```",
    ]


def _render_row(row: dict) -> list[str]:
    row_index = row.get("row_index")
    normalized = row.get("normalized", "")
    truncated = row.get("truncated", False)
    status = row.get("status", {})
    status_label = "processed" if status.get("processed") else f"skipped ({status.get('skip_reason')})"

    lines = [f"### Row {row_index}", f"- Status: {status_label}"]
    if truncated:
        lines.append("- Truncated: true")
    if normalized:
        lines.extend(["- Input:", "", "```", normalized, "```"])
    lines.extend(_render_row_ai_output(row))
    lines.append("")
    return lines


def _render_rows_section(rows: list[dict]) -> list[str]:
    lines = ["## Rows"]
    for row in rows:
        lines.extend(_render_row(row))
    return lines


def build_report(
    run_meta: dict,
    rows: list[dict],
) -> str:
    now = datetime.now(timezone.utc).isoformat()
    status_counts, pattern_counts, pattern_lengths = _collect_counts(rows)

    lines = [
        *_render_metadata_section(run_meta, now),
        *_render_summary_section(rows, status_counts, pattern_counts),
        *_render_quantification_section(rows, pattern_counts, pattern_lengths),
        *_render_prompts_section(rows, pattern_counts),
        *_render_rows_section(rows),
    ]
    return "\n".join(lines).strip() + "\n"


def write_report(path: Path, content: str, overwrite: bool = False) -> bool:
    if path.exists() and not overwrite:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True
