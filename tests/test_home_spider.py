"""Unit tests for the AdaptationStoriesHomeSpider using fake HTML pages."""

import asyncio

from scrapy.http import HtmlResponse, Request
from adaptation_stories.spiders.adaptation_stories_home import (
    AdaptationStoriesHomeSpider,
)


class FakePage:
    """A fake page object to simulate browser page interactions for testing."""

    def __init__(self, html_pages):
        self._html_pages = html_pages
        self._page_index = 0
        self.closed = False

    async def click(self, _selector):
        """Simulate clicking a selector by advancing to the next HTML page if available."""
        if self._page_index + 1 < len(self._html_pages):
            self._page_index += 1

    async def wait_for_selector(self, _selector):
        """Simulate waiting for a selector; does nothing in the fake page."""
        return None

    async def content(self):
        """Return the current HTML content of the fake page."""
        return self._html_pages[self._page_index]

    async def close(self):
        """Simulate closing the fake page."""
        self.closed = True


def test_home_spider_collects_links():
    """Test that AdaptationStoriesHomeSpider collects all unique story links and titles across multiple pages."""
    html_page_1 = """
    <div class="u-item listing-item result-item">
      <h3 class="listing-header"><a href="/story-1">Story One</a></h3>
    </div>
    <div class="u-item listing-item result-item">
      <h3 class="listing-header"><a href="/story-2">Story Two</a></h3>
    </div>
    """
    html_page_2 = """
    <div class="u-item listing-item result-item">
      <h3 class="listing-header"><a href="/story-2">Story Two</a></h3>
    </div>
    <div class="u-item listing-item result-item">
      <h3 class="listing-header"><a href="/story-3">Story Three</a></h3>
    </div>
    """
    fake_page = FakePage([html_page_1, html_page_2])

    spider = AdaptationStoriesHomeSpider(max_pages=2)
    request = Request(
        url="https://climate-adapt.eea.europa.eu/en/mission/solutions/mission-stories",
        meta={"playwright_page": fake_page},
    )
    response = HtmlResponse(
        url=request.url,
        request=request,
        body=b"",
        encoding="utf-8",
    )

    async def collect_items():
        items = []
        async for item in spider.parse(response):
            items.append(item)
        return items

    items = asyncio.run(collect_items())
    urls = sorted([item["url"] for item in items])
    titles = sorted([item["title"] for item in items])

    assert urls == [
        "https://climate-adapt.eea.europa.eu/story-1",
        "https://climate-adapt.eea.europa.eu/story-2",
        "https://climate-adapt.eea.europa.eu/story-3",
    ]
    assert titles == ["Story One", "Story Three", "Story Two"]
    assert fake_page.closed is True
