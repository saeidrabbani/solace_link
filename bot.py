from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "7816762363:AAEk86WceNctBS-Kj3deftYqaD0kmb543AA"
CHAT_ID = "589089595"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/send-file-to-telegram', methods=['POST'])
def send_file_to_telegram():
    data = request.get_json()
    filename = data.get("filename")
    if not filename:
        return jsonify({"message": "❌ No filename provided."}), 400

    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(file_path):
        return jsonify({"message": "❌ File not found."}), 404

    try:
        with open(file_path, 'rb') as file_to_send:
            response = requests.post(
                f"{TELEGRAM_API_URL}/sendDocument",
                data={"chat_id": CHAT_ID},
                files={"document": file_to_send}
            )
        if response.status_code == 200:
            return jsonify({"message": f"✅ Sent {filename} to Telegram"}), 200
        else:
            return jsonify({
                "message": f"❌ Failed to send {filename}",
                "details": response.text
            }), 500
    except Exception as e:
        return jsonify({"message": f"❌ Error sending file: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

