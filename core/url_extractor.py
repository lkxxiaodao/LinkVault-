import re

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