"""Compatibility shim for running analysis from the project root."""

from scripts.run_analysis import main

if __name__ == "__main__":
    raise SystemExit(main())
