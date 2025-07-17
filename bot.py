import os
import sqlite3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import requests
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Save to Google Sheets
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

# Telegram setup
TELEGRAM_TOKEN = "7816762363:AAEk86WceNctBS-Kj3deftYqaD0kmb543AA"
CHAT_ID = "253893212"
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
TELEGRAM_FILE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"

# SQLite DB setup
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

    tg_response = requests.post(TELEGRAM_URL, json={"chat_id": CHAT_ID, "text": msg})
    if tg_response.status_code != 200:
        return jsonify({"error": "Failed to send to Telegram"}), 500

    save_message("to_telegram", msg)
    save_to_sheet("to_telegram", msg)
    return jsonify({"message": f"✅ Sent to Telegram: {msg}"}), 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    msg = data.get("message", {}).get("text")
    if msg:
        save_message("from_telegram", msg)
        save_to_sheet("from_telegram", msg)

    doc = data.get("message", {}).get("document")
    if doc:
        file_id = doc["file_id"]
        file_name = doc["file_name"]
        file_url_resp = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}")
        file_path = file_url_resp.json()["result"]["file_path"]
        file_data = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}")

        save_path = os.path.join(app.config["UPLOAD_FOLDER"], file_name)
        with open(save_path, "wb") as f:
            f.write(file_data.content)

        save_to_sheet("file_from_telegram", file_name)

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

    save_to_sheet("upload_from_site", filename)
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

        save_to_sheet("file_to_telegram", filename)
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

import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

def backup_sheet_to_drive():
    try:
        # Read from Google Sheets
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = service_account.Credentials.from_service_account_file("credentials.json", scopes=scope)
        
        gc = gspread.authorize(creds)
        sheet = gc.open("solace_memory_log").sheet1
        data = sheet.get_all_values()

        # Save as CSV locally
        df = pd.DataFrame(data[1:], columns=data[0])  # First row as headers
        df.to_csv("solace_backup.csv", index=False)

        # Upload to Drive
        service = build("drive", "v3", credentials=creds)
        file_metadata = {
            "name": "solace_backup.csv",
            "parents": ["1tw3vTFE4g1oefRSPPta459IxTxZTKbW5"]
        }
        media = MediaFileUpload("solace_backup.csv", mimetype="text/csv")
        
        # Check if file already exists
        query = f"name='solace_backup.csv' and '{file_metadata['parents'][0]}' in parents"
        results = service.files().list(q=query, fields="files(id)").execute()
        files = results.get("files", [])
        if files:
            # Update existing file
            file_id = files[0]["id"]
            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            # Upload new file
            service.files().create(body=file_metadata, media_body=media, fields="id").execute()

        print("✅ Backup successful and uploaded to Drive.")
    except Exception as e:
        print("❌ Backup failed:", e)
