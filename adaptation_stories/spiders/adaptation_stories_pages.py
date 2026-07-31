"""Spider for scraping adaptation stories pages from the Mission website."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar

import scrapy

from adaptation_stories.items import AdaptationStoryItem
from env_settings import get_bool_setting


class AdaptationStoriesPagesSpider(scrapy.Spider):
    """Spider for scraping adaptation stories pages from the Mission website.

    This spider reads a list of URLs from a JSON file, visits each page, and extracts structured information
    such as titles, metadata, section content, keywords, links, and images. The extracted data is saved as
    JSON files, one per page.

    Attributes:
        name (str): Name of the spider.
        allowed_domains (list): List of allowed domains for crawling.
        input_path (Path): Path to the input JSON file containing URLs.
        output_path (Path): Directory where scraped data will be saved.
        max_links (int or None): Maximum number of links to process.

    Args:
        input_file (str): Path to the input JSON file with URLs (relative to project root).
        output_dir (str): Directory to save the output JSON files.
        max_links (int or None): Maximum number of links to process. If None, all links are processed.
        **kwargs: Additional keyword arguments passed to the Scrapy Spider.

    Methods:
        start: Loads URLs and yields Scrapy requests for each.
        parse: Extracts data from each response and saves it as a JSON file.
        _load_urls: Loads and parses URLs from the input file.
        _clean_text: Cleans and normalizes text values.
        _parse_max_links: Parses and validates the max_links parameter.

    """

    name = "adaptation_stories_pages"
    allowed_domains: ClassVar[list[str]] = ["climate-adapt.eea.europa.eu"]

    def __init__(
        self,
        input_file="data/links/links.json",
        output_dir="data/pages",
        max_links=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        base_dir = Path(__file__).resolve().parents[2]
        self.input_path = (base_dir / input_file).resolve()
        self.output_path = (base_dir / output_dir).resolve()
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.max_links = self._parse_max_links(max_links)

    async def start(self):
        """Starts the crawling process by loading URLs and yielding Scrapy requests for each URL.

        Yields:
            scrapy.Request: A Scrapy request object for each URL to be parsed.

        Limits:
            If self.max_links is set, only the first `max_links` URLs are processed.

        """
        urls = self._load_urls()
        if self.max_links:
            urls = urls[: self.max_links]
        for url in urls:
            output_file = self._output_file_for_url(url)
            if output_file.exists() and output_file.stat().st_size > 0:
                self.logger.info("Skipping cached page (%s): %s", output_file.name, url)
                continue
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        """Parse the response from an adaptation story page and extract structured data.

        This method extracts the following information from the response:
            - URL and a hashed filename for output.
            - Main title and subtitle of the page.
            - Metadata including published and modified dates.
            - Document description (summary/introduction).
            - All section headings (h2) and their associated content.
            - Keywords such as climate impacts, adaptation sectors, key community systems, and countries.
            - Funding programme information.
            - PDF download link and other external links.
            - Images with their source and alt text.
            - Timestamp of when the data was scraped.

        The extracted data is saved as a JSON file in the specified output path.

        Args:
            response (scrapy.http.Response): The HTTP response object to parse.

        Returns:
            None

        """
        url = response.url
        output_file = self._output_file_for_url(url)
        if output_file.exists() and output_file.stat().st_size > 0:
            self.logger.info("Already saved, skipping write (%s): %s", output_file.name, url)
            return

        # Extract the main title
        title = response.css("h1::text").get()
        subtitle = response.css("p.subtitle::text").get()

        # Extract metadata
        published_date = response.xpath('//p[@class="metadata"]//time[contains(., "Published")]/@datetime').get()
        modified_date = response.xpath('//p[@class="metadata"]//time[contains(., "Modified")]/@datetime').get()
        if not published_date:
            published_date = response.xpath('//p[@class="metadata"]//time[contains(., "Published")]/text()').get()
        if not modified_date:
            modified_date = response.xpath('//p[@class="metadata"]//time[contains(., "Modified")]/text()').get()

        # Extract the summary/introduction (document description)
        document_description = response.css("div.documentDescription.eea.callout p::text").get()

        # Extract all section headings and content
        sections = []

        # Method 1: Extract h2 sections with their content
        for section in response.css(
            "div.eight.wide.computer.twelve.wide.mobile.eight.wide.tablet.column.column-blocks-wrapper h2"
        ):
            section_title = section.css("::text").get()
            # Get all text until the next h2
            section_content = []
            for elem in section.xpath("./following-sibling::*"):
                if elem.xpath("name()").get() == "h2":
                    break
                text = elem.xpath(".//text()").getall()
                section_content.extend([t.strip() for t in text if t.strip()])

            sections.append(
                {
                    "section_title": section_title.strip() if section_title else None,
                    "content": " ".join(section_content),
                }
            )

        # Extract keywords
        climate_impacts = response.css("span.climate_impacts span::text").getall()

        adaptation_sectors = response.css("span.sectors span::text").getall()

        key_community_systems = response.css("span.key_system span::text").getall()

        countries = response.css("span.country span::text").getall()

        funding_programme = response.css("span.funding_programme::text").get()

        # Extract links
        pdf_link = response.css('main a[href*="pdf"]::attr(href)').get()
        external_links = response.css(
            "div.eight.wide.computer.twelve.wide.mobile.eight.wide.tablet.column.column-blocks-wrapper "
            'a[href^="http"]::attr(href)'
        ).getall()

        # Extract image information
        images = []
        for img in response.css(
            "div.eight.wide.computer.twelve.wide.mobile.eight.wide.tablet.column.column-blocks-wrapper img"
        ):
            images.append(
                {
                    "src": img.css("::attr(src)").get(),
                    "alt": img.css("::attr(alt)").get(),
                }
            )

        data = AdaptationStoryItem(
            url=response.url,
            title=self._normalize_text(title),
            subtitle=self._normalize_text(subtitle),
            published_date=self._normalize_text(published_date),
            modified_date=self._normalize_text(modified_date),
            document_description=self._normalize_text(document_description),
            sections=sections,
            climate_impacts=self._normalize_list(climate_impacts),
            adaptation_sectors=self._normalize_list(adaptation_sectors),
            key_community_systems=self._normalize_list(key_community_systems),
            countries=self._normalize_list(countries),
            funding_programme=self._normalize_text(funding_programme),
            pdf_download_link=response.urljoin(pdf_link) if pdf_link else None,
            external_links=self._normalize_list(external_links),
            images=images,
            scraped_at=datetime.now(timezone.utc).isoformat(),
        )

        with output_file.open("w", encoding="utf-8") as handle:
            ensure_ascii = get_bool_setting("JSON_ENSURE_ASCII", default=False)
            json.dump(dict(data), handle, ensure_ascii=ensure_ascii, indent=2)

        self.logger.info("Saved %s", output_file.name)

    def _load_urls(self):
        if not self.input_path.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_path}")

        raw = json.loads(self.input_path.read_text(encoding="utf-8"))
        urls = []
        for item in raw:
            if isinstance(item, dict) and "url" in item:
                urls.append(item["url"])
            elif isinstance(item, str):
                urls.append(item)
        return urls

    def _output_file_for_url(self, url):
        filename = f"{hashlib.sha256(url.encode('utf-8')).hexdigest()}.json"
        return self.output_path / filename

    @staticmethod
    def _clean_text(value):
        if value is None:
            return None
        if isinstance(value, list):
            value = " ".join(value)
        return " ".join(value.split())

    def _normalize_text(self, value):
        return self._clean_text(value)

    def _normalize_list(self, values):
        if not values:
            return []
        return [self._clean_text(value) for value in values if self._clean_text(value)]

    @staticmethod
    def _parse_max_links(value):
        if value is None:
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None
