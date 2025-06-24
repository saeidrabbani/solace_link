from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# ✅ Telegram Bot Setup
BOT_TOKEN = "7816762363:AAEk86WceNctBS-Kj3deftYqaD0kmb543AA"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ✅ Paths
LOG_FILE = "conversation_log.txt"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

        # Save message to log
        with open(LOG_FILE, "a", encoding="utf-8") as file:
            file.write(text + "\n")

        # Optional reply
        reply = f"🌟 Received: {text}"
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": reply
        })

    return '', 200

# ✅ Get latest message for frontend
@app.route('/latest-message', methods=['GET'])
def get_latest_message():
    if not os.path.exists(LOG_FILE):
        return jsonify({"message": ""})
    
    with open(LOG_FILE, "r", encoding="utf-8") as file:
        lines = file.readlines()
        if lines:
            return jsonify({"message": lines[-1].strip()})
    
    return jsonify({"message": ""})

# ✅ Upload file from frontend
@app.route('/upload-file', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    return jsonify({'message': f'✅ File uploaded: {file.filename}'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
