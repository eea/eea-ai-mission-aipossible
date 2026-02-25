"""Tests for the AdaptationStoriesPagesSpider page parser."""

import hashlib
import json
from pathlib import Path

from scrapy.http import HtmlResponse

from adaptation_stories.spiders.adaptation_stories_pages import (
    AdaptationStoriesPagesSpider,
)


def test_pages_parser_smoke(tmp_path):
    """Smoke test for AdaptationStoriesPagesSpider page parser."""
    fixture_path = Path(__file__).parent / "fixtures" / "story.html"
    html = fixture_path.read_text(encoding="utf-8")

    url = "https://climate-adapt.eea.europa.eu/en/mission/solutions/mission-stories/example"
    response = HtmlResponse(url=url, body=html.encode("utf-8"), encoding="utf-8")

    spider = AdaptationStoriesPagesSpider(
        input_file="data/links/links.json",
        output_dir=str(tmp_path),
    )
    spider.parse(response)

    filename = f"{hashlib.sha256(url.encode('utf-8')).hexdigest()}.json"
    output_file = tmp_path / filename
    assert output_file.exists()

    data = json.loads(output_file.read_text(encoding="utf-8"))
    assert data["title"] == "Example Story Title"
    assert data["subtitle"] == "Example subtitle line"
    assert data["published_date"] == "2024-03-25T11:51:00+00:00"
    assert data["modified_date"] == "2025-12-17T20:21:53+00:00"
    assert data["document_description"] == "Example summary text."
    assert data["sections"][0]["section_title"] == "Section One"
    assert "First section paragraph." in data["sections"][0]["content"]
    assert data["climate_impacts"] == ["Droughts", "Storms"]
    assert data["adaptation_sectors"] == ["Urban"]
    assert data["key_community_systems"] == [
        "Critical Infrastructure",
        "Health and Wellbeing",
    ]
    assert data["countries"] == ["France"]
    assert data["funding_programme"] == "National Funding"
    assert data["pdf_download_link"].endswith("/files/report.pdf")
    assert len(data["external_links"]) == 2
    assert data["images"][0]["alt"] == "Example image"
