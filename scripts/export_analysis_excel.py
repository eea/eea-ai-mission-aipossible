"""Script to export analysis JSON files to a single Excel workbook."""

import argparse
from pathlib import Path

from exporters.analysis_excel_exporter import export_analysis_to_excel


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for the export analysis script.
    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Export analysis JSON files to a single Excel workbook.")
    parser.add_argument(
        "--input",
        default="data/analysis",
        help="Input directory with analysis JSON files.",
    )
    parser.add_argument(
        "--output",
        default="data/exports/analysis.xlsx",
        help="Output Excel file path.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional run folder name inside --input (for example: 20260227_143015).",
    )
    parser.add_argument(
        "--no-header-bold",
        action="store_true",
        help="Disable bold formatting for header row.",
    )
    parser.add_argument(
        "--no-auto-width",
        action="store_true",
        help="Disable automatic column width sizing.",
    )
    parser.add_argument(
        "--no-wrap-text",
        action="store_true",
        help="Disable wrapped text for body cells.",
    )
    parser.add_argument(
        "--freeze-panes",
        default="A2",
        help='Freeze panes reference (for example "A2"). Ignored when --no-freeze-panes is set.',
    )
    parser.add_argument(
        "--no-freeze-panes",
        action="store_true",
        help="Disable freeze panes in the output workbook.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output file.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be exported without writing outputs.",
    )
    return parser.parse_args()


def main() -> int:
    """
    Main function to parse arguments and export analysis JSON files to a single Excel workbook.

    Returns:
        int: Exit code (0 for success).
    """
    args = parse_args()
    input_dir = Path(args.input)
    if args.run_id:
        input_dir = input_dir / args.run_id
    freeze_panes = None if args.no_freeze_panes else args.freeze_panes

    export_analysis_to_excel(
        input_dir=input_dir,
        output_path=Path(args.output),
        overwrite=args.overwrite,
        verbose=not args.quiet,
        dry_run=args.dry_run,
        header_bold=not args.no_header_bold,
        auto_width=not args.no_auto_width,
        wrap_text=not args.no_wrap_text,
        freeze_panes=freeze_panes,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
