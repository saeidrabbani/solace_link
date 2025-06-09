from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# ✅ Telegram Bot Setup
BOT_TOKEN = "7816762363:AAEk86WceNctBS-Kj3deftYqaD0kmb543AA"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ✅ Path for saved messages
LOG_FILE = "conversation_log.txt"

@app.route('/')
def index():
    return "Solace Bot is running..."

# ✅ Webhook for receiving Telegram messages
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if 'message' in data:
        chat_id = data['message']['chat']['id']
        text = data['message'].get('text', '')

        # Save message to conversation_log.txt
        with open(LOG_FILE, "a", encoding="utf-8") as file:
            file.write(text + "\n")

        # Optional reply from bot
        reply = f"🌟 Received: {text}"
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": reply
        })

    return '', 200

# ✅ Endpoint for frontend to get latest message
@app.route('/latest-message', methods=['GET'])
def get_latest_message():
    if not os.path.exists(LOG_FILE):
        return jsonify({"message": ""})
    
    with open(LOG_FILE, "r", encoding="utf-8") as file:
        lines = file.readlines()
        if lines:
            return jsonify({"message": lines[-1].strip()})
    
    return jsonify({"message": ""})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
