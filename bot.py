from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "7816762363:AAEk86WceNctBS-Kj3deftYqaD0kmb543AA"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
LOG_FILE = "conversation_log.txt"
UPLOAD_FOLDER = "uploads"
CHAT_ID = "589089595"  # Saeid's Telegram chat ID
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return "Solace Bot is running..."

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if 'message' in data:
        message = data['message']
        chat_id = message['chat']['id']

        if 'text' in message:
            text = message['text']
            with open(LOG_FILE, "a", encoding="utf-8") as file:
                file.write(text + "\n")

            reply = f"🌟 Received: {text}"
            requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": reply
            })

        elif 'document' in message:
            file_id = message['document']['file_id']
            file_name = message['document']['file_name']
            file_info_res = requests.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}").json()

            if 'result' in file_info_res:
                file_path = file_info_res['result']['file_path']
                file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                file_data = requests.get(file_url)

                with open(os.path.join(UPLOAD_FOLDER, file_name), 'wb') as f:
                    f.write(file_data.content)

                requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": f"✅ File saved to Solace Portal: {file_name}"
                })
            else:
                requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": "❌ Could not retrieve file info."
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
    for filename in os.listdir(UPLOAD_FOLDER):
        path = os.path.join(UPLOAD_FOLDER, filename)
        size = round(os.path.getsize(path) / 1024, 2)
        files.append({"name": filename, "size": size})
    return jsonify({"files": files})

@app.route('/uploads/<path:filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/delete-file/<filename>', methods=['DELETE'])
def delete_file(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
        return jsonify({"message": f"🗑️ Deleted: {filename}"}), 200
    return jsonify({"message": "❌ File not found."}), 404

@app.route('/send-file-to-telegram', methods=['POST'])
def send_file_to_telegram():
    data = request.get_json()
    filename = data.get("filename")

    if not filename:
        return jsonify({"message": "❌ No filename provided."}), 400

    file_path = os.path.join(UPLOAD_FOLDER, filename)

    if not os.path.exists(file_path):
        return jsonify({"message": "❌ File not found."}), 404

    with open(file_path, 'rb') as f:
        files = {'document': f}
        response = requests.post(f"{TELEGRAM_API_URL}/sendDocument?chat_id={CHAT_ID}", files=files)

    if response.status_code == 200:
        return jsonify({"message": f"✅ Sent {filename} to Telegram"}), 200
    else:
        return jsonify({"message": f"❌ Failed to send {filename}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
