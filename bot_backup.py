from flask import Flask, jsonify
import gspread
import csv
import os
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

app = Flask(__name__)

def backup_sheet_to_drive():
    try:
        # Load Google Sheet
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key("1GFm1IdDYw_jcPw2azflRK0hux0UKWCmqLekQJkezoac").worksheet("Sheet1")
        data = sheet.get_all_values()

        # Save to CSV
        filename = "solace_backup.csv"
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(data)

        # Upload to Google Drive using googleapiclient
        folder_id = "1tw3vTFE4g1oefRSPPta459IxTxZTKbW5"
        creds_drive = service_account.Credentials.from_service_account_file(
            "credentials.json",
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        service = build("drive", "v3", credentials=creds_drive)

        # Delete old file if exists
        results = service.files().list(q=f"'{folder_id}' in parents and name='{filename}' and trashed=false").execute()
        for file in results.get("files", []):
            service.files().delete(fileId=file["id"]).execute()

        # Upload new file
        file_metadata = {
            "name": filename,
            "parents": [folder_id]
        }
        media = MediaFileUpload(filename, mimetype="text/csv")
        service.files().create(body=file_metadata, media_body=media, fields="id").execute()

        return True, "✅ Backup uploaded to Google Drive."

    except Exception as e:
        return False, f"❌ Backup failed: {str(e)}"

@app.route("/backup-now", methods=["POST"])
def trigger_backup():
    success, message = backup_sheet_to_drive()
    return jsonify({"status": message}), 200 if success else 500

if __name__ == "__main__":
    app.run(debug=True)
