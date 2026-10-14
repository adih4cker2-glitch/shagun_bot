import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

# Verify Token jo tum Meta Dashboard mein daloge
VERIFY_TOKEN = "shagun_secret_token"
# Apni Instagram/Facebook Page ki Permanent Access Token yahan daalna
PAGE_ACCESS_TOKEN = os.environ.get("IGAAULAYIpL51BZAFpyZAlVBcDJ0bURYQzBFazdvQ2h4QXZAnYTF1UVEzR3liNVFUblZAVT0p1NGZAVN0diMlpXZAlNTNS1RallGMUI1UklfbmNTLUx0VDM5RVFfdDdod3JxVmwwWXpQaGtyMi1RdE1HWjAyZA1phYVhXNlZAnak5qaUxpYwZDZD")


@app.route("/", methods=["GET"])
def home():
  return "Hello from Shagun Bot Server"


# 1. Webhook Verification (Meta setup ke liye)
@app.route("/webhook", methods=["GET"])
def verify_webhook():
  mode = request.args.get("hub.mode")
  token = request.args.get("hub.verify_token")
  challenge = request.args.get("hub.challenge")

  if mode and token:
    if mode == "subscribe" and token == VERIFY_TOKEN:
      print("WEBHOOK_VERIFIED")
      return challenge, 200
    else:
      return "Verification failed", 403
  return "Hello World", 200


# 2. Incoming Messages Handle karne ke liye
@app.route("/webhook", methods=["POST"])
def handle_webhook():
  data = request.get_json()

  if data.get("object") == "instagram":
    for entry in data.get("entry", []):
      for messaging in entry.get("messaging", []):
        sender_id = messaging.get("sender", {}).get("id")
        message_text = messaging.get("message", {}).get("text")

        if message_id_text := message_text:
          print(f"Message aaya from {sender_id}: {message_text}")
          # Yahan AI ka response generate karke reply bhejne ka function call hoga
          send_instagram_message(
              sender_id, f"Tune kaha: {message_text}"
          )  # Example reply

    return jsonify({"status": "EVENT_RECEIVED"}), 200
  return jsonify({"status": "not found"}), 404


def send_instagram_message(recipient_id, message_text):
  url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
  payload = {
      "recipient": {"id": recipient_id},
      "message": {"text": message_text},
  }
  response = requests.post(url, json=payload)
  return response.json()


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=10000)
  