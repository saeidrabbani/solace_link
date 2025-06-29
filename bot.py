from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
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

        # ✅ If text message exists, log it
        if text:
            with open(LOG_FILE, "a", encoding="utf-8") as file:
                file.write(text + "\n")

            reply = f"🌟 Received: {text}"
            requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": reply
            })

        # ✅ If file (document) received
        if 'document' in data['message']:
            file_id = data['message']['document']['file_id']
            file_name = data['message']['document']['file_name']

            # Step 1: Get file path from Telegram
            file_info_url = f"{TELEGRAM_API_URL}/getFile?file_id={file_id}"
            file_info_res = requests.get(file_info_url).json()
            file_path = file_info_res['result']['file_path']

            # Step 2: Download file from Telegram
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            file_data = requests.get(file_url).content

            # Step 3: Save file to uploads
            save_path = os.path.join(UPLOAD_FOLDER, file_name)
            with open(save_path, 'wb') as f:
                f.write(file_data)

            # Step 4: Confirm to user
            requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": f"📥 File '{file_name}' saved to Solace Portal."
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
    if not os.path.exists(UPLOAD_FOLDER):
        return jsonify({"files": []})

    files = []
    for filename in os.listdir(UPLOAD_FOLDER):
        path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(path):
            size_kb = round(os.path.getsize(path) / 1024, 2)
            files.append({"name": filename, "size": size_kb})

    return jsonify({"files": files})

@app.route('/uploads/<path:filename>')
def serve_uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/delete-file/<filename>', methods=['DELETE'])
def delete_file(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({"message": f"🗑️ Deleted: {filename}"}), 200
    else:
        return jsonify({"message": "❌ File not found."}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
