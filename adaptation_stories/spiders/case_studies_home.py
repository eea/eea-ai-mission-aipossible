"""Spider for scraping case studies links from the data and downloads listing page."""

from typing import ClassVar

import scrapy
from scrapy.selector import Selector
from scrapy_playwright.page import PageMethod


class CaseStudiesHomeSpider(scrapy.Spider):
    """Spider for scraping case study links from the data and downloads listing page.

    This spider uses Scrapy with Playwright integration to handle dynamic content loading.
    It paginates through result pages, extracts item links and titles, and yields them as items.
    """

    name = "case_studies_home"
    allowed_domains: ClassVar[list[str]] = ["climate-adapt.eea.europa.eu"]
    start_urls = [  # noqa: RUF012 -- scrapy.Spider types this as an instance var, ClassVar conflicts with mypy
        "https://climate-adapt.eea.europa.eu/en/data-and-downloads?size=n_200_n&filters%5B0%5D%5Bfield%5D=language&filters%5B0%5D%5Btype%5D=any&filters%5B0%5D%5Bvalues%5D%5B0%5D=en&filters%5B1%5D%5Bfield%5D=objectProvides&filters%5B1%5D%5Bvalues%5D%5B0%5D=Case%20study&filters%5B1%5D%5Bvalues%5D%5B1%5D=Mission%20story&filters%5B1%5D%5Btype%5D=any&filters%5B2%5D%5Bfield%5D=issued.date&filters%5B2%5D%5Bvalues%5D%5B0%5D=Last%205%20years&filters%5B2%5D%5Btype%5D=any&sort-field=issued.date&sort-direction=desc"
    ]

    def __init__(self, max_pages=10, use_playwright="false", **kwargs):
        super().__init__(**kwargs)
        try:
            max_pages_int = int(max_pages)
        except (TypeError, ValueError):
            max_pages_int = 10
        self.max_pages = max(1, max_pages_int)
        self.use_playwright = str(use_playwright).lower() in {"1", "true", "yes", "y"}

    async def start(self):
        """Starts the crawling process by generating Scrapy requests for each URL in `start_urls`.
        Each request is configured to use Playwright for rendering JavaScript content and waits
        for result items before proceeding.
        """
        for url in self.start_urls:
            meta = {}
            if self.use_playwright:
                meta = {
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle"),
                    ],
                }
            yield scrapy.Request(url=url, callback=self.parse, meta=meta)

    async def parse(self, response):
        """Parses each listing page, extracts item links and titles, and paginates through results.

        Args:
            response (scrapy.http.Response): The response object containing the page content.

        Yields:
            dict: A dictionary with 'url' and 'title' keys for each item found.

        """
        page = response.meta.get("playwright_page")
        seen = set()
        try:
            for page_num in range(1, self.max_pages + 1):
                if page_num > 1 and page is not None:
                    await page.click(f"button.pagination-item:has-text('{page_num}')")
                    try:
                        await page.wait_for_load_state("networkidle", timeout=30000)
                    except Exception as exc:
                        self.logger.warning(
                            "Timed out waiting for page %d to settle: %s",
                            page_num,
                            exc,
                        )

                if page is not None:
                    html = await page.content()
                else:
                    html = response.text
                selector = Selector(text=html)
                cards = selector.css("div.u-item.listing-item.result-item")
                if not cards:
                    self.logger.warning("No result-item links found on page %d.", page_num)
                    continue

                for card in cards:
                    link = card.css("h3.listing-header a")
                    href = link.attrib.get("href") if link else None
                    if not href:
                        continue
                    url = response.urljoin(href)
                    if url in seen:
                        continue
                    seen.add(url)
                    title = link.css("::text").get()
                    yield {"url": url, "title": title.strip() if title else None}

                self.logger.info(
                    "Collected %d unique links after page %d.",
                    len(seen),
                    page_num,
                )
        finally:
            if page is not None:
                await page.close()
