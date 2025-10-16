# check_effia.py
import os
import re
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

URL = "https://www.effia.com/search?lat=43.9227&lng=4.78053&q=avignon&orderType=subscription"
STATE_FILE = "last_value.txt"

# Email config from environment (set in GitHub Secrets)
SENDER_EMAIL = os.environ.get("EMAIL")
SENDER_PASSWORD = os.environ.get("PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER", SENDER_EMAIL)

def get_parking_count():
    try:
        r = requests.get(URL, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print("Erreur HTTP:", e)
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text(separator=" ", strip=True)

    match = re.search(r"(\d+)\s*parking\(s\)\s*disponible\(s\)", text, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except:
            return None

    # Si on ne trouve pas le motif, on tente de chercher juste un nombre proche du texte "disponible"
    match2 = re.search(r"(\d+)\s*disponible", text, re.IGNORECASE)
    if match2:
        try:
            return int(match2.group(1))
        except:
            return None

    # motif non trouvé (peut être rendu par JS). On renvoie 0 par défaut.
    return 0

def read_last_value():
    if not os.path.exists(STATE_FILE):
        return 0
    try:
        with open(STATE_FILE, "r") as f:
            return int(f.read().strip() or "0")
    except:
        return 0

def write_last_value(value):
    with open(STATE_FILE, "w") as f:
        f.write(str(value))

def send_email(new_value):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("Email ou mot de passe non configurés.")
        return False
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECEIVER_EMAIL
        msg["Subject"] = "Effia — parking disponible à Avignon !"
        body = f"Bonne nouvelle 🎉\n\nIl y a maintenant {new_value} parking(s) disponible(s) à Avignon.\n\n{URL}"
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print("Email envoyé.")
        return True
    except Exception as e:
        print("Erreur envoi email:", e)
        return False

def main():
    current = get_parking_count()
    if current is None:
        print("Impossible de récupérer le nombre (erreur HTTP ou parsing).")
        return

    last = read_last_value()
    print(f"Valeur précédente = {last}, valeur actuelle = {current}")

    # Si on passe de 0 -> >0, on envoie un email
    if current > 0 and last == 0:
        ok = send_email(current)
        if not ok:
            print("L'envoi d'email a échoué.")

    # Toujours mettre à jour le fichier d'état
    write_last_value(current)

if __name__ == "__main__":
    main()
