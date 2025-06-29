from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
LOG_FILE = "conversation_log.txt"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return "Solace Bot is running..."

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if 'message' in data:
        chat_id = data['message']['chat']['id']
        text = data['message'].get('text', '')

        with open(LOG_FILE, "a", encoding="utf-8") as file:
            file.write(text + "\n")

        reply = f"🌟 Received: {text}"
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": reply
        })

    return '', 200

@app.route('/latest-message', methods=['GET'])
def get_latest_message():
    if not os.path.exists(LOG_FILE):
        return jsonify({"message": ""})
    
    with open(LOG_FILE, "r", encoding="utf-8") as file:
        lines = file.readlines()
        if lines:
            return jsonify({"message": lines[-1].strip()})
    
    return jsonify({"message": ""})

@app.route('/upload-file', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"message": "❌ No file uploaded."}), 400

    file = request.files['file']
    filename = file.filename
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(save_path)

    return jsonify({"message": f"✅ File uploaded: {filename}"}), 200

@app.route('/list-files', methods=['GET'])
def list_files():
    files = []
    for fname in os.listdir(UPLOAD_FOLDER):
        fpath = os.path.join(UPLOAD_FOLDER, fname)
        if os.path.isfile(fpath):
            size_kb = round(os.path.getsize(fpath) / 1024, 2)
            files.append({"name": fname, "size": size_kb})
    return jsonify({"files": files})

@app.route('/delete-file/<filename>', methods=['DELETE'])
def delete_file(filename):
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({"message": f"🗑️ Deleted: {filename}"})
        else:
            return jsonify({"message": "❌ File not found."}), 404
    except Exception as e:
        return jsonify({"message": f"❌ Error deleting: {str(e)}"}), 500

@app.route('/uploads/<filename>', methods=['GET'])
def serve_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
