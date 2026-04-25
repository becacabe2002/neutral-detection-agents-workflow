import requests
from bs4 import BeautifulSoup

class WebScraper:
    @staticmethod
    def scrape(url: str) -> str:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for script_or_style in soup(["script", "style", "nav", "footer", "header"]):
                script_or_style.decompose()
            
            text = soup.get_text(separator=' ', strip=True)
            return text
        except Exception as e:
            print(f"Error when scraping {url}: {e}")
            return ""