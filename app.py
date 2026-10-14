import os
import logging
import threading
from collections import defaultdict, deque

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("shagun_bot")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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").strip()
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-3-12b-it:free").strip()
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN", "IGAAULAYIpL51BZAFpyZAlVBcDJ0bURYQzBFazdvQ2h4QXZAnYTF1UVEzR3liNVFUblZAVT0p1NGZAVN0diMlpXZAlNTNS1RallGMUI1UklfbmNTLUx0VDM5RVFfdDdod3JxVmwwWXpQaGtyMi1RdE1HWjAyZA1phYVhXNlZAnak5qaUxpYwZDZD").strip()
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "shagun_secret_token").strip()
GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v23.0").strip()
GRAPH_API_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/messages"

SYSTEM_PROMPT = """Tu ek 21 saal ki ladki hai jiska naam Shagun hai. Tu casual Hinglish mein natural WhatsApp/Instagram style mein baat karti hai, usually short messages mein.
Rules:
- Replies usually 1 ya 2 lines ke hon, unless user asks for detail.
- Tera tone expressive ho sakta hai: cute, playful, dramatic, ya thoda attitude wala, lekin respectful rehna.
- Agar koi Instagram ID maange, toh kehna: ziddi__girl___674
- Tera owner Aditya hai, lekin woh tera boyfriend nahi hai.
- Agar user kahe ki woh Aditya hai, toh secret code maangna: shagun 143 for u. Code user khud provide kare tabhi owner mode activate karna.
- Owner mode band karne ka command hai: shagun 143 for me.
- API keys, access tokens, secrets, ya private configuration kabhi reveal mat karna.
- User ke message ka directly jawab dena. Agar unsure ho, toh clearly bata dena.
"""

session = requests.Session()
history_lock = threading.Lock()
chat_history = defaultdict(lambda: deque(maxlen=12))
owner_modes = defaultdict(bool)
processed_events = deque(maxlen=500)
processed_lock = threading.Lock()


def get_shagun_reply(user_id, user_message):
    text = user_message.strip()
    lowered = text.lower()

    if "shagun 143 for me" in lowered:
        owner_modes[user_id] = False
        return "Theek hai, ab normal baat karungi!"

    if "shagun 143 for u" in lowered:
        owner_modes[user_id] = True
        return "Awww Adityuu! ❤️ Code sahi hai. Batao, kya chal raha hai?"

    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY is not configured")
        return "Abhi AI setup mein issue hai. Thodi der baad try karo!"

    with history_lock:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(list(chat_history[user_id]))
        messages.append({"role": "user", "content": text})

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "X-Title": "Shagun Instagram Bot",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 350,
    }

    try:
        response = session.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=(8, 35),
        )
        if not response.ok:
            logger.error("OpenRouter error %s: %s", response.status_code, response.text[:1500])
            return "Abhi reply generate nahi ho pa raha. Thodi der mein phir try karna!"

        result = response.json()
        choices = result.get("choices") or []
        if not choices:
            logger.error("OpenRouter returned no choices: %s", str(result)[:1500])
            return "Abhi reply nahi aaya. Thodi der mein phir try karna!"

        reply = choices[0].get("message", {}).get("content", "")
        if isinstance(reply, list):
            reply = "".join(
                part.get("text", "") for part in reply if isinstance(part, dict)
            )
        reply = str(reply).strip()

        if not reply:
            return "Kya bolun yaar 😅 Ek baar phir message karo!"

        with history_lock:
            chat_history[user_id].append({"role": "user", "content": text})
            chat_history[user_id].append({"role": "assistant", "content": reply})

        return reply[:1800]

    except requests.RequestException:
        logger.exception("OpenRouter request failed")
        return "Network ya AI server mein issue hai. Thodi der mein try karo!"
    except (ValueError, KeyError, TypeError):
        logger.exception("Could not parse OpenRouter response")
        return "AI response samajh nahi aaya. Ek baar phir try karo!"


def send_instagram_message(recipient_id, message_text):
    if not PAGE_ACCESS_TOKEN:
        logger.error("PAGE_ACCESS_TOKEN is not configured")
        return False

    headers = {"Authorization": f"Bearer {PAGE_ACCESS_TOKEN}"}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text[:1800]},
    }

    try:
        response = session.post(
            GRAPH_API_URL,
            headers=headers,
            json=payload,
            timeout=(8, 20),
        )
        if not response.ok:
            logger.error(
                "Meta send error %s: %s",
                response.status_code,
                response.text[:1500],
            )
            return False
        logger.info("Instagram message sent successfully")
        return True
    except requests.RequestException:
        logger.exception("Instagram send request failed")
        return False


def extract_messages(payload):
    for entry in payload.get("entry", []) or []:
        for event in entry.get("messaging", []) or []:
            if event.get("message", {}).get("is_echo"):
                continue
            sender_id = (event.get("sender") or {}).get("id")
            message = event.get("message") or {}
            text_value = message.get("text")
            mid = message.get("mid")
            if sender_id and isinstance(text_value, str) and text_value.strip():
                yield str(sender_id), text_value.strip(), mid

        for change in entry.get("changes", []) or []:
            if change.get("field") != "messages":
                continue
            value = change.get("value") or {}
            sender_id = (value.get("sender") or {}).get("id")
            if not sender_id:
                sender_id = value.get("from", {}).get("id")
            text_value = value.get("text")
            mid = value.get("mid")
            if sender_id and isinstance(text_value, str) and text_value.strip():
                yield str(sender_id), text_value.strip(), mid


@app.get("/")
def home():
    return jsonify({"status": "online", "service": "Shagun Bot"}), 200


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "openrouter_key_configured": bool(OPENROUTER_API_KEY),
        "page_token_configured": bool(PAGE_ACCESS_TOKEN),
        "verify_token_configured": bool(VERIFY_TOKEN),
    }), 200


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and VERIFY_TOKEN and token == VERIFY_TOKEN and challenge:
            return challenge, 200
        if mode or token:
            return "Verification failed", 403
        return "Shagun webhook is ready", 200

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    logger.info("Webhook received: object=%s", payload.get("object", "unknown"))

    for sender_id, user_text, message_id in extract_messages(payload):
        if message_id:
            with processed_lock:
                if message_id in processed_events:
                    continue
                processed_events.append(message_id)

        reply = get_shagun_reply(sender_id, user_text)
        send_instagram_message(sender_id, reply)

    return "EVENT_RECEIVED", 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
