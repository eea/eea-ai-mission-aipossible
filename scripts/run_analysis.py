"""CLI entry point for running AI analysis over saved pages or configured use cases."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from analysis.analyzer import run_batch
from analysis.clients.env_loader import load_env_file
from analysis.clients.factory import get_client
from analysis.excel_analyzer import run_batch as run_excel_batch
from api.service import (
    UseCaseConfig,
    UseCaseConfigurationError,
    _load_system_prompt_override,
    _load_user_prompt_override,
    _resolve_use_case,
)

repo_root = Path(__file__).resolve().parents[1]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parses command-line arguments for the AI analysis script.

    Returns:
        argparse.Namespace: Namespace containing parsed arguments:
            --use-case: Optional use-case preset key defined in config/analysis_use_cases.json.
            --source-path: Optional absolute path override for the use-case source.
            --input: Input directory with page JSON files.
            --output: Output directory for analysis JSON files.
            --max-items: Maximum number of pages to analyze.
            --provider: AI provider name (mock, openai, or eea).
            --model: AI model name (overrides .env MODEL).
            --api-url: API URL (overrides .env API_URL).
            --api-key: API key (overrides .env.keys API_KEY).
            --system-prompt-file: Absolute path to a system prompt file override.
            --user-prompt-file: Absolute path to a user prompt file override.
            --sheet-name/--column-name/--header-row: Excel source overrides for use-case mode.
            --quiet: Suppress progress output.
            --overwrite: Overwrite existing analysis files.
            --dry-run: Show what would be processed without writing outputs.
            --file: Specify a single JSON file in the pages folder to analyze (overrides --input).

    """
    parser = argparse.ArgumentParser(description="Run AI analysis over saved pages.")
    repo_root_path = Path(__file__).resolve().parents[1]
    env_values = load_env_file(repo_root_path / ".env")
    parser.add_argument(
        "--use-case",
        default=None,
        help="Optional use-case preset key defined in config/analysis_use_cases.json.",
    )
    parser.add_argument(
        "--source-path",
        default=None,
        help="Absolute path override for the selected use-case source.",
    )
    parser.add_argument(
        "--file",
        default=None,
        help="Specify a single JSON file in the pages folder to analyze (overrides --input).",
    )
    parser.add_argument(
        "--input",
        default="data/pages",
        help="Input directory with page JSON files.",
    )
    parser.add_argument(
        "--output",
        default=env_values.get("OUTPUT_DIR", "data/analysis"),
        help="Output directory for analysis JSON files.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Maximum number of pages to analyze.",
    )
    parser.add_argument(
        "--provider",
        default=env_values.get("PROVIDER", "mock"),
        help="AI provider name (mock, openai, or eea). Overrides PROVIDER in .env.",
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
        "--system-prompt-file",
        default=None,
        help="Absolute path to a system prompt file override.",
    )
    parser.add_argument(
        "--user-prompt-file",
        default=None,
        help="Absolute path to a user prompt file override.",
    )
    parser.add_argument(
        "--sheet-name",
        default=None,
        help="Excel sheet name override when using --use-case with an excel source.",
    )
    parser.add_argument(
        "--column-name",
        default=None,
        help="Excel column name override when using --use-case with an excel source.",
    )
    parser.add_argument(
        "--header-row",
        type=int,
        default=None,
        help="Excel header row override when using --use-case with an excel source.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing analysis files.",
    )
    parser.add_argument(
        "--timestamped-output-dir",
        action="store_true",
        help="Create a date-time subfolder inside --output and store run results there.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without writing outputs.",
    )
    return parser.parse_args(argv)


def resolve_output_dir(output: str, timestamped_output_dir: bool) -> Path:
    base_output_dir = Path(output)
    if not timestamped_output_dir:
        return base_output_dir
    folder_name = datetime.now().strftime("%Y%m%d_%H%M%S")
    return base_output_dir / folder_name


def _explicit_flag(argv: list[str], *names: str) -> bool:
    return any(name in argv for name in names)


def _require_absolute_path(raw_value: str, flag_name: str) -> Path:
    path = Path(raw_value)
    if not path.is_absolute():
        raise ValueError(f"{flag_name} must be an absolute path: {raw_value}")
    return path


def _load_system_prompt_file(path: Path) -> str:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"System prompt file not found: {path}")
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"System prompt file is empty: {path}")
    return content


def _load_user_prompt_file(path: Path) -> str:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"User prompt file not found: {path}")
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"User prompt file is empty: {path}")
    return content


def _resolve_use_case_overrides(args: argparse.Namespace, argv: list[str]) -> UseCaseConfig:
    if not args.use_case:
        raise ValueError("Missing required field: use_case")

    resolved = _resolve_use_case(args.use_case)
    if args.source_path:
        source_path = _require_absolute_path(args.source_path, "--source-path")
    elif _explicit_flag(argv, "--input"):
        source_path = _require_absolute_path(args.input, "--input")
    else:
        source_path = resolved.source_path
    system_prompt_path = (
        _require_absolute_path(args.system_prompt_file, "--system-prompt-file")
        if args.system_prompt_file
        else resolved.system_prompt_path
    )
    user_prompt_path = (
        _require_absolute_path(args.user_prompt_file, "--user-prompt-file")
        if args.user_prompt_file
        else resolved.user_prompt_path
    )
    header_row = args.header_row if args.header_row is not None else resolved.header_row

    if args.use_case and header_row < 1:
        raise ValueError("--header-row must be >= 1")

    return UseCaseConfig(
        name=resolved.name,
        source_type=resolved.source_type,
        source_path=source_path,
        system_prompt_path=system_prompt_path,
        user_prompt_path=user_prompt_path,
        sheet_name=args.sheet_name or resolved.sheet_name,
        column_name=args.column_name or resolved.column_name,
        header_row=header_row,
        row_identifier_column=resolved.row_identifier_column,
    )


