from tests.core.base import BaseCoreTest
from core.url_extractor import UrlExtractor
from data.bookmark_repo import BookmarkRepo


class TestUrlExtractor(BaseCoreTest):
    def test_extract_single_url(self):
        text = 'Check out https://example.com today'
        urls = UrlExtractor.extract(text)
        self.assertEqual(urls, ['https://example.com'])

    def test_extract_multiple_urls(self):
        text = 'Visit https://a.com and https://b.com also'
        urls = UrlExtractor.extract(text)
        self.assertEqual(len(urls), 2)
        self.assertIn('https://a.com', urls)
        self.assertIn('https://b.com', urls)

    def test_extract_deduplicates(self):
        text = 'Here https://example.com and again https://example.com'
        urls = UrlExtractor.extract(text)
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0], 'https://example.com')

    def test_extract_empty_text(self):
        self.assertEqual(UrlExtractor.extract(''), [])
        self.assertEqual(UrlExtractor.extract(None), [])

    def test_extract_no_url(self):
        text = 'Just some plain text without any link'
        urls = UrlExtractor.extract(text)
        self.assertEqual(urls, [])

    def test_extract_strips_trailing_punctuation(self):
        text = 'Check https://example.com. Then see https://other.com, also'
        urls = UrlExtractor.extract(text)
        self.assertNotIn('https://example.com.', urls)
        self.assertIn('https://example.com', urls)
        self.assertNotIn('https://other.com,', urls)
        self.assertIn('https://other.com', urls)

    def test_extract_http_url(self):
        text = 'Use http://oldsite.com for reference'
        urls = UrlExtractor.extract(text)
        self.assertEqual(urls, ['http://oldsite.com'])

    def test_check_and_prompt_new_urls(self):
        BookmarkRepo.create('Existing', 'https://exists.com')
        captured = []
        def callback(urls):
            captured.extend(urls)
        text = 'See https://exists.com and https://new.com'
        result = UrlExtractor.check_and_prompt(text, callback)
        self.assertTrue(result)
        self.assertEqual(captured, ['https://new.com'])

    def test_check_and_prompt_all_existing(self):
        BookmarkRepo.create('Existing', 'https://exists.com')
        captured = []
        def callback(urls):
            captured.extend(urls)
        text = 'Check https://exists.com again'
        result = UrlExtractor.check_and_prompt(text, callback)
        self.assertFalse(result)
        self.assertEqual(captured, [])

    def test_check_and_prompt_no_urls(self):
        captured = []
        def callback(urls):
            captured.extend(urls)
        text = 'No links here'
        result = UrlExtractor.check_and_prompt(text, callback)
        self.assertFalse(result)
        self.assertEqual(captured, [])