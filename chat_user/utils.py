import re
def contains_url(text: str) -> bool:
    # Regex đơn giản để phát hiện URL
    url_pattern = r'https?://\S+|www\.\S+'
    return re.search(url_pattern, text) is not None