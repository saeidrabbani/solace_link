import os
import json
import datetime
import requests
from flask import Flask, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# Telegram config
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OWNER_CHAT_ID = os.environ.get("OWNER_CHAT_ID")

# Google Sheets config
SPREADSHEET_ID = "1GFm1IdDYw_jcPw2azflRK0hux0UKWCmqLekQJkezoac"
CREDENTIALS_PATH = "/etc/secrets/credentials.json"

# Setup Google Sheets connection
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

        try:
            sheet.append_row([
                user.get("username", "unknown"),
                user.get("first_name", ""),
                user.get("last_name", ""),
                text,
                timestamp
            ])
            print("✅ Telegram → Sheet saved successfully.")
        except Exception as e:
            print("❌ Error saving Telegram message to Sheet:", str(e))

        chat_id = data["message"]["chat"]["id"]
        send_message(chat_id, "🧠 Memory saved to Google Sheets.")

    return "OK", 200

@app.route("/send-from-site", methods=["POST"])
@app.route("/save-message", methods=["POST"])  # ✅ new route added
def save_message():
    data = request.get_json()
    message = data.get("message", "")

    if not message:
        return jsonify({"error": "No message provided"}), 400

    send_message(OWNER_CHAT_ID, message)
    print("📤 Message sent to Telegram:", message)

    try:
        timestamp = datetime.datetime.now().isoformat()
        sheet.append_row([
            "solace_portal", "", "", message, timestamp
        ])
        print("✅ Site → Sheet saved successfully.")
    except Exception as e:
        print("❌ Error saving Site message to Sheet:", str(e))

    return jsonify({"status": "sent and saved"}), 200

@app.route("/latest-message", methods=["GET"])
def latest_message():
    try:
        all_records = sheet.get_all_values()
        if len(all_records) < 2:
            return jsonify({"message": "", "timestamp": ""})
        last_row = all_records[-1]
        return jsonify({"message": last_row[3], "timestamp": last_row[4]})
    except Exception as e:
        return jsonify({"error": "❌ Fetch error: " + str(e)}), 500

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        response = requests.post(url, json=payload)
        print("📤 Telegram response:", response.text)
    except Exception as e:
        print("❌ Error sending message to Telegram:", str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
