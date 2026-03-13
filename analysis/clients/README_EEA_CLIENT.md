# EEA Client (eea_client.py)

This README describes the EEA client for the mission_aipossible project, implemented in `eea_client.py`.

## Location

- `analysis/clients/eea_client.py`

## Purpose

The EEA client provides an interface to the European Environment Agency (EEA) AI service for analyzing saved web pages.

## Usage

The EEA client is used via the main script and the client factory. Example:

```bash
python main.py --provider eea --input data/pages --output data/analysis
```

## Configuration

- `.env.eea` for general settings (e.g., `MODEL`, `API_URL`)
- `.env.eea.keys` for sensitive keys (e.g., `API_KEY`)

## Example Environment Files

`.env.eea`:
```
MODEL=eea-default-model
API_URL=https://api.eea.europa.eu/ai
```

`.env.eea.keys`:
```
API_KEY=your-eea-api-key
```

## Features

- Connects to the EEA AI API
- Batch analysis of web pages
- Configurable model, API URL, and prompts

## Related Files

- [main.py](../../main.py)
- [factory.py](factory.py)
- [analyzer.py](../analyzer.py)
