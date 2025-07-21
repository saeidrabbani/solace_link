from flask import Flask, jsonify, send_file
import gspread
import csv
import os
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

app = Flask(__name__)  # ✅ faghat inja

# CONFIG
SPREADSHEET_ID = "1GFm1IdDYw_jcPw2azflRK0hux0UKWCmqLekQJkezoac"
SHEET_NAME = "Sheet1"
DRIVE_FOLDER_ID = "1tw3vTFE4g1oefRSPPta459IxTxZTKbW5"
CREDENTIALS_PATH = "/etc/secrets/credentials.json"
CSV_FILENAME = "solace_backup.csv"
LOG_FILE = "static/uploads/backup_log.txt"

@app.route("/download-csv", methods=["GET"])
def download_csv():
    try:
        return send_file(CSV_FILENAME, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.utcnow()}] {msg}\n")

def backup_sheet_to_drive():
    try:
        log("Starting backup process...")

        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        data = sheet.get_all_values()

        log(f"Fetched {len(data)} rows from Google Sheet.")

        with open(CSV_FILENAME, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(data)

        log(f"Saved CSV file: {CSV_FILENAME}")

        drive_creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        service = build("drive", "v3", credentials=drive_creds)

        query = f"'{DRIVE_FOLDER_ID}' in parents and name='{CSV_FILENAME}' and trashed=false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get("files", [])

        for file in files:
            service.files().delete(fileId=file["id"]).execute()
            log(f"Deleted old file in Drive: {file['name']}")

        file_metadata = {
            "name": CSV_FILENAME,
            "parents": [DRIVE_FOLDER_ID]
        }
        media = MediaFileUpload(CSV_FILENAME, mimetype="text/csv")
        service.files().create(body=file_metadata, media_body=media, fields="id").execute()

        log("✅ Upload to Drive successful.")
        return True, "✅ Backup uploaded to Google Drive."

    except Exception as e:
        log(f"❌ Error: {str(e)}")
        return False, f"❌ Backup failed: {str(e)}"

@app.route("/backup-now", methods=["POST"])
def trigger_backup():
    success, message = backup_sheet_to_drive()
    return jsonify({"status": message}), 200 if success else 500

if __name__ == "__main__":
    app.run(debug=True)
