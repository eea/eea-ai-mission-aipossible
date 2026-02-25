"""Defines the AdaptationStoryItem for the adaptation stories scraper."""

import scrapy


class AdaptationStoryItem(scrapy.Item):
    """Item representing an adaptation story scraped from the website."""

    url = scrapy.Field()
    title = scrapy.Field()
    subtitle = scrapy.Field()
    published_date = scrapy.Field()
    modified_date = scrapy.Field()
    document_description = scrapy.Field()
    sections = scrapy.Field()
    climate_impacts = scrapy.Field()
    adaptation_sectors = scrapy.Field()
    key_community_systems = scrapy.Field()
    countries = scrapy.Field()
    funding_programme = scrapy.Field()
    pdf_download_link = scrapy.Field()
    external_links = scrapy.Field()
    images = scrapy.Field()
    scraped_at = scrapy.Field()
