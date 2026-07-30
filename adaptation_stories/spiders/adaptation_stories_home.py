"""Spider for scraping adaptation stories links from the Mission Stories home page using Scrapy and Playwright."""

import scrapy
from scrapy.selector import Selector
from scrapy_playwright.page import PageMethod


class AdaptationStoriesHomeSpider(scrapy.Spider):
    """Spider for scraping adaptation stories from the Mission Stories page.

    This spider uses Scrapy with Playwright integration to handle dynamic content loading.
    It navigates through paginated results, extracts story links and titles, and yields them as items.

    Attributes:
        name (str): Name of the spider.
        allowed_domains (list): List of allowed domains for crawling.
        start_urls (list): Initial URLs to start scraping from.
        max_pages (int): Maximum number of pages to scrape, configurable via spider arguments.

    Methods:
        __init__(max_pages=10, **kwargs): Initializes the spider with a configurable number of pages.
        start(): Starts the crawling process, yielding requests with Playwright enabled.
        parse(response): Parses each page, extracts story links and titles, and handles pagination.

    """

    name = "adaptation_stories_home"
    allowed_domains = ["climate-adapt.eea.europa.eu"]  # noqa: RUF012
    start_urls = ["https://climate-adapt.eea.europa.eu/en/mission/solutions/mission-stories"]  # noqa: RUF012

    def __init__(self, max_pages=10, **kwargs):
        super().__init__(**kwargs)
        try:
            max_pages_int = int(max_pages)
        except (TypeError, ValueError):
            max_pages_int = 10
        self.max_pages = max(1, max_pages_int)

    async def start(self):
        """Starts the crawling process by generating Scrapy requests for each URL in `start_urls`.
        Each request is configured to use Playwright for rendering JavaScript content and waits for a specific
        selector before proceeding.
        """
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod(
                            "wait_for_selector",
                            "div.u-item.listing-item.result-item",
                        )
                    ],
                },
            )

    async def parse(self, response):
        """Parse a mission stories page, extract story links and titles, paginate through results, and yield items.

        Args:
            response (scrapy.http.Response): The response object containing the page content.

        Yields:
            dict: A dictionary with 'url' and 'title' keys for each story found.

        """
        page = response.meta["playwright_page"]
        seen = set()
        try:
            for page_num in range(1, self.max_pages + 1):
                if page_num > 1:
                    await page.click(f"button.pagination-item:has-text('{page_num}')")
                    await page.wait_for_selector("div.u-item.listing-item.result-item")

                html = await page.content()
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
            await page.close()
