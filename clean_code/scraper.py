import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, List, Tuple, Optional

def scrape_clean_html_groups(url_dict: Dict[str, List[str]]) -> Dict[str, List[Tuple[str, str]]]:
    """
    Accepts a dictionary mapping sentiments to lists of URLs.
    Fetches each URL, extracts and cleans the text.
    
    Returns:
        Dict where key is sentiment, value is a list of tuples: (cleaned_text, url)
    """
    results = {}

    for label, urls in url_dict.items():
        group_data = []

        for url in urls:
            try:
                # 10s timeout to prevent hanging
                response = requests.get(url, timeout=10)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                # Remove script and style elements to reduce noise
                for script_or_style in soup(["script", "style"]):
                    script_or_style.extract()

                # Extract text with space separator to avoid merging words
                text = soup.get_text(separator=" ")

                # Normalize whitespace (remove newlines, tabs, double spaces)
                text = re.sub(r"\s+", " ", text).strip()

                # Append tuple: (cleaned_text, url)
                if text: # Only append if we actually got text back
                    group_data.append((text, url))
            
            except Exception as e:
                # Print error but keep the loop going
                print(f"Failed to scrape {url}: {e}")
                continue

        results[label] = group_data

    return results

def scrape_clean_html_list(urls: List[str]) -> Dict[str, Optional[str]]:
    """
    Accepts a list of URLs.
    Fetches each URL, extracts and cleans the text.
    
    Returns:
        Dict where key is the 'url', value is the 'cleaned_text'.
        If scraping fails, the value will be None (or you can choose to omit it).
    """
    results = {}

    for url in urls:
        try:
            # 10s timeout to prevent hanging
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script and style elements to reduce noise
            for script_or_style in soup(["script", "style"]):
                script_or_style.extract()

            # Extract text with space separator to avoid merging words
            text = soup.get_text(separator=" ")

            # Normalize whitespace (remove newlines, tabs, double spaces)
            text = re.sub(r"\s+", " ", text).strip()

            # Store result with url as the key
            if text:
                results[url] = text
            else:
                results[url] = "" # Handle empty pages

        except Exception as e:
            # Print error but keep the loop going
            print(f"Failed to scrape {url}: {e}")
            results[url] = None # Indicate failure in the dictionary

    return results