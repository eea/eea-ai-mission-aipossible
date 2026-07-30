"""Script to export scraped page JSON files to a JSONL format."""

import argparse
from pathlib import Path

from exporters.pages_exporter import export_pages_to_jsonl


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the export script.

    Returns:
        argparse.Namespace: Parsed command-line arguments.

    """
    parser = argparse.ArgumentParser(description="Export scraped page JSON files to JSONL.")
    parser.add_argument(
        "--input",
        default="data/pages",
        help="Input directory with page JSON files.",
    )
    parser.add_argument(
        "--output",
        default="data/exports/pages.jsonl",
        help="Output JSONL file path.",
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
    """Main function to parse arguments and export scraped page JSON files to JSONL format.

    Returns:
        int: Exit code (0 for success).

    """
    args = parse_args()
    export_pages_to_jsonl(
        input_dir=Path(args.input),
        output_path=Path(args.output),
        overwrite=args.overwrite,
        verbose=not args.quiet,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
