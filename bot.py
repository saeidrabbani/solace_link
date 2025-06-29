from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

latest_message = {"text": "", "files": []}


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if "message" in data:
        message = data["message"]
        if "text" in message:
            latest_message["text"] = message["text"]
            latest_message["files"] = []
        elif "document" in message:
            file_id = message["document"]["file_id"]
            file_name = message["document"]["file_name"]

            file_info_res = requests.get(f"{BASE_URL}/getFile?file_id={file_id}").json()
            if "result" not in file_info_res:
                return "Error getting file info", 500

            file_path = file_info_res["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
            file_data = requests.get(file_url).content

            file_save_path = os.path.join(UPLOAD_FOLDER, file_name)
            with open(file_save_path, "wb") as f:
                f.write(file_data)

            latest_message["text"] = f"📂 File '{file_name}' saved to Solace Portal"
            latest_message["files"] = [{"name": file_name, "size": round(len(file_data)/1024, 2)}]

    return jsonify(success=True)


@app.route("/latest-message", methods=["GET"])
def get_latest_message():
    return jsonify(latest_message)


@app.route("/list-files", methods=["GET"])
def list_files():
    files = []
    for filename in os.listdir(UPLOAD_FOLDER):
        path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(path):
            size_kb = round(os.path.getsize(path) / 1024, 2)
            files.append({"name": filename, "size": size_kb})
    return jsonify({"files": files})


@app.route("/uploads/<filename>", methods=["GET"])
def get_file(filename):
    from flask import send_from_directory
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/delete-file/<filename>", methods=["DELETE"])
def delete_file(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "File not found"}), 404


@app.route("/")
def home():
    return "SolaceBot is running."


if __name__ == "__main__":
    app.run(debug=True)
