"""CLI entrypoint to run the analysis API server."""

import argparse
import errno
import os
import socket
import sys
from pathlib import Path

import uvicorn


def _is_port_in_use(host: str, port: int) -> bool:
    """Return True when host/port cannot be bound in the current environment."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
        return False
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE or getattr(exc, "winerror", None) == 10048:
            return True
        raise
    finally:
        sock.close()


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the API server."""
    parser = argparse.ArgumentParser(description="Run Analysis API server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument(
        "--port-fallback-attempts",
        type=int,
        default=20,
        help="Number of additional ports to try when the selected port is busy",
    )
    parser.add_argument("--reload", action="store_true", help="Enable auto reload")
    parser.add_argument(
        "--input-dir",
        default=None,
        help="Default input directory for analysis runs (overrides config file API_INPUT_DIR).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Default output directory for analysis/results (overrides config file API_OUTPUT_DIR).",
    )
    parser.add_argument(
        "--export-dir",
        default=None,
        help="Default export directory for API Excel exports (overrides config file API_EXPORT_DIR).",
    )
    parser.add_argument(
        "--config-file",
        default=None,
        help="Configuration file to read defaults from. Defaults to .env.api at repo root.",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="Default provider for /v1/analysis/runs (overrides config file API_PROVIDER).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Default model for /v1/analysis/runs (overrides config file API_MODEL).",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Default API key for /v1/analysis/runs (overrides config file API_API_KEY).",
    )
    return parser.parse_args()


def main() -> int:
    """Run uvicorn server."""
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    args = parse_args()
    config_path = Path(args.config_file) if args.config_file else (repo_root / ".env.api")
    if not config_path.is_absolute():
        config_path = (repo_root / config_path).resolve()
    if not config_path.exists():
        raise SystemExit(
            f"Config file not found: {config_path}. "
            "Create .env.api at repo root or pass --config-file <path>."
        )

    os.environ["MISSION_CONFIG_FILE"] = str(config_path)
    if args.input_dir:
        os.environ["API_INPUT_DIR"] = args.input_dir
    if args.output_dir:
        os.environ["API_OUTPUT_DIR"] = args.output_dir
    if args.export_dir:
        os.environ["API_EXPORT_DIR"] = args.export_dir
    if args.provider:
        os.environ["API_PROVIDER"] = args.provider
    if args.model:
        os.environ["API_MODEL"] = args.model
    if args.api_key:
        os.environ["API_API_KEY"] = args.api_key

    selected_port = args.port
    max_attempts = max(args.port_fallback_attempts, 0)
    for offset in range(max_attempts + 1):
        candidate_port = args.port + offset
        if not _is_port_in_use(args.host, candidate_port):
            selected_port = candidate_port
            break
    else:
        last_port = args.port + max_attempts
        raise SystemExit(
            f"No free port found in range {args.port}-{last_port}. "
            "Pass --port to select another starting port."
        )

    if selected_port != args.port:
        print(f"Port {args.port} is in use. Retrying on port {selected_port}...")

    uvicorn.run(
        "api.app:app",
        host=args.host,
        port=selected_port,
        reload=args.reload,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
