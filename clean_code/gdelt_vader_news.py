import requests
import pandas as pd
import os
from datetime import datetime, timezone
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import pymongo
from typing import Dict, List, Tuple

from summary_sender import process_and_send_summary
from scraper import scrape_clean_html_groups


class VaderSetup:
    """Handles VADER sentiment analyzer setup and initialization."""
    
    @staticmethod
    def initialize():
        """Download VADER lexicon if needed and return analyzer."""
        try:
            nltk.data.find('sentiment/vader_lexicon.zip')
        except LookupError:
            print("Downloading VADER lexicon...")
            nltk.download('vader_lexicon')
        
        return SentimentIntensityAnalyzer()


class GDELTConfig:
    """Configuration for GDELT API requests."""
    
    def __init__(self, keywords: str = None, domains: str = None, themes: str = None):
        # Expanded keywords to cover Crypto + Macro/Geopolitics
        # Added: Regulation, Sanctions, SEC, Fed, CBDC, Legislation, Tariffs, Conflict
        self.keywords = keywords or (
            "(bitcoin OR crypto OR solana OR ethereum OR NFT OR DeFi OR "
            "regulation OR sanctions OR SEC OR 'federal reserve' OR "
            "legislation OR tariffs OR CBDC OR geopolitics OR conflict)"
        )
        
        self.domains = domains or (
            "(domain:reuters.com OR domain:bloomberg.com OR domain:wsj.com OR "
            "domain:cnbc.com OR domain:coindesk.com OR domain:politico.com OR "
            "domain:ft.com)"
        )
        
        # Added GOV_REGULATION and ECON_CENTRALBANK to themes
        self.themes = themes or (
            "(theme:FINANCE OR theme:ECON_STOCKMARKET OR "
            "theme:SEC_FINANCIAL_ASSETS OR theme:GOV_REGULATION OR "
            "theme:ECON_CENTRALBANK)"
        )
        
        self.url = "https://api.gdeltproject.org/api/v2/doc/doc"
        self.max_records = 100
    
    def get_query(self) -> str:
        """Generate full query string."""
        return f"{self.keywords} {self.domains} {self.themes}"
    
    def get_params(self) -> Dict:
        """Get API request parameters."""
        return {
            "query": self.get_query(),
            "mode": "ArtList",
            "format": "json",
            "maxrecords": self.max_records,
            "sort": "DateDesc"
        }


class GDELTFetcher:
    """Handles fetching articles from GDELT API."""
    
    def __init__(self, config: GDELTConfig):
        self.config = config
    
    def fetch_articles(self) -> List[Dict]:
        """Fetch articles from GDELT API."""
        print("Fetching headlines...")
        try:
            response = requests.get(self.config.url, params=self.config.get_params())
            response.raise_for_status()
            data = response.json()
            articles = data.get("articles", [])
            
            if not articles:
                print("No articles found.")
                return []
            
            print(f"Fetched {len(articles)} articles.")
            return articles
            
        except Exception as e:
            print(f"Request failed: {e}")
            return []


class SentimentAnalyzer:
    """Performs sentiment analysis on article titles."""
    
    def __init__(self, vader_analyzer: SentimentIntensityAnalyzer):
        self.vader = vader_analyzer
    
    def get_sentiment_score(self, title: str) -> float:
        """Calculate sentiment score for a title."""
        if not title:
            return 0
        scores = self.vader.polarity_scores(title)
        return scores['compound']
    
    def get_sentiment_label(self, score: float) -> str:
        """Convert sentiment score to readable label."""
        if score >= 0.05:
            return "Positive"
        if score <= -0.05:
            return "Negative"
        return "Neutral"
    
    def analyze_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add sentiment analysis to dataframe."""
        print(f"Analyzing sentiment for {len(df)} headlines...")
        df['sentiment_score'] = df['title'].apply(self.get_sentiment_score)
        df['sentiment_label'] = df['sentiment_score'].apply(self.get_sentiment_label)
        return df


class DataProcessor:
    """Processes and cleans article data."""
    
    @staticmethod
    def parse_gdelt_time(t) -> datetime:
        """Parse GDELT timestamp format."""
        if pd.isna(t) or t == "":
            return None
        t = str(t)
        try:
            return datetime.strptime(t, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        except:
            return None
    
    @staticmethod
    def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Clean and reorder dataframe columns."""
        # Parse dates
        if 'seendate' in df.columns:
            df['seendate_dt'] = df['seendate'].apply(DataProcessor.parse_gdelt_time)
        
        # Define desired columns
        desired_columns = [
            "seendate_dt", "sentiment_score", "sentiment_label", "title", 
            "domain", "url", "url_mobile", "socialimage", "seendate", 
            "language", "sourcecountry"
        ]
        
        # Add missing columns
        for col in desired_columns:
            if col not in df.columns:
                df[col] = None
        
        return df[desired_columns]


