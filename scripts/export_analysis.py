import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from exporters.analysis_exporter import export_analysis_to_md


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export analysis outputs to Markdown.")
    parser.add_argument(
        "--input",
        default="data/analysis",
        help="Input directory with analysis JSON files.",
    )
    parser.add_argument(
        "--output",
        default="data/exports",
        help="Output directory for exported files.",
    )
    parser.add_argument(
        "--combine",
        action="store_true",
        help="Write a single combined Markdown file (all.md).",
    )
    parser.add_argument(
        "--no-header",
        action="store_true",
        help="Do not include metadata header in Markdown output.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing export files.",
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
    args = parse_args()
    export_analysis_to_md(
        input_dir=Path(args.input),
        output_dir=Path(args.output),
        combine=args.combine,
        include_header=not args.no_header,
        overwrite=args.overwrite,
        verbose=not args.quiet,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
