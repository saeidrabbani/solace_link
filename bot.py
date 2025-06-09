from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = "7816762363:AAEk86WceNctBS-Kj3deftYqaD0kmb543AA"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

messages = []  # List baraye zakhire kardan payam-ha

@app.route('/')
def index():
    return "Bot is running..."

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if 'message' in data:
        chat_id = data['message']['chat']['id']
        text = data['message'].get('text', '')
        
        # 🔴 Save message
        messages.append(text)

        # Optional: bot reply
        reply = f"🌟 Received: {text}"
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": reply
        })

    return '', 200

# ✅ Route for static site to fetch last message
@app.route('/latest-message', methods=['GET'])
def latest_message():
    if messages:
        return {'message': messages[-1]}, 200
    else:
        return {'message': 'No message yet'}, 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
