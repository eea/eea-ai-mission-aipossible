# Architecture

## Overview

This project has two main stages:

1. Scraping and storing source pages.
2. Running AI analysis on the stored pages.

## Data flow

1. `adaptation_stories_home` spider writes link lists to `data/links/`.
2. `adaptation_stories_pages` spider fetches each page and writes one JSON file per page to `data/pages/`.
3. `main.py` runs the analysis batch and writes one JSON file per page to `data/analysis/`.

## Key modules

- `adaptation_stories/spiders/`  
  Scrapy spiders for extracting links and page content.
- `analysis/utils.py`  
  Helpers for loading data, normalizing text, prompt construction, and output filenames.
- `analysis/analyzer.py`  
  Batch analysis runner with skip/overwrite/dry-run behavior.
- `analysis/clients/`  
  Provider clients and factory (Mock, OpenAI, and EEA).

## Providers

Clients are selected by `--provider` and created by `analysis/clients/factory.py`.
Provider settings come from:

- `.env.<provider>`: `MODEL`, `API_URL`
- `.env.<provider>.keys`: `API_KEY`

`mock` works without real API credentials and is intended for local/API testing.

For the Analysis API (`/v1/analysis/runs`), provider/model/key are configured at server level via `.env.api`
(`API_PROVIDER`, `API_MODEL`, `API_API_KEY`) or overridden by `scripts/run_analysis_api.py` arguments.
The run payload itself is minimal and currently accepts only `max_items` (optional).

API run input/output directories are configured at server level via `.env.api`
(`API_INPUT_DIR`, `API_OUTPUT_DIR`) or startup arguments.
Excel export location is configured with `API_EXPORT_DIR`.

## Storage

- `data/links/`: link lists (inputs for page scraping)
- `data/pages/`: scraped page JSONs (inputs for analysis)
- `data/analysis/`: AI analysis outputs

## Extending

To add a new provider:

1. Create `analysis/clients/<provider>_client.py` implementing `analyze`.
2. Register it in `analysis/clients/factory.py`.
3. Add `.env.<provider>.example` and `.env.<provider>.keys.example`.
