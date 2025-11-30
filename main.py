import pandas as pd
import requests
from googleapiclient.discovery import build
from datetime import datetime
from dotenv import load_dotenv
import bleach
import os
from bs4 import BeautifulSoup
import time
from requests.exceptions import RequestException

# Load environment variables from .env file
load_dotenv()

# Setup Google Custom Search using environment variables
API_KEY = os.getenv('API_KEY')  # Get the API key from the environment variable
CX = os.getenv('CX')  # Get the CSE ID from the environment variable

# Initialize Google Custom Search API client
service = build("customsearch", "v1", developerKey=API_KEY)

# List of search phrases (you can modify this list)
search_phrases = ['bitcoin news', 'crypto news', 'apple news', 'financial news', 'geopolitics']

# Function to fetch search results using Google Custom Search API
def fetch_top5_results(query):
    # Perform search query using the Google Custom Search API
    res = service.cse().list(q=query, cx=CX).execute()
    
    results = []
    for idx, item in enumerate(res['items'][:5]):  # Top 5 results
        # Extract the necessary information
        title = item['title']
        link = item['link']
        snippet = item.get('snippet', 'No snippet available')
        results.append({
            'position': idx + 1,
            'title': title,
            'link': link,
            'snippet': snippet
        })
    
    return results

# Function to fetch raw HTML of a webpage
def fetch_raw_text(url, retries=3):
    try:
        response = requests.get(url, timeout=5)
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        # Extract only the text from the HTML
        clean_text = soup.get_text(separator=" ", strip=True)
        # Remove all newlines and replace with spaces, then normalize whitespace
        clean_text = ' '.join(clean_text.split())
        return clean_text
    except RequestException as e:
        if retries > 0:
            print(f"Error fetching page {url}: {e}. Retrying...")
            time.sleep(2)  # Wait before retrying
            return fetch_raw_text(url, retries - 1)
        else:
            return f"Error fetching page: {str(e)}"

# Prepare a list to store results
data = []

# Loop over each search phrase and collect data
for phrase in search_phrases:
    search_results = fetch_top5_results(phrase)
    
    for result in search_results:
        # Fetch raw HTML for the link
        raw_html = fetch_raw_text(result['link'])
        
        # Add the current timestamp, phrase, and raw HTML to the data
        data.append({
            'time_signature': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'phrase': phrase,
            'position': result['position'],
            'raw_html': raw_html
        })

# Create a pandas DataFrame
df = pd.DataFrame(data)

# Save the DataFrame to a CSV file
df.to_csv('data/top5_news_results.csv', index=False)

print("Scraping complete and saved to 'top5_news_results.csv'.")