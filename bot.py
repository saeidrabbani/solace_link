import os
import json
import datetime
import requests
from flask import Flask, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
SPREADSHEET_ID = "1GFm1IdDYw_jcPw2azflRK0hux0UKWCmqLekQJkezoac"
CREDENTIALS_PATH = "/etc/secrets/credentials.json"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

@app.route("/", methods=["GET"])
def home():
    return "Solace Memory Logger is running."

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data and "text" in data["message"]:
        user = data["message"]["from"]
        text = data["message"]["text"]
        timestamp = datetime.datetime.now().isoformat()

        sheet.append_row([
            user.get("username", "unknown"),
            user.get("first_name", ""),
            user.get("last_name", ""),
            text,
            timestamp
        ])

        chat_id = data["message"]["chat"]["id"]
        reply = "🧠 Memory saved to Google Sheets."
        send_message(chat_id, reply)

    return "OK", 200

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(debug=True)
