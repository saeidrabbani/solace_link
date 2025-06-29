from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "7816762363:AAEk86WceNctBS-Kj3deftYqaD0kmb543AA"
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

        if text:
            with open(LOG_FILE, "a", encoding="utf-8") as file:
                file.write(text + "\n")

            requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": f"🌟 Received: {text}"
            })

        # ✅ Handle file upload from Telegram
        if 'document' in data['message']:
            file_id = data['message']['document']['file_id']
            file_name = data['message']['document']['file_name']
            
            # Get file info from Telegram
            file_info_res = requests.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}").json()
            file_path = file_info_res.get("result", {}).get("file_path")

            if not file_path:
                print("❌ file_path not found:", file_info_res)
                return '', 200  # Avoid crash if something goes wrong

            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            file_data = requests.get(file_url)

            save_path = os.path.join(UPLOAD_FOLDER, file_name)
            with open(save_path, "wb") as f:
                f.write(file_data.content)

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
    files = []
    for filename in os.listdir(UPLOAD_FOLDER):
        path = os.path.join(UPLOAD_FOLDER, filename)
        size_mb = round(os.path.getsize(path) / 1024 / 1024, 2)
        files.append({"name": filename, "size": size_mb})
    return jsonify({"files": files})

@app.route('/delete-file', methods=['POST'])
def delete_file():
    data = request.json
    filename = data.get("filename", "")
    path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
        return jsonify({"message": f"🗑️ Deleted: {filename}"})
    else:
        return jsonify({"message": "❌ File not found."}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
