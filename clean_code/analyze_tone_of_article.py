from scraper import scrape_clean_html_list
from tone_analyzer import analyze_tone
from transformers import pipeline
import numpy as np
import tiktoken

import re

url = "https://www.coindesk.com/daybook-us/2025/11/28/out-of-breadth-crypto-daybook-americas"

dict = scrape_clean_html_list([url])

def clean_financial_text(text):
    # Flatten text first to make spacing consistent
    text = " ".join(text.split())
    
    # Remove specific header junk explicitly (No ".*" wildcards!)
    junk_phrases = [
        "Search / News Video Prices Research",
        "Consensus 2026 Data & Indices Sponsored Search / en",
        "Out of Breadth: Crypto Daybook Americas", # Remove title repetition if needed
        "Share this article Copy link X icon X (Twitter) LinkedIn Facebook Email"
    ]
    
    for phrase in junk_phrases:
        text = text.replace(phrase, " ")

    # Remove the ticker data (e.g., "BTC $ 89,189.08 3.53 %")
    # This regex looks for: Capital letters -> $ -> Numbers -> %
    text = re.sub(r'[A-Z]{2,5}\s\$\s[\d,]+\.\d+\s\d+\.\d+\s%', '', text)
    
    # Remove stand-alone noise like "USDT $ 1.0002 0.00 %" if missed above
    text = re.sub(r'\$\s[\d,]+\.\d+', '', text)
    
    # Final cleanup of double spaces created by the removals
    text = " ".join(text.split())
    
    return text

def analyze_long_text(text, chunk_size=1024):
    classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
    
    # Financial labels
    candidate_labels = [
        "Positive Market Outlook", 
        "Negative Market Outlook", 
        "Cautious Market Outlook", 
        "Neutral News"
        ]
    
    template = "The financial sentiment of this article is {}."

    # --- THE FIX: CHUNKING STRATEGY ---
    # We split the text into chunks of ~1024 characters (safe size for tokens)
    # We overlap slightly to not cut sentences in half
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    
    print(f"Analyzing {len(chunks)} text chunks...")
    
    scores_map = {label: [] for label in candidate_labels}

    for i, chunk in enumerate(chunks):
        # Skip chunks that are too short (garbage data)
        if len(chunk) < 50: continue
            
        result = classifier(chunk, candidate_labels, hypothesis_template=template)
        
        # Store scores for this chunk
        for label, score in zip(result['labels'], result['scores']):
            scores_map[label].append(score)

    # Calculate Average Scores across all chunks
    final_results = {}
    for label, scores in scores_map.items():
        final_results[label] = np.mean(scores)

    # Sort results by score (highest first)
    sorted_results = sorted(final_results.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "top_label": sorted_results[0][0],
        "top_score": sorted_results[0][1],
        "full_breakdown": sorted_results
    }
    
def count_gpt4o_tokens(text: str) -> int:
    """
    Returns the number of GPT-4o tokens in the given string.
    """
    enc = tiktoken.encoding_for_model("gpt-4o")
    tokens = enc.encode(text)
    return len(tokens)

raw_text = dict[url] 
cleaned_text = clean_financial_text(raw_text)

print(count_gpt4o_tokens(cleaned_text))

# print("CLEANED TEXT: ", cleaned_text)

# analysis = analyze_long_text(cleaned_text)

# print(f"\nFINAL RESULT (Averaged across {len(cleaned_text)//1024 + 1} chunks):")
# print(f"Top Tone: {analysis['top_label']}")
# print(f"Confidence: {analysis['top_score']:.4f}")

# print("\nFull Breakdown:")
# for label, score in analysis['full_breakdown']:
#     print(f"- {label}: {score:.4f}")