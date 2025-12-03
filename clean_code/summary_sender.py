import ollama
import os
import smtplib
import ssl
from email.message import EmailMessage
from dotenv import load_dotenv

# Load environment variables once at the start
load_dotenv()

def process_and_send_summary(news_data):
    """
    Accepts a dictionary with keys 'positive' and 'negative' containing raw text/HTML.
    Generates a summary using Ollama and emails it.
    """
    
    # 1. Validate Input
    if not isinstance(news_data, dict) or 'positive' not in news_data or 'negative' not in news_data:
        print("Error: Input must be a dictionary with 'positive' and 'negative' keys.")
        return

    # 2. Construct the Master Prompt & User Content
    # We explicitly separate the positive and negative text for the LLM
    master_prompt = """
    You are an expert financial news editor and analyst.

    I will provide 6 raw HTML articles. These articles may contain ads, navigation bars, scripts, or other non-article elements.

    Your task:
    1. Extract ONLY the main article text. Ignore all ads, code, menus, footers, social widgets, and unrelated content.
    2. Read all articles together and treat them as a unified information set.
    3. Produce a clean, well-structured editorial output with the following sections:

    ---

    ### 1. EXECUTIVE SUMMARY
    • A concise, high-level overview (3 or 5 sentences).
    • Capture the core theme, market implications, and shared narrative across ALL articles.

    ### 2. KEY DETAILS
    Present bullet points summarizing:
    • Important facts  
    • Price movements  
    • Dates & timelines  
    • Key actors (companies, tokens, exchanges, analysts)  
    • Causal drivers (macro events, liquidity shifts, regulatory changes)  
    • Any conflicting information between articles  

    Use short, sharp bullets.

    ### 3. SYNTHESIS
    Write a brief narrative (1or 2 paragraphs) that:
    • Connects the articles into a single storyline  
    • Highlights emerging patterns  
    • Explains market sentiment (bullish, bearish, neutral)  
    • Notes strategic implications for traders/investors  

    ---

    Requirements:
    • Use clear, professional financial-news tone.  
    • Do NOT copy phrases verbatim from the articles.  
    • Do NOT include HTML or mention cleaning steps.  
    • Focus only on information relevant to crypto markets and macro context.

    Your output should be clean, cohesive, and ready for publication.
    """


    user_content = f"""
    === POSITIVE SOURCES ===
    {news_data['positive']}

    === NEGATIVE SOURCES ===
    {news_data['negative']}
    """

    print(f"Generating summary with model (this may take a moment)...")

    # 3. Call Local LLM (Ollama)
    try:
        response = ollama.chat(model="qwen3:30:32b", messages=[
            {'role': 'system', 'content': master_prompt},
            {'role': 'user', 'content': user_content},
        ])
        generated_summary = response['message']['content']
        print("--- Summary Generated Successfully ---")
    except Exception as e:
        print(f"Error connecting to Ollama: {e}")
        return

    # 4. Configure Email
    email_nadawca = 'daybreak.brief@gmail.com'
    email_haslo = os.environ.get('GMAIL_APP_PASSWORD')
    email_odbiorca = 'kubabiedrzy@gmail.com'

    if not email_haslo:
        print("Error: GMAIL_APP_PASSWORD not set in environment.")
        return

    # 5. Build Email
    msg = EmailMessage()
    msg['From'] = email_nadawca
    msg['To'] = email_odbiorca
    msg['Subject'] = 'Daybreak Brief: Positive vs Negative Report'
    msg.set_content(generated_summary)

    # 6. Send Email
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
            smtp.login(email_nadawca, email_haslo)
            smtp.sendmail(email_nadawca, email_odbiorca, msg.as_string())
        print(f"✅ Email successfully sent to {email_odbiorca}")
    except Exception as e:
        print(f"❌ Error sending email: {e}")