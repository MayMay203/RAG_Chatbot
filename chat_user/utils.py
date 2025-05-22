import re
from urllib.parse import urlparse

def contains_url(text: str) -> bool:
    # Regex đơn giản để phát hiện URL
    url_pattern = r'https?://\S+|www\.\S+'
    return re.search(url_pattern, text) is not None

def extract_first_url(text: str) -> str:
    match = re.search(r'https?://\S+', text)
    if not match:
        return ""
    url = match.group(0)

    # Loại bỏ ký tự thừa ở cuối (nếu có)
    url = url.rstrip('.,;:)[]{}\'"<>')
    
    return url

def classify_url_type(url: str) -> str:
    parsed = urlparse(url.lower())
    path = parsed.path

    if path.endswith((".pdf", ".docx", ".doc", ".pptx", ".xlsx")):
        return "document"
    else:
        return "website"