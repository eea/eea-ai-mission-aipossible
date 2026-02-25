"""Markdown reporting for pre-analysis runs."""

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import json


def build_report(
    run_meta: dict,
    rows: list[dict],
) -> str:
    now = datetime.now(timezone.utc).isoformat()
    lines = []
    lines.append("# Pre-analysis Report")
    lines.append("")
    lines.append("## Run Metadata")
    lines.append(f"- Generated At: {now}")
    for key, value in run_meta.items():
        lines.append(f"- {key}: {value}")
    lines.append("")

    status_counts = Counter()
    pattern_counts = Counter()
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

    lines.append("## Summary")
    lines.append(f"- Total Rows: {len(rows)}")
    if status_counts:
        for key, count in status_counts.items():
            lines.append(f"- {key}: {count}")
    if pattern_counts:
        lines.append("- Patterns:")
        for key, count in pattern_counts.most_common():
            lines.append(f"  - {key}: {count}")
    lines.append("")

    if pattern_counts:
        lines.append("## Quantification Ideas")
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

    lines.append("## Generated Prompts")
    if pattern_counts:
        total_rows = len(rows) if rows else 1
        threshold = 0.1
        lines.append(
            f"- Criteria: patterns appearing in >= {threshold * 100:.0f}% of rows."
        )
        for pattern, count in pattern_counts.most_common():
            if (count / total_rows) < threshold:
                continue
            lines.append(f"- Pattern: {pattern}")
            lines.append(
                f"  - Extract numeric quantities with units related to '{pattern}', and map each value to its subject."
            )
            lines.append(
                f"  - Extract budgets, counts, and thresholds mentioned within '{pattern}', including currency, units, and timelines."
            )
    else:
        lines.append("- No patterns detected; use generic quantification prompts.")
    lines.append("")

    lines.append("## Rows")
    for row in rows:
        row_index = row.get("row_index")
        normalized = row.get("normalized", "")
        truncated = row.get("truncated", False)
        status = row.get("status", {})
        status_label = "processed" if status.get("processed") else f"skipped ({status.get('skip_reason')})"
        lines.append(f"### Row {row_index}")
        lines.append(f"- Status: {status_label}")
        if truncated:
            lines.append("- Truncated: true")
        if normalized:
            lines.append("- Input:")
            lines.append("")
            lines.append("```")
            lines.append(normalized)
            lines.append("```")
        pattern = row.get("pattern") or ""
        explanation = row.get("explanation") or ""
        confidence = row.get("confidence")
        if pattern or explanation or confidence is not None:
            lines.append("- AI Output:")
            lines.append("")
            lines.append("```json")
            payload = {
                "pattern": pattern,
                "explanation": explanation,
                "confidence": confidence,
            }
            lines.append(json.dumps(payload, ensure_ascii=False, indent=2))
            lines.append("```")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def write_report(path: Path, content: str, overwrite: bool = False) -> bool:
    if path.exists() and not overwrite:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True
