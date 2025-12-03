import requests
import pandas as pd
import time
import os
from datetime import datetime, timezone
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import pymongo

import clean_code.scraper as scraper


# --- SETUP VADER (Run this once) ---
# VADER requires a small lexicon file to work. 
# We download it automatically if you don't have it.
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    print("Downloading VADER lexicon...")
    nltk.download('vader_lexicon')

# Initialize the analyzer
vader = SentimentIntensityAnalyzer()

# --- Configuration ---
current_time = pd.Timestamp.now(tz='Europe/Warsaw').strftime("%Y%m%d_%H%M%S_%Z")
os.makedirs('data', exist_ok=True)
OUTPUT_FILE = f"data/gdelt_headlines_sentiment_{current_time}.csv"

# --- Parameters ---
keywords = "(bitcoin OR crypto OR solana OR ethereum OR NFT OR DeFi)"
domains = "(domain:reuters.com OR domain:bloomberg.com OR domain:wsj.com OR domain:cnbc.com OR domain:coindesk.com)"
themes = "(theme:FINANCE OR theme:ECON_STOCKMARKET OR theme:SEC_FINANCIAL_ASSETS)"
full_query = f"{keywords} {domains} {themes}"

url = "https://api.gdeltproject.org/api/v2/doc/doc"

params = {
    "query": full_query,
    "mode": "ArtList",
    "format": "json",
    "maxrecords": 100,
    "sort": "DateDesc"
}

# --- API Request ---
print("Fetching headlines...")
try:
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
except Exception as e:
    print(f"Request failed: {e}")
    exit()

articles = data.get("articles", [])
if not articles:
    print("No articles found.")
    exit()

df = pd.DataFrame(articles)

# --- 🧠 AI SENTIMENT ANALYSIS ---
print(f"Analyzing sentiment for {len(df)} headlines...")

def get_sentiment(title):
    if not title: return 0
    # polarity_scores returns a dict: {'neg': 0.0, 'neu': 0.4, 'pos': 0.6, 'compound': 0.5}
    # We only care about 'compound' which combines them all (-1 to +1)
    scores = vader.polarity_scores(title)
    return scores['compound']

# Apply the function to the 'title' column
df['sentiment_score'] = df['title'].apply(get_sentiment)

# Optional: Create a readable label
def get_label(score):
    if score >= 0.05: return "Positive"
    if score <= -0.05: return "Negative"
    return "Neutral"

df['sentiment_label'] = df['sentiment_score'].apply(get_label)

# --- Clean & Reorder ---
# Parse dates
def parse_gdelt_time(t):
    if pd.isna(t) or t == "": return None
    t = str(t)
    try: return datetime.strptime(t, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except: return None

if 'seendate' in df.columns:
    df['seendate_dt'] = df['seendate'].apply(parse_gdelt_time)

# Select columns (Added 'sentiment_score' and 'sentiment_label')
desired_columns = [
    "seendate_dt", "sentiment_score", "sentiment_label", "title", 
    "domain", "url", "url_mobile", "socialimage", "seendate", "language", "sourcecountry"
]

for col in desired_columns:
    if col not in df.columns:
        df[col] = None

df_final = df[desired_columns]

# --- Save ---
# df_final.to_csv(OUTPUT_FILE, index=False)
# print(f"Success! Saved to {OUTPUT_FILE}")

# Preview the most positive/negative news
print("\n--- Most Positive Headlines ---")
print(df_final.sort_values('sentiment_score', ascending=False)[['sentiment_score', 'title']].head(3))

print("\n--- Most Negative Headlines ---")
print(df_final.sort_values('sentiment_score', ascending=True)[['sentiment_score', 'title']].head(3))

# --- 1. Database Connection ---
# If using a local DB: "mongodb://localhost:27017/"
# If using Cloud (Atlas): "mongodb+srv://<user>:<password>@cluster0.mongodb.net/..."
connection_string = "mongodb://localhost:27017/" 
client = pymongo.MongoClient(connection_string)

# Create/Connect to Database and Collection
db = client["gdelt_articles_sentiment"]
collection = db["articles_sentiment"]

# --- 2. Prepare Data ---
# MongoDB needs a list of dictionaries, not a Pandas DataFrame
records = df_final.to_dict("records")

print(f"Syncing {len(records)} articles to MongoDB...")

# --- 3. The "Upsert" Loop ---
new_count = 0
updated_count = 0

for record in records:
    # We use the 'url' as the Unique Key (Primary Key)
    result = collection.update_one(
        filter={"url": record["url"]},  # Find article by URL
        update={"$set": record},        # Update/Set the data
        upsert=True                     # Create if it doesn't exist
    )
    
    if result.upserted_id:
        new_count += 1
    else:
        updated_count += 1

print(f"Database Update Complete: {new_count} New, {updated_count} Updated.")

