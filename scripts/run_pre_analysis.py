"""CLI entry point for running AI pre-analysis over Excel data sources."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from analysis.clients.env_loader import load_env_file
from analysis.clients.factory import get_client
from pre_analysis.analyzer import run_batch
from pre_analysis.reporting import build_report, write_report

repo_root = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the pre-analysis runner."""
    parser = argparse.ArgumentParser(description="Run AI pre-analysis on Excel data sources.")
    parser.add_argument(
        "--input-file",
        required=True,
        help="Excel file path (e.g. data/data_sources/2_1_1.xlsx).",
    )
    parser.add_argument(
        "--sheet-name",
        required=True,
        help="Sheet name to analyze (exact match).",
    )
    parser.add_argument(
        "--column",
        required=True,
        help="Column header name to analyze (exact match).",
    )
    parser.add_argument(
        "--header-row",
        type=int,
        default=1,
        help="Row index containing column headers (default: 1).",
    )
    parser.add_argument(
        "--start-row",
        type=int,
        default=None,
        help="Row index to start processing (default: header_row + 1).",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Maximum number of rows to process (counts empty cells).",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=4000,
        help="Maximum characters per cell to send to the model.",
    )
    parser.add_argument(
        "--output",
        default="data/pre_analysis",
        help="Output directory for row JSON files and report.",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Markdown report path (default: <output>/report.md).",
    )
    parser.add_argument(
        "--provider",
        default="mock",
        help="AI provider name (mock, openai, or eea).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="AI model name (overrides .env MODEL).",
    )
    parser.add_argument(
        "--api-url",
        default=None,
        help="API URL (overrides .env API_URL).",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key (overrides .env.keys API_KEY).",
    )
    parser.add_argument(
        "--prompts-dir",
        default="pre_analysis/prompts",
        help="Directory containing system_prompt.txt and user_prompt.txt.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing row outputs and report (legacy; sets both overwrite flags).",
    )
    parser.add_argument(
        "--overwrite-rows",
        action="store_true",
        help="Overwrite existing row outputs.",
    )
    parser.add_argument(
        "--overwrite-report",
        action="store_true",
        help="Overwrite existing report.md output.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without writing outputs.",
    )
    return parser.parse_args()


def _load_row_payload(path: Path) -> dict:
    """Load a saved row JSON payload and normalize fields for reporting."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "row_index": data.get("source", {}).get("row_index"),
        "normalized": data.get("content", {}).get("normalized", ""),
        "truncated": data.get("content", {}).get("truncated", False),
        "pattern": data.get("ai", {}).get("pattern", ""),
        "explanation": data.get("ai", {}).get("explanation", ""),
        "confidence": data.get("ai", {}).get("confidence"),
        "status": data.get("status", {}),
    }


def main() -> int:
    """Run pre-analysis and write row outputs plus a summary report."""
    args = parse_args()
    input_file = Path(args.input_file)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    output_dir = Path(args.output)
    report_path = Path(args.report) if args.report else output_dir / "report.md"
    prompts_dir = (repo_root / args.prompts_dir).resolve()
    overwrite_rows = args.overwrite or args.overwrite_rows
    overwrite_report = args.overwrite or args.overwrite_report

    env_values = load_env_file(repo_root / f".env.{args.provider}")
    key_values = load_env_file(repo_root / f".env.{args.provider}.keys")
    model = args.model or env_values.get("MODEL") or env_values.get("AI_MODEL") or "stub"
    api_url = args.api_url or env_values.get("API_URL") or ""
    api_key = args.api_key or key_values.get("API_KEY") or key_values.get("AI_API_KEY") or ""

    client = get_client(
        provider=args.provider,
        api_key=api_key,
        model=model,
        api_url=api_url,
        prompts_dir=prompts_dir,
    )

    run_started_at = datetime.now(timezone.utc).isoformat()
    result = run_batch(
        input_file=input_file,
        sheet_name=args.sheet_name,
        column_header=args.column,
        header_row=args.header_row,
        start_row=args.start_row,
        max_rows=args.max_items,
        output_dir=output_dir,
        client=client,
        max_chars=args.max_chars,
        verbose=not args.quiet,
        overwrite=overwrite_rows,
        dry_run=args.dry_run,
    )
    run_completed_at = datetime.now(timezone.utc).isoformat()

    if args.dry_run:
        return 0

    rows = []
    for row in result.get("rows", []):
        status = row.get("status", {})
        output_path = row.get("output_path")
        if output_path and Path(output_path).exists():
            rows.append(_load_row_payload(Path(output_path)))
            continue
        rows.append(
            {
                "row_index": row.get("row_index"),
                "normalized": "",
                "truncated": False,
                "pattern": "",
                "explanation": "",
                "confidence": None,
                "status": status,
            }
        )

    run_meta = {
        "Input File": str(input_file),
        "Sheet Name": args.sheet_name,
        "Column": args.column,
        "Header Row": args.header_row,
        "Start Row": args.start_row or (args.header_row + 1),
        "Max Items": args.max_items if args.max_items is not None else "all",
        "Max Chars": args.max_chars,
        "Provider": args.provider,
        "Model": model,
        "Prompt Version": getattr(client, "prompt_version", ""),
        "Run Started At": run_started_at,
        "Run Completed At": run_completed_at,
    }

    report = build_report(run_meta=run_meta, rows=rows)
    saved = write_report(report_path, report, overwrite=overwrite_report)
    if not args.quiet:
        print(f"{'saved' if saved else 'skip'}: {report_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
