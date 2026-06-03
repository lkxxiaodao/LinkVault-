import re
from data.bookmark_repo import BookmarkRepo

URL_PATTERN = re.compile(
    r'https?://[^\s<>"\'{}|\\^`\[\]]+',
    re.IGNORECASE
)


class UrlExtractor:
    @staticmethod
    def extract(text):
        if not text:
            return []
        urls = URL_PATTERN.findall(text)
        seen = set()
        result = []
        for url in urls:
            url = url.rstrip('.,;:!?）)】」』')
            if url not in seen:
                seen.add(url)
                result.append(url)
        return result

    @staticmethod
    def check_and_prompt(text, callback):
        urls = UrlExtractor.extract(text)
        if not urls:
            return False
        new_urls = []
        for url in urls:
            existing = BookmarkRepo.find_by_url(url)
            if not existing:
                new_urls.append(url)
        if new_urls:
            callback(new_urls)
            return True
        return False