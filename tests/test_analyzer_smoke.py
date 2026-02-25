import json
from pathlib import Path

from analysis.analyzer import run_batch
from analysis.utils import output_path_for_url


def test_analyzer_smoke(tmp_path):
    """Smoke test for the analysis pipeline."""
    input_dir = tmp_path / "pages"
    output_dir = tmp_path / "analysis"
    input_dir.mkdir()

    page = {
        "url": "https://example.com/story",
        "title": "Example Story",
        "document_description": "Short description here.",
        "climate_impacts": ["Droughts", "Storms"],
        "sections": [],
    }
    page_path = input_dir / "page.json"
    page_path.write_text(json.dumps(page), encoding="utf-8")

    run_batch(input_dir, output_dir, client=None, max_items=1)

    output_path = output_path_for_url(output_dir, page["url"])
    assert output_path.exists()
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["url"] == page["url"]
    assert data["summary"] == page["document_description"]
