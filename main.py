import pandas as pd
import requests
from googleapiclient.discovery import build
from datetime import datetime
from dotenv import load_dotenv
import os
from bs4 import BeautifulSoup
import time
from requests.exceptions import RequestException
from transformers import pipeline
import warnings

warnings.filterwarnings('ignore')


class ConfigManager:
    """Handles environment variables and configuration"""
    
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('API_KEY')
        self.cx = os.getenv('CX')
        self.search_phrases = [
            'bitcoin news', 
            'crypto news', 
            'apple news', 
            'financial news', 
            'geopolitics'
        ]
        
    def validate(self):
        """Validate that required config exists"""
        if not self.api_key or not self.cx:
            raise ValueError("API_KEY and CX must be set in .env file")


class TextSummarizer:
    """Handles text summarization using transformers"""
    
    def __init__(self, model_name="facebook/bart-large-cnn"):
        print(f"Loading summarization model: {model_name}...")
        self.summarizer = pipeline("summarization", model=model_name)
        print("Model loaded successfully!")
    
    def summarize(self, text, max_words=20, min_words=10):
        """
        Summarize text to a maximum word count
        
        Args:
            text: Input text to summarize
            max_words: Maximum number of words in summary
            min_words: Minimum number of words in summary
        
        Returns:
            Summarized text string
        """
        try:
            # Transformers work better with token counts
            # Approximate: 1 word ≈ 1.3 tokens
            max_length = int(max_words * 1.3)
            min_length = int(min_words * 1.3)
            
            # Truncate input if too long (model has max input length)
            if len(text.split()) > 1000:
                text = ' '.join(text.split()[:1000])
            
            # Skip if text is already short enough
            if len(text.split()) <= max_words:
                return text
            
            summary = self.summarizer(
                text, 
                max_length=max_length, 
                min_length=min_length, 
                do_sample=False,
                truncation=True
            )
            
            return summary[0]['summary_text']
        
        except Exception as e:
            print(f"Error summarizing text: {e}")
            # Fallback: return first N words
            return ' '.join(text.split()[:max_words])


class WebScraper:
    """Handles web scraping and text extraction"""
    
    @staticmethod
    def fetch_clean_text(url, retries=3):
        """
        Fetch webpage and extract clean text
        
        Args:
            url: URL to fetch
            retries: Number of retry attempts
        
        Returns:
            Clean text with no newlines, normalized whitespace
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract text
            clean_text = soup.get_text(separator=" ", strip=True)
            
            # Remove newlines and normalize whitespace
            clean_text = ' '.join(clean_text.split())
            
            return clean_text
        
        except RequestException as e:
            if retries > 0:
                print(f"Error fetching {url}: {e}. Retrying... ({retries} left)")
                time.sleep(2)
                return WebScraper.fetch_clean_text(url, retries - 1)
            else:
                print(f"Failed to fetch {url} after all retries")
                return f"Error: {str(e)}"


class GoogleSearchClient:
    """Handles Google Custom Search API interactions"""
    
    def __init__(self, api_key, cx):
        self.service = build("customsearch", "v1", developerKey=api_key)
        self.cx = cx
    
    def search(self, query, num_results=5):
        """
        Search Google and return top results
        
        Args:
            query: Search query string
            num_results: Number of results to return
        
        Returns:
            List of result dictionaries
        """
        try:
            res = self.service.cse().list(q=query, cx=self.cx).execute()
            
            results = []
            for idx, item in enumerate(res.get('items', [])[:num_results]):
                results.append({
                    'position': idx + 1,
                    'title': item.get('title', 'No title'),
                    'link': item.get('link', ''),
                    'snippet': item.get('snippet', 'No snippet available')
                })
            
            return results
        
        except Exception as e:
            print(f"Error searching for '{query}': {e}")
            return []


class NewsScraperPipeline:
    """Main pipeline that orchestrates the scraping and summarization"""
    
    def __init__(self, config):
        self.config = config
        self.search_client = GoogleSearchClient(config.api_key, config.cx)
        self.scraper = WebScraper()
        self.summarizer = TextSummarizer()
    
    def run(self, output_file='data/top5_news_results.csv'):
        """
        Execute the full scraping and summarization pipeline
        
        Args:
            output_file: Path to save the CSV output
        """
        print("Starting news scraping pipeline...\n")
        data = []
        
        for phrase in self.config.search_phrases:
            print(f"Searching for: '{phrase}'")
            search_results = self.search_client.search(phrase, num_results=5)
            
            for result in search_results:
                print(f"  [{result['position']}] {result['title']}")
                
                # Fetch raw text
                raw_text = self.scraper.fetch_clean_text(result['link'])
                
                # Summarize text
                if raw_text and not raw_text.startswith("Error"):
                    summary = self.summarizer.summarize(raw_text, max_words=20)
                else:
                    summary = "Failed to fetch content"
                
                # Store data
                data.append({
                    'time_signature': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'phrase': phrase,
                    'position': result['position'],
                    'title': result['title'],
                    'link': result['link'],
                    'snippet': result['snippet'],
                    'raw_text': raw_text,
                    'summary': summary
                })
                
                print(f"      Summary: {summary}\n")
        
        # Create DataFrame and save
        df = pd.DataFrame(data)
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        df.to_csv(output_file, index=False)
        print(f"\n✅ Scraping complete! Saved to '{output_file}'")
        print(f"Total articles processed: {len(data)}")
        
        return df


def main():
    """Main entry point"""
    # Initialize configuration
    config = ConfigManager()
    config.validate()
    
    # Run pipeline
    pipeline = NewsScraperPipeline(config)
    df = pipeline.run()
    
    # Display sample results
    print("\n--- Sample Results ---")
    print(df[['phrase', 'title', 'summary']].head())


if __name__ == "__main__":
    main()