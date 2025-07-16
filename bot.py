import os
import sqlite3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import requests
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def save_to_sheet(direction, message):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key("1GFm1IdDYw_jcPw2azflRK0hux0UKWCmqLekQJkezoac").worksheet("Sheet1")
        sheet.append_row([direction, message, datetime.utcnow().isoformat()])
    except Exception as e:
        print("❌ Sheet Error:", e)



app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Telegram
TELEGRAM_TOKEN = "7816762363:AAEk86WceNctBS-Kj3deftYqaD0kmb543AA"
CHAT_ID = "253893212"
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
TELEGRAM_FILE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"

# DB Setup
DB_FILE = "conversation.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    direction TEXT,
    content TEXT,
    timestamp TEXT
)""")
conn.commit()

def save_message(direction, content):
    cursor.execute("INSERT INTO messages (direction, content, timestamp) VALUES (?, ?, ?)",
                   (direction, content, datetime.utcnow().isoformat()))
    conn.commit()

@app.route("/send-message", methods=["POST"])
def send_message():
    data = request.json
    msg = data.get("message")
    if not msg:
        return jsonify({"error": "No message"}), 400

    # Send to Telegram
    tg_response = requests.post(TELEGRAM_URL, json={"chat_id": CHAT_ID, "text": msg})
    if tg_response.status_code != 200:
        return jsonify({"error": "Failed to send to Telegram"}), 500

    save_message("to_telegram", msg)
    save_to_sheet("to_telegram", msg)

    return jsonify({"message": f"✅ Sent to Telegram: {msg}"}), 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    # Handle text message
    msg = data.get("message", {}).get("text")
    if msg:
        save_message("from_telegram", msg)
        save_to_sheet("from_telegram", msg)


    # Handle document upload
    doc = data.get("message", {}).get("document")
    if doc:
        file_id = doc["file_id"]
        file_name = doc["file_name"]
        file_url_resp = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}")
        file_path = file_url_resp.json()["result"]["file_path"]
        file_data = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}")

        # Save file
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], file_name)
        with open(save_path, "wb") as f:
            f.write(file_data.content)

    return jsonify({"status": "received"}), 200


@app.route("/latest-message", methods=["GET"])
def latest_message():
    cursor.execute("SELECT content FROM messages WHERE direction='from_telegram' ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    message = row[0] if row else "No messages yet"
    return jsonify({"message": message})

@app.route("/upload-file", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No filename"}), 400
    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    return jsonify({"message": f"✅ Uploaded {filename}"}), 200

@app.route("/list-files", methods=["GET"])
def list_files():
    try:
        files = os.listdir(app.config["UPLOAD_FOLDER"])
        file_data = []
        for name in files:
            path = os.path.join(app.config["UPLOAD_FOLDER"], name)
            size_kb = os.path.getsize(path) / 1024
            file_data.append({"name": name, "size": size_kb})
        return jsonify({"files": file_data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/uploads/<filename>")
def get_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/delete-file/<filename>", methods=["DELETE"])
def delete_file(filename):
    try:
        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        os.remove(path)
        return jsonify({"message": f"✅ Deleted {filename}"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/send-file-to-telegram", methods=["POST"])
def send_file_to_telegram():
    data = request.json
    filename = data.get("filename")
    if not filename:
        return jsonify({"error": "No filename provided"}), 400

    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404

    try:
        with open(path, "rb") as f:
            res = requests.post(
                TELEGRAM_FILE_URL,
                data={"chat_id": CHAT_ID},
                files={"document": f}
            )
        if res.status_code != 200:
            return jsonify({"message": "❌ Failed to send file", "details": res.text}), 500
        return jsonify({"message": f"✅ Sent {filename} to Telegram"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/export-messages", methods=["GET"])
def export_messages():
    try:
        cursor.execute("SELECT direction, content, timestamp FROM messages ORDER BY id ASC")
        messages = cursor.fetchall()
        content = "\n".join([f"[{d}] {t}: {c}" for d, c, t in messages])
        with open("solace_messages.txt", "w", encoding="utf-8") as f:
            f.write(content)
        return send_from_directory(".", "solace_messages.txt", as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
