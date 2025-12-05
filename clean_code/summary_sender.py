import ollama
import os
import smtplib
import ssl
from email.message import EmailMessage
from dotenv import load_dotenv

from master_prompt import MASTER_PROMPT

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
    master_prompt = MASTER_PROMPT

    user_content = f"""
    === POSITIVE SOURCES ===
    {news_data['positive']}

    === NEGATIVE SOURCES ===
    {news_data['negative']}
    """

    print(f"Generating summary with model (this may take a moment)...")

    # 3. Call Local LLM (Ollama)
    try:
        response = ollama.chat(model="qwen3:30b", messages=[
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
    # email_odbiorcy = ['kubabiedrzy@gmail.com', 'nbiedrzy@gmail.com', 'kapibied@gmail.com']
    email_odbiorcy = ['kubabiedrzy@gmail.com']

    if not email_haslo:
        print("Error: GMAIL_APP_PASSWORD not set in environment.")
        return

    # 5. Build Email
    msg = EmailMessage()
    msg['From'] = email_nadawca
    msg['To'] = ", ".join(email_odbiorcy)
    msg['Subject'] = 'Daybreak Brief: Positive vs Negative Report'
    msg.set_content(generated_summary)

    # 6. Send Email
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
            smtp.login(email_nadawca, email_haslo)
            smtp.sendmail(email_nadawca, email_odbiorcy, msg.as_string())
        print(f"✅ Email successfully sent to: {', '.join(email_odbiorcy)}")
    except Exception as e:
        print(f"❌ Error sending email: {e}")