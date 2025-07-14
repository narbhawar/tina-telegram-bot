
from flask import Flask, request, jsonify
import requests
import pymongo
import os
from datetime import datetime, timedelta
from bson.objectid import ObjectId

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN") or "7590159969:AAF-8yxRGWbFX7a_Zt7o6bfMUWGlRZvSF7w"
MONGO_URI = os.getenv("MONGO_URI") or "mongodb+srv://Tina:tina123@clustertina.nntbqqx.mongodb.net/?retryWrites=true&w=majority&appName=Clustertina"

mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client["tina"]
drops = db["drops"]
users = db["users"]
sent_log = db["sent"]

@app.route("/admin/analytics")
def analytics():
    total_users = users.count_documents({})
    total_drops = drops.count_documents({})
    total_sent = sent_log.count_documents({})

    today = datetime.utcnow()
    graph = []
    for i in range(7):
        day = today - timedelta(days=6 - i)
        day_start = datetime(day.year, day.month, day.day)
        day_end = day_start + timedelta(days=1)
        count = sent_log.count_documents({"timestamp": {"$gte": day_start, "$lt": day_end}})
        graph.append({"date": day.strftime("%Y-%m-%d"), "sent": count})

    return jsonify({
        "totalUsers": total_users,
        "totalDrops": total_drops,
        "totalSent": total_sent,
        "engagementGraph": graph
    })

@app.route("/admin/push_drop", methods=["POST"])
def push_drop():
    data = request.json
    user_id = data.get("user_id")
    drop_id = data.get("drop_id")

    if not user_id or not drop_id:
        return jsonify({"error": "Missing user_id or drop_id"}), 400

    drop = drops.find_one({"_id": ObjectId(drop_id)})
    if not drop:
        return jsonify({"error": "Drop not found"}), 404

    result = send_telegram(user_id, drop)
    sent_log.insert_one({"user_id": user_id, "drop_id": drop_id, "timestamp": datetime.utcnow()})
    return jsonify({"status": "sent", "response": result})

def send_telegram(user_id, drop):
    if drop["type"] == "text":
        return requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
            "chat_id": user_id,
            "text": drop.get("caption", "")
        }).json()
    elif drop["type"] == "image":
        return requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", json={
            "chat_id": user_id,
            "photo": drop.get("file_url", ""),
            "caption": drop.get("caption", "")
        }).json()
    elif drop["type"] == "voice":
        return requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVoice", json={
            "chat_id": user_id,
            "voice": drop.get("file_url", "")
        }).json()
    else:
        return {"error": "unsupported drop type"}

@app.route(f"/webhook/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    payload = request.json
    user_id = payload["message"]["from"]["id"]
    msg = payload["message"].get("text", "")

    users.update_one({"user_id": user_id}, {"$setOnInsert": {"user_id": user_id}}, upsert=True)

    if msg.lower() == "hi":
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
            "chat_id": user_id,
            "text": "Hi! You’re connected to Tina ✨"
        })

    return jsonify(ok=True)

@app.route("/")
def home():
    return "Tina Telegram Bot is running!"

if __name__ == '__main__':
    app.run(debug=True)
