# Mission AIpossible

<img src="assets/images/Mission_AIpossible_logo.png" alt="Mission AIpossible logo" width="240">

A lightweight pipeline to collect and analyse 'EU Mission on Adaptation' related data.

## Setup

Create and activate a virtual environment, then install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

Generated data is kept separate from code:

- `data/links/` contains link lists produced by the home spider.
- `data/pages/` contains one JSON file per scraped story page.

Basic crawl:

```powershell
scrapy crawl adaptation_stories_home -O data\links\links.json
```

Limit pages (example):

```powershell
scrapy crawl adaptation_stories_home -a max_pages=3 -O data\links\links_test.json
```

Scrape the story pages from a link list:

```powershell
scrapy crawl adaptation_stories_pages -a input_file=data/links/links.json
```

Limit how many story pages are scraped:

```powershell
scrapy crawl adaptation_stories_pages -a input_file=data/links/links.json -a max_links=3
```

## Tests

Run the parser smoke test:

```powershell
pytest -q
```

## Analysis

Docs:

- `ARCHITECTURE.md`
- `AI_GUIDE.md`

Run the analysis stub over saved pages:

```powershell
python -m scripts.run_analysis --input data/pages --output data/analysis --max-items 5
```

Suppress progress output:

```powershell
python -m scripts.run_analysis --input data/pages --output data/analysis --max-items 5 --quiet
```

Overwrite existing analysis outputs:

```powershell
python -m scripts.run_analysis --input data/pages --output data/analysis --max-items 5 --overwrite
```

Create a timestamped output subfolder (for example `data/analysis/20260227_143015`):

```powershell
python -m scripts.run_analysis --input data/pages --output data/analysis --max-items 5 --timestamped-output-dir
```

If you combine `--timestamped-output-dir` with `--overwrite`, the script prints a warning because each run writes to a new folder, so overwrite has no practical effect.

Dry run (no files written):

```powershell
python -m scripts.run_analysis --input data/pages --output data/analysis --max-items 5 --dry-run
```

Select provider and model:

```powershell
python -m scripts.run_analysis --provider openai --model gpt-4o --input data/pages --output data/analysis
```

Use the mock provider (no API calls, no token usage):

```powershell
python -m scripts.run_analysis --provider mock --input data/pages --output data/analysis --max-items 5
```

Example for using inside the Virtual Machine of EEA

```powershell
python -m scripts.run_analysis --provider eea --input data/pages --output data/analysis --max-items 5
```

## Analysis API

Run the API server:

```powershell
uvicorn api.app:app --host 127.0.0.1 --port 8000 --reload
```

With plain `uvicorn`, set environment variables before startup:

```powershell
$env:API_INPUT_DIR="data/pages"; $env:API_OUTPUT_DIR="data/analysis"; uvicorn api.app:app --host 127.0.0.1 --port 8000 --reload
```

Run the API server with configurable default input/output directories:

```powershell
python -m scripts.run_analysis_api --host 127.0.0.1 --port 8000 --reload --input-dir C:/absolute/path/to/data/pages --output-dir C:/absolute/path/to/data/analysis --export-dir C:/absolute/path/to/data/exports
```

You can also keep defaults in a config file (`.env.api` by default):

```text
API_INPUT_DIR=C:/absolute/path/to/eea-ai-mission-aipossible/data/pages
API_OUTPUT_DIR=C:/absolute/path/to/eea-ai-mission-aipossible/data/analysis
API_EXPORT_DIR=C:/absolute/path/to/eea-ai-mission-aipossible/data/exports
API_PROVIDER=mock
# API_MODEL=mock-model
# API_API_KEY=
```

When `--input-dir`, `--output-dir`, or `--export-dir` is passed, it overrides config-file values for that server run.
When `--provider`, `--model`, or `--api-key` is passed, it overrides `API_PROVIDER`, `API_MODEL`, or `API_API_KEY`.
If you do not pass `--config-file`, the server looks for `.env.api` in the repo root and exits with an error if it is missing.
`/v1/analysis/runs` fails with `404` if configured `API_INPUT_DIR` or `API_OUTPUT_DIR` does not exist.
`/v1/analysis/runs` returns `400` with a clear message if provider credentials are missing
(for example missing `.env.<provider>.keys` and no `API_API_KEY` override).

