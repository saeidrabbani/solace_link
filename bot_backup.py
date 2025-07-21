from flask import Flask, send_file, jsonify
import gspread
import csv
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# === CONFIG ===
SPREADSHEET_ID = "1GFm1IdDYw_jcPw2azflRK0hux0UKWCmqLekQJkezoac"
SHEET_NAME = "Sheet1"
CREDENTIALS_PATH = "/etc/secrets/credentials.json"
CSV_FILENAME = "solace_backup.csv"

@app.route("/download-csv", methods=["GET"])
def download_csv():
    try:
        # 1. Google Sheets → Fetch
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        data = sheet.get_all_values()

        # 2. Save as CSV
        with open(CSV_FILENAME, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(data)

        # 3. Download to user
        return send_file(CSV_FILENAME, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
