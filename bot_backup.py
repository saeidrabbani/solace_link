import gspread
import csv
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os

def backup_sheet_to_drive():
    try:
        # 1. Load Google Sheets
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key("1GFm1IdDYw_jcPw2azflRK0hux0UKWCmqLekQJkezoac").worksheet("Sheet1")
        data = sheet.get_all_values()

        # 2. Save CSV locally
        filename = "solace_backup.csv"
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(data)

        # 3. Upload to Google Drive
        gauth = GoogleAuth()
        gauth.LoadCredentialsFile("credentials.json")
        if gauth.credentials is None:
            gauth.LocalWebserverAuth()
        elif gauth.access_token_expired:
            gauth.Refresh()
        else:
            gauth.Authorize()
        gauth.SaveCredentialsFile("credentials.json")

        drive = GoogleDrive(gauth)

        # Check if file already exists in Drive folder
        folder_id = "1tw3vTFE4g1oefRSPPta459IxTxZTKbW5"  # Your shared folder
        file_list = drive.ListFile({
            'q': f"'{folder_id}' in parents and trashed=false"
        }).GetList()

        for file in file_list:
            if file['title'] == filename:
                file.Delete()

        # Upload new file
        file_drive = drive.CreateFile({'title': filename, 'parents': [{"id": folder_id}]})
        file_drive.SetContentFile(filename)
        file_drive.Upload()

        print("✅ Backup uploaded to Google Drive.")

    except Exception as e:
        print("❌ Backup failed:", e)

# Manual Run
if __name__ == "__main__":
    backup_sheet_to_drive()
