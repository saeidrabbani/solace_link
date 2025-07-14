from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os
import traceback
import sqlite3

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "7816762363:AAEk86WceNctBS-Kj3deftYqaD0kmb543AA"
CHAT_ID = "253893212"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
UPLOAD_FOLDER = "uploads"
LOG_FILE = "conversation_log.txt"
DB_PATH = "conversation.db"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- DATABASE SETUP ---
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        direction TEXT,
        content TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()
conn.close()

# --- ROUTES ---

@app.route('/')
def home():
    return "✅ Solace Bot Running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if 'message' in data:
        message = data['message']
        chat_id = message['chat']['id']

        if 'text' in message:
            text = message['text']
            save_message('incoming', text)

            requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": f"🌟 Received: {text}"
            })

        elif 'document' in message:
            file_id = message['document']['file_id']
            file_name = message['document']['file_name']
            file_info = requests.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}").json()
            if 'result' in file_info:
                file_path = file_info['result']['file_path']
                file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                file_data = requests.get(file_url)
                with open(os.path.join(UPLOAD_FOLDER, file_name), 'wb') as f:
                    f.write(file_data.content)

                save_message('incoming', f"[File] {file_name}")

                requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": f"✅ File saved: {file_name}"
                })
    return '', 200

@app.route('/latest-message', methods=['GET'])
def latest_message():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT content FROM messages ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    return jsonify({"message": row[0] if row else ""})

@app.route('/send-text', methods=['POST'])
def send_text():
    try:
        data = request.get_json()
        text = data.get("message", "")
        if not text:
            return jsonify({"message": "❌ No message provided."}), 400

        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
            "chat_id": CHAT_ID,
            "text": text
        })

        save_message('outgoing', text)
        return jsonify({"message": "✅ Message sent."}), 200

    except Exception as e:
        return jsonify({"message": "❌ Failed to send message.", "error": str(e)}), 500

@app.route('/upload-file', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"message": "❌ No file uploaded."}), 400
    file = request.files['file']
    filename = file.filename
    file.save(os.path.join(UPLOAD_FOLDER, filename))
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

    try:
        with open(file_path, 'rb') as f:
            response = requests.post(
                f"{TELEGRAM_API_URL}/sendDocument",
                data={"chat_id": CHAT_ID},
                files={"document": f}
            )
        if response.status_code == 200:
            save_message('outgoing', f"[File] {filename}")
            return jsonify({"message": f"✅ Sent {filename} to Telegram"}), 200
        else:
            return jsonify({"message": f"❌ Failed to send {filename}", "details": response.text}), 500
    except Exception as e:
        return jsonify({
            "message": "❌ Error sending file",
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500

# --- UTIL ---
def save_message(direction, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO messages (direction, content) VALUES (?, ?)", (direction, content))
    conn.commit()
    conn.close()

@app.route('/all-messages', methods=['GET'])
def all_messages():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, direction, content, timestamp FROM messages ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    messages = [
        {"id": row[0], "direction": row[1], "content": row[2], "timestamp": row[3]}
        for row in rows
    ]
    return jsonify({"messages": messages})

@app.route('/export-messages', methods=['GET'])
def export_messages():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT direction, content, timestamp FROM messages ORDER BY id")
        rows = c.fetchall()
        conn.close()

        lines = [f"[{row[2]}] {row[0]}: {row[1]}" for row in rows]
        content = "\n".join(lines)

        export_path = os.path.join(UPLOAD_FOLDER, "solace_memory_export.txt")
        with open(export_path, "w", encoding="utf-8") as f:
            f.write(content)

        return jsonify({"message": "✅ Exported to solace_memory_export.txt"}), 200
    except Exception as e:
        return jsonify({
            "message": "❌ Failed to export messages",
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
