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
    export_analysis_to_excel(
        input_dir=Path(args.input),
        output_path=Path(args.output),
        overwrite=args.overwrite,
        verbose=not args.quiet,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
