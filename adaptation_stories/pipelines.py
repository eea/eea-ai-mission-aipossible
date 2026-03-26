"""
Pipeline module for processing scraped adaptation story items.
"""

# useful for handling different item types with a single interface


class AdaptationStoriesPipeline:
    """
    Pipeline for processing AdaptationStoryItem objects after scraping.
    You can add custom cleaning, validation, or storage logic here.
    """

    def process_item(self, item, spider):  # pylint: disable=unused-argument
        """
        Process a single item after it has been scraped.

        Args:
            item: The scraped item.
            spider: The spider that scraped the item.

        Returns:
            The processed item.
        """
        return item
