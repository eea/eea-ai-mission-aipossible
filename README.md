# Mission AIpossible

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

Dry run (no files written):

```powershell
python -m scripts.run_analysis --input data/pages --output data/analysis --max-items 5 --dry-run
```

Select provider and model:

```powershell
python -m scripts.run_analysis --provider openai --model gpt-4o --input data/pages --output data/analysis
```

Example for using inside the Virtual Machine of EEA

```powershell
python -m scripts.run_analysis --provider eea --input data/pages --output data/analysis --max-items 5
```

Defaults for `--model` and `--api-key` can be read from provider-specific files:

- `.env.openai` and `.env.openai.keys`
- `.env.eea` and `.env.eea.keys`

You can also set `API_URL` in the provider `.env` file or pass `--api-url`.

Use the EEA provider:

```powershell
python -m scripts.run_analysis --provider eea --model eea-model --input data/pages --output data/analysis
```

## Export

Export analysis JSON files to Excel:

```powershell
python -m scripts.export_analysis_excel --input data/analysis --output data/exports/analysis.xlsx
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
