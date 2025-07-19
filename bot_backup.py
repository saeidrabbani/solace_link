from flask import Flask, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import csv
import os
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

import logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

@app.route("/backup-now", methods=["POST"])
def backup_now():
    try:
        print("🔄 Starting backup process...")

        # Step 1: Load credentials for gspread
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_path = "/etc/secrets/credentials.json"
        print(f"🔐 Loading credentials from: {creds_path}")
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        client = gspread.authorize(creds)

        # Step 2: Open Google Sheet
        sheet = client.open("solace_memory_log").sheet1
        print("📄 Google Sheet loaded successfully.")

        # Step 3: Export to CSV
        records = sheet.get_all_values()
        csv_filename = "solace_memory_backup.csv"
        with open(csv_filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(records)
        print(f"✅ CSV exported: {csv_filename}")

        # Step 4: Upload to Google Drive
        drive_creds = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=drive_creds)

        # Find the folder ID
        folder_id = "1tw3vTFE4g1oefRSPPta459IxTxZTKbW5"
        file_metadata = {
            "name": "solace_memory_backup.csv",
            "parents": [folder_id],
            "mimeType": "application/vnd.google-apps.spreadsheet"
        }

        # First delete existing file with same name (optional)
        print("🔎 Checking for old backups to delete...")
        existing_files = service.files().list(
            q=f"name='solace_memory_backup.csv' and '{folder_id}' in parents and trashed = false",
            fields="files(id, name)"
        ).execute().get("files", [])

        for f in existing_files:
            print(f"🗑 Deleting old file: {f['name']} ({f['id']})")
            service.files().delete(fileId=f["id"]).execute()

        # Upload new CSV
        media = MediaFileUpload(csv_filename, mimetype='text/csv')
        uploaded = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        print(f"🚀 Uploaded new file to Drive with ID: {uploaded.get('id')}")

        return jsonify({"status": "Backup complete"})
    
  except Exception as e:
    import traceback
    error_message = traceback.format_exc()
    print("❌ Backup failed:\n", error_message)

    # Save error to a log file
    with open("error_log.txt", "w") as f:
        f.write(error_message)

    return jsonify({"error": "Backup failed. Check error_log.txt"}), 500


