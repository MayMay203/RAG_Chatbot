import re
from urllib.parse import urlparse

def contains_url(text: str) -> bool:
    # Regex đơn giản để phát hiện URL
    url_pattern = r'https?://\S+|www\.\S+'
    return re.search(url_pattern, text) is not None

def extract_all_urls(text: str) -> list[str]:
    matches = re.findall(r'https?://\S+', text)
    # Loại bỏ ký tự thừa ở cuối mỗi URL nếu có
    cleaned_urls = [url.rstrip('.,;:)[]{}\'"<>') for url in matches]
    return cleaned_urls

def classify_url_type(url: str, fileTypes) -> str:
    parsed = urlparse(url.lower())
    path = parsed.path

    if path.endswith((".pdf", ".docx", ".doc", ".pptx", ".xlsx")) or len(fileTypes) > 0:
        return "document"
    else:
        return "website"