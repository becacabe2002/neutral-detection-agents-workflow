import json
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional

class WebScraper:
    @staticmethod
    def scrape(url: str) -> Dict[str, Optional[str]]:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            published_at = None

            # 1. Try Schema.org (JSON-LD)
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string)
                    # Handle both single objects and lists
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if isinstance(item, dict):
                            # Check common article/webpage types
                            if item.get("@type") in ["Article", "NewsArticle", "WebPage", "Report"]:
                                published_at = item.get("datePublished") or item.get("dateModified")
                                if published_at:
                                    break
                    if published_at:
                        break
                except (json.JSONDecodeError, TypeError):
                    continue

            # 2. Fallback to Meta Tags
            if not published_at:
                meta_tags = [
                    ("property", "article:published_time"),
                    ("property", "article:modified_time"),
                    ("name", "date"),
                    ("name", "pubdate"),
                    ("name", "last-modified"),
                    ("itemprop", "datePublished")
                ]
                for attr, name in meta_tags:
                    tag = soup.find("meta", {attr: name})
                    if tag and tag.get("content"):
                        published_at = tag["content"]
                        break

            # Clean the HTML
            for script_or_style in soup(["script", "style", "nav", "footer", "header"]):
                script_or_style.decompose()
            
            text = soup.get_text(separator=' ', strip=True)
            return {
                "text": text,
                "published_at": published_at
            }
        except Exception as e:
            print(f"Error when scraping {url}: {e}")
            return {
                "text": "",
                "published_at": None
            }