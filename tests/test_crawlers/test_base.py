from crawlers.base import BaseCrawler, CrawlResult


def test_crawl_result_has_required_fields():
    result = CrawlResult(
        source="test",
        title="Test Title",
        content="Test content",
        url="https://example.com",
        metadata={"author": "test"}
    )
    assert result.source == "test"
    assert result.title == "Test Title"
    assert result.content == "Test content"
    assert result.url == "https://example.com"
    assert result.metadata == {"author": "test"}
    assert result.crawled_at is not None


def test_base_crawler_is_abstract():
    import inspect
    from crawlers.base import BaseCrawler
    assert inspect.isabstract(BaseCrawler)