def main() -> int:  # noqa: C901
    """Main function to parse arguments, set up environment, and run AI analysis batch.

    Returns:
        int: Exit code (0 for success).

    """
    argv = sys.argv[1:]
    args = parse_args(argv)
    env_values = load_env_file(repo_root / f".env.{args.provider}")
    key_values = load_env_file(repo_root / f".env.{args.provider}.keys")
    model = args.model or env_values.get("MODEL") or env_values.get("AI_MODEL") or "stub"
    api_url = args.api_url or env_values.get("API_URL") or ""
    api_key = args.api_key or key_values.get("API_KEY") or key_values.get("AI_API_KEY") or ""
    prompts_dir = (repo_root / "analysis/prompts").resolve()
    output_base = (
        _require_absolute_path(args.output, "--output") if _explicit_flag(argv, "--output") else Path(args.output)
    )
    effective_timestamped_output_dir = args.timestamped_output_dir or bool(args.use_case)
    output_dir = resolve_output_dir(str(output_base), effective_timestamped_output_dir)
    if effective_timestamped_output_dir and args.overwrite:
        print(
            "warning: --timestamped-output-dir creates a new folder on each run; "
            "--overwrite does not make a difference."
        )

    system_prompt_override = None
    if args.system_prompt_file and not args.use_case:
        system_prompt_override = _load_system_prompt_file(
            _require_absolute_path(args.system_prompt_file, "--system-prompt-file")
        )
    user_prompt_override = None
    if args.user_prompt_file:
        user_prompt_override = _load_user_prompt_file(
            _require_absolute_path(args.user_prompt_file, "--user-prompt-file")
        )

    try:
        use_case_config = _resolve_use_case_overrides(args, argv) if args.use_case else None
    except (UseCaseConfigurationError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    if use_case_config:
        try:
            system_prompt_override = _load_system_prompt_override(use_case_config)
            if not user_prompt_override:
                user_prompt_override = _load_user_prompt_override(use_case_config)
        except UseCaseConfigurationError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    client = get_client(
        provider=args.provider,
        api_key=api_key,
        model=model,
        api_url=api_url,
        prompts_dir=prompts_dir,
        user_prompt_template=user_prompt_override,
        system_prompt_template=system_prompt_override,
    )
    # If --file is specified, run analysis only for that file
    if args.file:
        if use_case_config and use_case_config.source_type != "pages":
            raise ValueError("--file can only be used with page-based analysis.")
        from analysis.utils import load_page_json, output_path_for_url

        page_path = _require_absolute_path(args.file, "--file")
        page = load_page_json(page_path)
        output_path_file = output_path_for_url(output_dir, page.get("url", ""))
        # Check if file exists and should be skipped
        from analysis.analyzer import analyze_page, should_skip

        if not args.overwrite and should_skip(output_path_file):
            print(f"skip: {output_path_file.name} (already exists, use --overwrite to replace)")
            return 0
        analyze_page(
            page_path,
            output_dir,
            client,
            overwrite=args.overwrite,
            use_case=use_case_config.name if use_case_config else None,
            source_type=use_case_config.source_type if use_case_config else "pages",
            source_path=str(use_case_config.source_path) if use_case_config else str(page_path.parent),
        )
    elif use_case_config and use_case_config.source_type == "excel":
        if not use_case_config.source_path.is_file():
            print(
                f"Error: Source file not found for use case '{use_case_config.name}': {use_case_config.source_path}",
                file=sys.stderr,
            )
            return 1
        try:
            run_excel_batch(
                input_file=use_case_config.source_path,
                sheet_name=use_case_config.sheet_name or "",
                column_name=use_case_config.column_name or "",
                header_row=use_case_config.header_row,
                output_dir=output_dir,
                client=client,
                max_items=args.max_items,
                verbose=not args.quiet,
                overwrite=args.overwrite,
                dry_run=args.dry_run,
                use_case=use_case_config.name,
                source_type=use_case_config.source_type,
                source_path=str(use_case_config.source_path),
                row_identifier_column=use_case_config.row_identifier_column,
            )
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
    else:
        input_dir = (
            use_case_config.source_path
            if use_case_config
            else (
                _require_absolute_path(args.input, "--input") if _explicit_flag(argv, "--input") else Path(args.input)
            )
        )
        if use_case_config and not input_dir.is_dir():
            print(
                f"Error: Source directory not found for use case '{use_case_config.name}': {input_dir}",
                file=sys.stderr,
            )
            return 1
        run_batch(
            input_dir=input_dir,
            output_dir=output_dir,
            client=client,
            max_items=args.max_items,
            verbose=not args.quiet,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
            use_case=use_case_config.name if use_case_config else None,
            source_type=use_case_config.source_type if use_case_config else "pages",
            source_path=str(use_case_config.source_path) if use_case_config else str(input_dir),
        )
    if use_case_config:
        print(f"run_id: {output_dir.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