Health check:

```powershell
Invoke-RestMethod -Method GET http://127.0.0.1:8000/health
```

Run analysis (sync):

```powershell
Invoke-RestMethod -Method POST http://127.0.0.1:8000/v1/analysis/runs -ContentType "application/json" -Body '{"max_items":3}'
```

The response includes `run_id`, which is the folder name created under `data/analysis` for that run.

Provider/model/api key for runs are configured at API server level (`.env.api` or `scripts.run_analysis_api` args), not in the run request payload.
The run request payload currently accepts only `max_items` (optional).

Runs are written into timestamped output subfolders (`output_dir/YYYYMMDD_HHMMSS`) by default.

Download all analysis files for a run as ZIP:

```powershell
Invoke-WebRequest -Method GET "http://127.0.0.1:8000/v1/analysis/runs/<run_id>/download" -OutFile "run_<run_id>.zip"
```

Download Excel export for one run folder:

```powershell
Invoke-WebRequest -Method GET "http://127.0.0.1:8000/v1/analysis/export/excel?run_id=<run_id>" -OutFile "analysis_<run_id>.xlsx"
```

The API writes the workbook to `API_EXPORT_DIR/<run_id>/analysis_<run_id>.xlsx` and then streams that same file in the response.

Provider-specific defaults still come from:

- `.env.openai` and `.env.openai.keys`
- `.env.eea` and `.env.eea.keys`

Use the EEA provider:

```powershell
python -m scripts.run_analysis --provider eea --model eea-model --input data/pages --output data/analysis
```

## Export

Export analysis JSON files to Excel:

```powershell
python -m scripts.export_analysis_excel --input data/analysis --output data/exports/analysis.xlsx
```

Export one timestamped run folder to Excel:

```powershell
python -m scripts.export_analysis_excel --input data/analysis --run-id 20260227_143015 --output data/exports/run_20260227_143015.xlsx
```

Disable default formatting options:

```powershell
python -m scripts.export_analysis_excel --input data/analysis --output data/exports/analysis_plain.xlsx --no-header-bold --no-auto-width --no-wrap-text --no-freeze-panes
```

Export `ai_result` to Markdown files:

```powershell
python -m scripts.export_analysis --input data/analysis --output data/exports
```

Combine all outputs into one file:

```powershell
python -m scripts.export_analysis --input data/analysis --output data/exports --combine
```

Skip the metadata header:

```powershell
python -m scripts.export_analysis --input data/analysis --output data/exports --no-header
```

Overwrite existing export files:

```powershell
python -m scripts.export_analysis --input data/analysis --output data/exports --overwrite
```

Suppress export progress output:

```powershell
python -m scripts.export_analysis --input data/analysis --output data/exports --quiet
```

Dry run for export (no files written):

```powershell
python -m scripts.export_analysis --input data/analysis --output data/exports --dry-run
```

## Pre-analysis

Run AI pre-analysis on an Excel data source column:

```powershell
python -m scripts.run_pre_analysis --input-file data/data_sources/excel_filename.xlsx --sheet-name "Sheet1" --column "column_name" --max-rows 5
```

Specify the header row if it is not the first row:

```powershell
python -m scripts.run_pre_analysis --input-file data/data_sources/excel_filename.xlsx --sheet-name "Sheet1" --column "column_name" --header-row 2 --max-rows 5
```

Overwrite only the report:

```powershell
python -m scripts.run_pre_analysis --input-file data/data_sources/excel_filename.xlsx --sheet-name "Sheet1" --column "column_name" --max-rows 5 --overwrite-report
```

Overwrite only the row outputs:

```powershell
python -m scripts.run_pre_analysis --input-file data/data_sources/2_1_1.xlsx --sheet-name "Sheet1" --column "col7_Please explain" --max-rows 5 --overwrite-rows
```

## Security

This repository includes automated security checks in GitHub:

- **Dependabot** (`.github/dependabot.yml`) creates weekly update PRs for Python dependencies and GitHub Actions.
- **Security Scan workflow** (`.github/workflows/security-scan.yml`) runs on push/PR/schedule and fails the pipeline when:
  - dependency vulnerabilities with **HIGH** or **CRITICAL** severity are found
  - code scanning finds **high-severity** Python security issues (Bandit)
