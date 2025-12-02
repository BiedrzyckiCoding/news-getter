import smtplib
import ssl
from email.message import EmailMessage
import os
from dotenv import load_dotenv

load_dotenv()

# 1. Konfiguracja nadawcy i odbiorcy
email_nadawca = 'daybreak.brief@gmail.com'
# Poniżej wklej wygenerowane 16-znakowe hasło do aplikacji (nie zwykłe hasło!)
email_haslo = os.environ.get('GMAIL_APP_PASSWORD')
email_odbiorca = 'kubabiedrzy@gmail.com'

# 2. Temat i treść wiadomości
temat = 'Testowa wiadomość z Pythona'
tresc = """
Cześć,

To jest testowa wiadomość wysłana automatycznie przez skrypt w Pythonie!
"""

# 3. Tworzenie obiektu wiadomości
em = EmailMessage()
em['From'] = email_nadawca
em['To'] = email_odbiorca
em['Subject'] = temat
em.set_content(tresc)

# 4. Łączenie z serwerem SMTP Gmaila i wysyłanie
# Adres serwera: smtp.gmail.com
# Port dla SSL: 465
context = ssl.create_default_context()

try:
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
        smtp.login(email_nadawca, email_haslo)
        smtp.sendmail(email_nadawca, email_odbiorca, em.as_string())
    print("E-mail został wysłany pomyślnie!")
except Exception as e:
    print(f"Błąd podczas wysyłania: {e}")