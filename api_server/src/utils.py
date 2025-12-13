from urllib.parse import urlparse

def is_url(value: str) -> bool:
    try:
        result = urlparse(value)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False