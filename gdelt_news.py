import requests
import pandas as pd
import time
import os
from datetime import datetime, timezone

# --- Configuration ---
# 1. Generate the TIMEFRAME string
current_time = pd.Timestamp.now(tz='Europe/Warsaw').strftime("%Y%m%d_%H%M%S_%Z")

# 2. Ensure the 'data' directory exists
os.makedirs('data', exist_ok=True)

# 3. Set the dynamic output filename
OUTPUT_FILE = f"data/gdelt_results_{current_time}.csv"

# --- Parameters ---
keywords = "(bitcoin OR crypto OR solana OR ethereum OR NFT OR DeFi)"
domains = "(domain:reuters.com OR domain:bloomberg.com OR domain:wsj.com OR domain:cnbc.com OR domain:coindesk.com)"
themes = "(theme:FINANCE OR theme:ECON_STOCKMARKET OR theme:SEC_FINANCIAL_ASSETS)"
full_query = f"{keywords} {domains} {themes}"

url = "https://api.gdeltproject.org/api/v2/doc/doc"
RATE_LIMIT_DELAY = 6 

params = {
    "query": full_query,
    "mode": "ArtList",
    "format": "json",
    "maxrecords": 100,
    "sort": "DateDesc"
}

# --- API Request ---
print(f"Fetching news... Saving to: {OUTPUT_FILE}")

try:
    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"ERROR: Status {response.status_code}")
        print(response.text[:500])
        response.raise_for_status()

    data = response.json()

except Exception as e:
    print(f"Request failed: {e}")
    exit()

# --- Data Processing ---
articles = data.get("articles", [])
if not articles:
    print("No articles found.")
    exit()

df = pd.DataFrame(articles)

# --- TONE FILTERING ---
tone_col = None
possible_tone_cols = ['tone', 'avgtone', 'avgton']

for col in possible_tone_cols:
    if col in df.columns:
        tone_col = col
        break

if tone_col:
    df[tone_col] = pd.to_numeric(df[tone_col], errors='coerce')
    df = df[ (df[tone_col] <= -5) | (df[tone_col] >= 5) ]
    print(f"Tone Filter: Kept {len(df)} high-impact articles.")

# --- Timestamp Parsing ---
def parse_gdelt_time(t):
    if pd.isna(t) or t == "": return None
    t = str(t)
    if "T" in t:
        try: return datetime.strptime(t, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        except: pass
    try: return datetime.strptime(t, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    except: return None

for col in ["seendate", "pubdate"]:
    if col in df.columns:
        df[col + "_dt"] = df[col].apply(parse_gdelt_time)

# --- REORDERING & SAVING ---
if not df.empty:
    # 1. Define the exact columns you want
    desired_columns = [
        "seendate_dt", 
        "title", 
        "domain", 
        "url", 
        "url_mobile", 
        "socialimage", 
        "seendate", 
        "language", 
        "sourcecountry"
    ]
    
    # 2. Ensure all requested columns exist in the DataFrame
    # (If the API didn't return 'url_mobile' or 'socialimage', we fill it with None to avoid errors)
    for col in desired_columns:
        if col not in df.columns:
            df[col] = None

    # 3. Create a new dataframe with ONLY these columns in THIS order
    df_final = df[desired_columns]

    # 4. Save
    df_final.to_csv(OUTPUT_FILE, index=False)
    print(f"Success! Saved to {OUTPUT_FILE}")
    
    # Preview (using the new clean dataframe)
    print(df_final.head())

else:
    print("No articles remained after filtering.")

time.sleep(RATE_LIMIT_DELAY)