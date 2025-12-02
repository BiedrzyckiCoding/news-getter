import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, List

def scrape_clean_html_groups(url_dict: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Accepts a dictionary mapping categories (e.g., 'positive', 'negative')
    to lists of URLs. Fetches each URL, parses HTML with BeautifulSoup,
    extracts cleaned text, and returns a matching dictionary.
    """
    results = {}

    for label, urls in url_dict.items():
        cleaned_articles = []

        for url in urls:
            response = requests.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract only visible text; adjust as needed
            text = soup.get_text(separator=" ")

            # Normalize whitespace
            text = re.sub(r"\s+", " ", text).strip()

            cleaned_articles.append(text)

        results[label] = cleaned_articles

    return results
