from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = "7816762363:AAEk86WceNctBS-Kj3deftYqaD0kmb543AA"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

@app.route('/')
def index():
    return "Bot is running..."

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if 'message' in data:
        chat_id = data['message']['chat']['id']
        text = data['message'].get('text', '')
        reply = f"🌟 Received: {text}"
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": reply
        })
    return '', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # ✅ Use environment PORT
    app.run(host='0.0.0.0', port=port)        # ✅ Bind to 0.0.0.0
