# Mission AIpossible

<img src="assets/images/Mission_AIpossible_logo.png" alt="Mission AIpossible logo" width="240">

[![Pipeline](https://ci.eionet.europa.eu/buildStatus/icon?job=EEA-AI%2Feea-ai-mission-aipossible%2Ftest2-cicd-skill&subject=test2-cicd-skill)](https://ci.eionet.europa.eu/view/Github/job/EEA-AI/job/eea-ai-mission-aipossible/job/test2-cicd-skill/display/redirect)
[![Quality Gate](https://sonarqube.eea.europa.eu/api/project_badges/quality_gate?project=eea-ai-mission-aipossible&branch=test2-cicd-skill)](https://sonarqube.eea.europa.eu/dashboard?id=eea-ai-mission-aipossible&branch=test2-cicd-skill)
[![Coverage](https://sonarqube.eea.europa.eu/api/project_badges/measure?project=eea-ai-mission-aipossible&branch=test2-cicd-skill&metric=coverage)](https://sonarqube.eea.europa.eu/dashboard?id=eea-ai-mission-aipossible&branch=test2-cicd-skill)
[![Duplications](https://sonarqube.eea.europa.eu/api/project_badges/measure?project=eea-ai-mission-aipossible&branch=test2-cicd-skill&metric=duplicated_lines_density)](https://sonarqube.eea.europa.eu/dashboard?id=eea-ai-mission-aipossible&branch=test2-cicd-skill)
[![Security Hotspots Reviewed](https://sonarqube.eea.europa.eu/api/project_badges/measure?project=eea-ai-mission-aipossible&branch=test2-cicd-skill&metric=security_hotspots_reviewed)](https://sonarqube.eea.europa.eu/dashboard?id=eea-ai-mission-aipossible&branch=test2-cicd-skill)
[![Maintainability](https://sonarqube.eea.europa.eu/api/project_badges/measure?project=eea-ai-mission-aipossible&branch=test2-cicd-skill&metric=sqale_rating)](https://sonarqube.eea.europa.eu/dashboard?id=eea-ai-mission-aipossible&branch=test2-cicd-skill)
[![Reliability](https://sonarqube.eea.europa.eu/api/project_badges/measure?project=eea-ai-mission-aipossible&branch=test2-cicd-skill&metric=reliability_rating)](https://sonarqube.eea.europa.eu/dashboard?id=eea-ai-mission-aipossible&branch=test2-cicd-skill)
[![Security](https://sonarqube.eea.europa.eu/api/project_badges/measure?project=eea-ai-mission-aipossible&branch=test2-cicd-skill&metric=security_rating)](https://sonarqube.eea.europa.eu/dashboard?id=eea-ai-mission-aipossible&branch=test2-cicd-skill)

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

The `scripts.run_analysis` CLI accepts `--use-case` and loads source and prompt paths from `config/analysis_use_cases.json`.
Each use case must define `source_path`, `system_prompt_path`, and `user_prompt_path`; the CLI raises an error if any of these files are missing or empty.
If `--provider` or `--output` is omitted, the CLI falls back to `PROVIDER` and `OUTPUT_DIR` from `.env`.
When `--use-case` is present, the CLI writes into a timestamped subfolder under `--output` by default, even if `--timestamped-output-dir` is not passed.
When you explicitly pass a path argument on the CLI (`--input`, `--output`, `--file`, `--source-path`, `--system-prompt-file`, or `--user-prompt-file`), it must be an absolute path.
`--user-prompt-file` overrides the use case `user_prompt_path` when `--use-case` is also specified.

Run the analysis stub over saved pages:

```powershell
python -m scripts.run_analysis --input C:/absolute/path/to/data/pages --output C:/absolute/path/to/data/analysis --max-items 5
```

Suppress progress output:

```powershell
python -m scripts.run_analysis --input C:/absolute/path/to/data/pages --output C:/absolute/path/to/data/analysis --max-items 5 --quiet
```

Overwrite existing analysis outputs:

```powershell
python -m scripts.run_analysis --input C:/absolute/path/to/data/pages --output C:/absolute/path/to/data/analysis --max-items 5 --overwrite
```

Create a timestamped output subfolder (for example `data/analysis/20260227_143015`):

```powershell
python -m scripts.run_analysis --input C:/absolute/path/to/data/pages --output C:/absolute/path/to/data/analysis --max-items 5 --timestamped-output-dir
```

If you combine `--timestamped-output-dir` with `--overwrite`, the script prints a warning because each run writes to a new folder, so overwrite has no practical effect.

Dry run (no files written):

```powershell
python -m scripts.run_analysis --input C:/absolute/path/to/data/pages --output C:/absolute/path/to/data/analysis --max-items 5 --dry-run
```

Select provider and model:

```powershell
python -m scripts.run_analysis --provider openai --model gpt-4o --input C:/absolute/path/to/data/pages --output C:/absolute/path/to/data/analysis
```

Use the mock provider (no API calls, no token usage):

```powershell
python -m scripts.run_analysis --provider mock --input C:/absolute/path/to/data/pages --output C:/absolute/path/to/data/analysis --max-items 5
```

Example for using inside the Virtual Machine of EEA

```powershell
python -m scripts.run_analysis --provider eea --input C:/absolute/path/to/data/pages --output C:/absolute/path/to/data/analysis --max-items 5
```

Run a configured use case from `config/analysis_use_cases.json`:

```powershell
python -m scripts.run_analysis --use-case adaptation_stories --output C:/absolute/path/to/data/analysis --max-items 5
```

For use-case runs, the CLI prints `run_id: <timestamp>` after a successful run. Use that value to export a specific run later.

Override a use-case source path from the CLI with `--input`:

```powershell
python -m scripts.run_analysis --use-case adaptation_stories --input C:/absolute/path/to/data/pages --output C:/absolute/path/to/data/analysis --max-items 5
```

Override a use-case source path from the CLI with `--source-path`:

```powershell
python -m scripts.run_analysis --use-case adaptation_stories --source-path C:/absolute/path/to/data/pages --output C:/absolute/path/to/data/analysis --max-items 5
```

Run the Excel-backed `question_2_1_1_column_7` use case through the main analysis CLI:

```powershell
python -m scripts.run_analysis --use-case question_2_1_1_column_7 --output C:/absolute/path/to/data/analysis --max-items 5
```

Override Excel-specific use-case settings from the CLI:

```powershell
python -m scripts.run_analysis --use-case question_2_1_1_column_7 --input C:/absolute/path/to/data/data_sources/2_1_1.xlsx --sheet-name "2.1.1" --column-name "col7_Please explain" --header-row 1 --output C:/absolute/path/to/data/analysis --max-items 5
```

Override the system prompt file for a run:

```powershell
python -m scripts.run_analysis --use-case adaptation_stories --system-prompt-file C:/absolute/path/to/prompts/system_prompt_custom.txt --output C:/absolute/path/to/data/analysis --max-items 5
```

Override the user prompt file for a run:

```powershell
python -m scripts.run_analysis --use-case adaptation_stories --user-prompt-file C:/absolute/path/to/prompts/user_prompt_custom.txt --output C:/absolute/path/to/data/analysis --max-items 5
```

Analyze a single saved page JSON file:

```powershell
python -m scripts.run_analysis --file C:/absolute/path/to/data/pages/example_page.json --output C:/absolute/path/to/data/analysis --provider mock
```

## Analysis API

Run the API server:

```powershell
uvicorn api.app:app --host 127.0.0.1 --port 8000 --reload
```

With plain `uvicorn`, set environment variables before startup:

```powershell
$env:OUTPUT_DIR="data/analysis"; uvicorn api.app:app --host 127.0.0.1 --port 8000 --reload
```

Run the API server with configurable default output/export directories:

```powershell
python -m scripts.run_analysis_api --host 127.0.0.1 --port 8000 --reload --output-dir C:/absolute/path/to/data/analysis --export-dir C:/absolute/path/to/data/exports
```

You can also keep defaults in a config file (`.env.api` by default):

```text
OUTPUT_DIR=C:/absolute/path/to/eea-ai-mission-aipossible/data/analysis
EXPORT_DIR=C:/absolute/path/to/eea-ai-mission-aipossible/data/exports
PROVIDER=mock
# API_MODEL=mock-model
# API_API_KEY=
```

When `--output-dir` or `--export-dir` is passed, it overrides config-file values for that server run.
When `--provider`, `--model`, or `--api-key` is passed, it overrides `PROVIDER`, `API_MODEL`, or `API_API_KEY`.
If you do not pass `--config-file`, the server looks for `.env.api` in the repo root and exits with an error if it is missing.
`/v1/analysis/runs` fails with `404` if the configured `OUTPUT_DIR` does not exist, or if the selected use case points to a missing source path.
`/v1/analysis/runs` returns `400` with a clear message if provider credentials are missing
(for example missing `.env.<provider>.keys` and no `API_API_KEY` override).

Health check:

```powershell
Invoke-RestMethod -Method GET http://127.0.0.1:8000/health
```

Run analysis (sync):

```powershell
Invoke-RestMethod -Method POST http://127.0.0.1:8000/v1/analysis/runs -ContentType "application/json" -Body '{"use_case":"adaptation_stories","max_items":3}'
```

Run analysis with inline prompt override (JSON):

```powershell
$body = @{
  use_case = "adaptation_stories"
  max_items = 3
  user_prompt = @"
Analyse the following climate adaptation report text.
I would like you to analyse the following 3 questions.
1. Simplified Title
2. Locality
3. Geographic extent
"@
} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Method POST http://127.0.0.1:8000/v1/analysis/runs -ContentType "application/json" -Body $body
```

Run analysis by uploading a prompt file (`.txt`):

```powershell
Invoke-RestMethod -Method POST http://127.0.0.1:8000/v1/analysis/runs/upload-prompt `
  -Form @{ use_case = "adaptation_stories"; prompt_file = Get-Item ".\analysis\prompts\user_prompt.txt"; max_items = "3" }
```

The response includes `run_id`, which is the folder name created under `data/analysis` for that run.

Provider/model/api key for runs are configured at API server level (`.env.api` or `scripts.run_analysis_api` args), not in the run request payload.
The JSON run request payload requires `use_case` and accepts `max_items` (optional) and `user_prompt` (optional).
The upload endpoint accepts multipart form fields `use_case` (required), `prompt_file` (`.txt`, UTF-8), and `max_items` (optional).

Use-case presets are defined in `config/analysis_use_cases.json`. Each entry must define:
- `source_type` (`pages` or `excel`)
- `source_path` — folder of page JSON files (pages) or an Excel file (excel)
- `system_prompt_path` — absolute path to the system prompt `.txt` file
- `user_prompt_path` — absolute path to the user prompt `.txt` file
- For `excel` use cases: `sheet_name`, `column_name`, and optionally `header_row` (default: `1`)

Available use cases:
- `adaptation_stories`: `source_type=pages`
- `question_2_1_1_column_7`: `source_type=excel`
- `question_4_8_column_7`: `source_type=excel`

The Analysis API also reads input sources from these use-case presets; there is no separate `API_INPUT_DIR` setting anymore.

When you use `python -m scripts.run_analysis --use-case ...`, the CLI loads these preset values and lets explicit CLI flags override them.

Runs are written into timestamped output subfolders (`output_dir/YYYYMMDD_HHMMSS`) by default.

Download all analysis files for a run as ZIP:

```powershell
Invoke-WebRequest -Method GET "http://127.0.0.1:8000/v1/analysis/runs/<run_id>/download" -OutFile "run_<run_id>.zip"
```

Download Excel export for one run folder:

```powershell
Invoke-WebRequest -Method GET "http://127.0.0.1:8000/v1/analysis/export/excel?run_id=<run_id>" -OutFile "analysis_<run_id>.xlsx"
```

The API writes the workbook to `EXPORT_DIR/<run_id>/analysis_<run_id>.xlsx` and then streams that same file in the response.

Provider-specific defaults still come from:

- `.env.openai` and `.env.openai.keys`
- `.env.eea` and `.env.eea.keys`

Use the EEA provider:

```powershell
python -m scripts.run_analysis --provider eea --model eea-model --input C:/absolute/path/to/data/pages --output C:/absolute/path/to/data/analysis
```

Use the EEA provider with a configured Excel use case:

```powershell
python -m scripts.run_analysis --provider eea --model eea-model --use-case question_2_1_1_column_7 --output C:/absolute/path/to/data/analysis --max-items 5
```

## Export

The export CLIs also fall back to `.env`: `OUTPUT_DIR` is used as the default analysis input folder and `EXPORT_DIR` as the default export destination.

Export analysis JSON files to Excel:

```powershell
python -m scripts.export_analysis_excel --input data/analysis --output data/exports/analysis.xlsx
```

Export one timestamped run folder to Excel (output is saved to `<EXPORT_DIR>/<run_id>/analysis.xlsx` automatically):

```powershell
python -m scripts.export_analysis_excel --run-id 20260227_143015
```

Disable default formatting options:

```powershell
python -m scripts.export_analysis_excel --input data/analysis --output data/exports/analysis_plain.xlsx --no-header-bold --no-auto-width --no-wrap-text --no-freeze-panes
```

Export `ai_result` to Markdown files:

```powershell
python -m scripts.export_analysis --input data/analysis --output data/exports
```

Export one timestamped run folder to Markdown (output is saved to `<EXPORT_DIR>/<run_id>/` automatically):

```powershell
python -m scripts.export_analysis --run-id 20260227_143015
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
