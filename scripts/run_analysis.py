"""CLI entry point for running AI analysis over saved pages."""

import argparse
from pathlib import Path

from analysis.analyzer import run_batch
from analysis.clients.env_loader import load_env_file
from analysis.clients.factory import get_client

repo_root = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    """
    Parses command-line arguments for the AI analysis script.

    Returns:
        argparse.Namespace: Namespace containing parsed arguments:
            --input: Input directory with page JSON files.
            --output: Output directory for analysis JSON files.
            --max-items: Maximum number of pages to analyze.
            --provider: AI provider name (openai or eea).
            --model: AI model name (overrides .env MODEL).
            --api-url: API URL (overrides .env API_URL).
            --api-key: API key (overrides .env.keys API_KEY).
            --prompts-dir: Directory containing system_prompt.txt and user_prompt.txt.
            --quiet: Suppress progress output.
            --overwrite: Overwrite existing analysis files.
            --dry-run: Show what would be processed without writing outputs.
            --file: Specify a single JSON file in the pages folder to analyze (overrides --input).
    """
    parser = argparse.ArgumentParser(description="Run AI analysis over saved pages.")
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
        default="data/analysis",
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
        default="openai",
        help="AI provider name (openai or eea).",
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
    # Load .env for default prompt directory
    repo_root_path = Path(__file__).resolve().parents[1]
    env_values = load_env_file(repo_root_path / ".env")
    default_prompts_dir = env_values.get("prompt_directory", "analysis/prompts")
    parser.add_argument(
        "--prompts-dir",
        default=default_prompts_dir,
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
        help="Overwrite existing analysis files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without writing outputs.",
    )
    return parser.parse_args()


def main() -> int:
    """
    Main function to parse arguments, set up environment, and run AI analysis batch.

    Returns:
        int: Exit code (0 for success).
    """
    args = parse_args()
    env_values = load_env_file(repo_root / f".env.{args.provider}")
    key_values = load_env_file(repo_root / f".env.{args.provider}.keys")
    model = args.model or env_values.get("MODEL") or env_values.get("AI_MODEL") or "stub"
    api_url = args.api_url or env_values.get("API_URL") or ""
    api_key = args.api_key or key_values.get("API_KEY") or key_values.get("AI_API_KEY") or ""
    prompts_dir = (repo_root / args.prompts_dir).resolve()
    client = get_client(
        provider=args.provider,
        api_key=api_key,
        model=model,
        api_url=api_url,
        prompts_dir=prompts_dir,
    )
    # If --file is specified, run analysis only for that file
    if args.file:
        from analysis.utils import load_page_json, output_path_for_url
        page_path = Path(args.file)
        page = load_page_json(page_path)
        output_path = Path(args.output)
        output_path_file = output_path_for_url(output_path, page.get("url", ""))
        from analysis.analyzer import analyze_page
        # Check if file exists and should be skipped
        import sys
        from analysis.analyzer import should_skip
        if not args.overwrite and should_skip(output_path_file):
            print(f"skip: {output_path_file.name} (already exists, use --overwrite to replace)")
            return 0
        analyze_page(
            page_path,
            output_path,
            client,
            overwrite=args.overwrite
        )
    else:
        run_batch(
            input_dir=Path(args.input),
            output_dir=Path(args.output),
            client=client,
            max_items=args.max_items,
            verbose=not args.quiet,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
