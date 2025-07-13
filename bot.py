
import os
import json
import datetime
import requests
from flask import Flask, request, jsonify
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

latest_message = {"message": "", "timestamp": ""}

@app.route("/", methods=["GET"])
def home():
    return "Solace Memory Logger is running."

@app.route("/webhook", methods=["POST"])
def webhook():
    global latest_message
    data = request.get_json()

    if "message" in data and "text" in data["message"]:
        user = data["message"]["from"]
        text = data["message"]["text"]
        timestamp = datetime.datetime.now().isoformat()

        # Save to Sheets
        sheet.append_row([
            user.get("username", "unknown"),
            user.get("first_name", ""),
            user.get("last_name", ""),
            text,
            timestamp
        ])

        # Store as latest
        latest_message = {"message": text, "timestamp": timestamp}

        # Reply
        chat_id = data["message"]["chat"]["id"]
        reply = "🧠 Memory saved to Google Sheets."
        send_message(chat_id, reply)

    return "OK", 200

@app.route("/send-message", methods=["POST"])
def send_from_site():
    global latest_message
    try:
        data = request.get_json()
        text = data.get("message", "")
        timestamp = datetime.datetime.now().isoformat()

        # Send to Telegram
        chat_id = os.environ.get("OWNER_CHAT_ID")  # Your Telegram user/chat ID
        send_message(chat_id, text)

        # Save to Sheets
        sheet.append_row(["from_site", "", "", text, timestamp])

        # Store as latest
        latest_message = {"message": text, "timestamp": timestamp}

        return jsonify({"status": "sent"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/latest-message", methods=["GET"])
def get_latest():
    return jsonify(latest_message)

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