class MongoDBSync:
    """Handles MongoDB synchronization."""
    
    def __init__(self, connection_string: str = "mongodb://localhost:27017/"):
        self.connection_string = connection_string
        self.client = None
        self.db = None
        self.collection = None
    
    def connect(self, db_name: str = "gdelt_articles_sentiment", 
                collection_name: str = "articles_sentiment"):
        """Connect to MongoDB database."""
        self.client = pymongo.MongoClient(self.connection_string)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        print(f"Connected to MongoDB: {db_name}.{collection_name}")
    
    def sync_articles(self, df: pd.DataFrame) -> Tuple[int, int]:
        """Sync articles to MongoDB with upsert logic."""
        records = df.to_dict("records")
        print(f"Syncing {len(records)} articles to MongoDB...")
        
        new_count = 0
        updated_count = 0
        
        for record in records:
            result = self.collection.update_one(
                filter={"url": record["url"]},
                update={"$set": record},
                upsert=True
            )
            
            if result.upserted_id:
                new_count += 1
            else:
                updated_count += 1
        
        print(f"Database Update Complete: {new_count} New, {updated_count} Updated.")
        return new_count, updated_count
    
    def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()


class SentimentReporter:
    """Generates reports and extracts top sentiment articles."""
    
    @staticmethod
    def print_top_sentiment(df: pd.DataFrame):
        """Print most positive and negative headlines."""
        print("\n--- Most Positive Headlines ---")
        print(df.sort_values('sentiment_score', ascending=False)[['sentiment_score', 'title']].head(3))
        
        print("\n--- Most Negative Headlines ---")
        print(df.sort_values('sentiment_score', ascending=True)[['sentiment_score', 'title']].head(3))
    
    @staticmethod
    def get_top_sentiment_urls(df: pd.DataFrame, top_n: int = 3) -> Dict[str, List[str]]:
        """
        Return URLs of top positive and negative news articles.
        
        Args:
            df: DataFrame with sentiment analysis
            top_n: Number of top articles to return (default: 3)
        
        Returns:
            Dictionary with 'positive' and 'negative' keys containing lists of URLs
        """
        top_positive = df.nlargest(top_n, 'sentiment_score')['url'].tolist()
        top_negative = df.nsmallest(top_n, 'sentiment_score')['url'].tolist()
        
        return {
            'positive': top_positive,
            'negative': top_negative
        }
    
    @staticmethod
    def save_to_csv(df: pd.DataFrame, output_dir: str = 'data'):
        """Save dataframe to CSV with timestamp."""
        os.makedirs(output_dir, exist_ok=True)
        current_time = pd.Timestamp.now(tz='Europe/Warsaw').strftime("%Y%m%d_%H%M%S_%Z")
        output_file = f"{output_dir}/gdelt_headlines_sentiment_{current_time}.csv"
        df.to_csv(output_file, index=False)
        print(f"Success! Saved to {output_file}")


class GDELTSentimentPipeline:
    """Main pipeline orchestrating the entire workflow."""
    
    def __init__(self, config: GDELTConfig = None, mongo_connection: str = None):
        self.config = config or GDELTConfig()
        self.vader = VaderSetup.initialize()
        self.fetcher = GDELTFetcher(self.config)
        self.analyzer = SentimentAnalyzer(self.vader)
        self.processor = DataProcessor()
        self.reporter = SentimentReporter()
        self.mongo = MongoDBSync(mongo_connection) if mongo_connection else None
    
    def run(self, save_to_csv: bool = False, sync_to_mongo: bool = False) -> pd.DataFrame:
        """Execute the full pipeline."""
        # Fetch articles
        articles = self.fetcher.fetch_articles()
        if not articles:
            return pd.DataFrame()
        
        # Create dataframe
        df = pd.DataFrame(articles)
        
        # Analyze sentiment
        df = self.analyzer.analyze_dataframe(df)
        
        # Process and clean
        df_final = self.processor.prepare_dataframe(df)
        
        # Report
        self.reporter.print_top_sentiment(df_final)
        
        # Save to CSV
        if save_to_csv:
            self.reporter.save_to_csv(df_final)
        
        # Sync to MongoDB
        if sync_to_mongo and self.mongo:
            self.mongo.connect()
            self.mongo.sync_articles(df_final)
            self.mongo.close()
        
        return df_final
    
    def get_top_sentiment_urls(self, df: pd.DataFrame = None, top_n: int = 3) -> Dict[str, List[str]]:
        """Get top positive and negative article URLs."""
        if df is None:
            df = self.run()
        return self.reporter.get_top_sentiment_urls(df, top_n)


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # Initialize and run pipeline
    pipeline = GDELTSentimentPipeline(mongo_connection="mongodb://localhost:27017/")
    
    # Run the full pipeline
    df_result = pipeline.run(save_to_csv=False, sync_to_mongo=True)
    
    # Get top sentiment URLs
    top_urls = pipeline.get_top_sentiment_urls(df_result)
    
    print("\n--- Top 3 Positive News URLs ---")
    for i, url in enumerate(top_urls['positive'], 1):
        print(f"{i}. {url}")
    
    print("\n--- Top 3 Negative News URLs ---")
    for i, url in enumerate(top_urls['negative'], 1):
        print(f"{i}. {url}")
    
    scraped_raw_html = scrape_clean_html_groups(top_urls)
    
    process_and_send_summary(scraped_raw_html)
    
