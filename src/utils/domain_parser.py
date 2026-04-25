import re
from urllib.parse import urlparse

def canonicalize_domain(url_or_domain: str) -> str:
    """
    1. remove protocols
    2. remove prefix 'www'
    3. remove paths, queries, and fragments
    4. lowercase
    5. strip trailing slashes and ports
    """

    if not url_or_domain:
        return ""
    
    if not re.match(r'^[a-zA-Z]+://', url_or_domain):
        processed_str = 'http://' + url_or_domain
    else:
        processed_str = url_or_domain
    
    try:
        parsed = urlparse(processed_str)
        domain = parsed.netloc or parsed.path
        domain = re.sub(r'^www\.',  '', domain.lower())
        # remove port
        domain = domain.split(':')[0]
        return domain.strip()
    except Exception:
        return url_or_domain.lower().strip()