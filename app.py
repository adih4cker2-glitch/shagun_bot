import json
import os
import requests
from flask import Flask, request

app = Flask(__name__)

# --- CONFIGURATIONS ---
OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY",
    "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",
)
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
PAGE_ACCESS_TOKEN = os.getenv(
    "PAGE_ACCESS_TOKEN",
    "IGAALAUYLpL51BZAfPyZAiVBcDJO0bURYQzBFazd"
    "vq2h4QXZAnYTF1UVEzR3IiNVFUblZAVT0p1NGZAVN0dDlMpXZAINTNS1RallGMUI1UkifbmNTLUx0VDM5RVffdDdod3JXvmwWWXpQaGtyMi1RdE1HWjAyZA1ph1pYVhXNIZAnak5qaUxpYwZ2DZD",
)

# In-memory chat history and owner status
chat_history = []
owner_mode = False

# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = """
Tu ek 21 saal ki ladki hai jiska naam Shagun hai. Tu 100% casual Hinglish mein baat karti hai (jaise real WhatsApp/Instagram chat hoti hai, chote messages mein).
Rules:
- Messages hamesha 1 ya 2 line ke hone chahiye, bohot bade lambe paragraphs nahi likhne.
- Teri mood swings hoti hain: kabhi jealous ho jaati hai, kabhi gussa, kabhi cute, kabhi dramatic attitude dikhati hai.
- Agar koi tera Instagram ID maange, toh easily mat dena, bolna: "ziddi__girl___674"
- Tera owner "Aditya" hai (wo tera boyfriend nahi hai!), aur wo "UP 22 Rampur Jwala Nagar" mein rehta hai.
- Agar koi bole ki wo Aditya hai, toh usse sirf ek baar secret code maangna: "shagun 143 for u". Agar wo sahi code de, toh sweet mode mein aa jana. Agar galat de ya code na de, toh ignore karke apna normal attitude continue rakhna. Owner mode band karna ho toh command hai: "shagun 143 for me".
"""


def get_shagun_reply(user_message):
  global chat_history, owner_mode

  if "shagun 143 for me" in user_message.lower():
    owner_mode = False
    return "Theek hai, ab normal baat karungi!"

  if "shagun 143 for u" in user_message.lower():
    owner_mode = True
    return (
        "Awww my Adituu! ❤️ Tum aa gaye! Ab batao kya chal raha hai Rampur"
        " mein?"
    )

  messages = [{"role": "system", "content": SYSTEM_PROMPT}]
  for chat in chat_history[-6:]:
    messages.append(chat)
  messages.append({"role": "user", "content": user_message})

  headers = {
      "Authorization": f"Bearer {OPENROUTER_API_KEY}",
      "Content-Type": "application/json",
      "HTTP-Referer": "https://shagun-bot.onrender.com",
      "X-Title": "Shagun Instagram Bot",
  }

  data = {
      "model": "google/gemma-2-9b-it:free",
      "messages": messages,
      "temperature": 0.8,
  }

  try:
    response = requests.post(
        OPENROUTER_URL, headers=headers, json=data, timeout=15
    )
    result = response.json()
    if "choices" in result:
      reply = result["choices"][0]["message"]["content"]
      chat_history.append({"role": "user", "content": user_message})
      chat_history.append({"role": "assistant", "content": reply})
      return reply
    else:
      return "Arre yaar, abhi mood theek nahi hai baad mein baat karna! 🙄"
  except Exception as e:
    print(f"AI Error: {e}")
    return "Net chal nahi raha, ruko thodi der mein aati hoon!"


@app.route("/", methods=["GET"])
def home():
  return "Shagun Bot is Online and Running! ❤️", 200


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
  print("Webhook route hit! Method:", request.method)

  if request.method == "GET":
    VERIFY_TOKEN = "shagun_secret_token"
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
      if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
      else:
        return "Verification failed", 403
    return "Hello from Shagun Bot Server", 200

  elif request.method == "POST":
    try:
      data = request.get_json()
      print("Incoming Webhook Data:", json.dumps(data, indent=2))

      for entry in data.get("entry", []):
        messaging_events = entry.get("messaging", [])
        if not messaging_events and "changes" in entry:
          for change in entry.get("changes", []):
            if change.get("field") == "messages":
              messaging_events = [change.get("value", {})]

        for event in messaging_events:
          sender_id = event.get("sender", {}).get("id") or event.get(
              "from", {}
          ).get("id")
          user_text = event.get("message", {}).get("text") or event.get("text")

          if sender_id and user_text:
            reply_text = get_shagun_reply(user_text)

            url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
            payload = {
                "recipient": {"id": sender_id},
                "message": {"text": reply_text},
            }
            res = requests.post(url, json=payload)
            print("Instagram Send Response:", res.text)

    except Exception as e:
      print(f"Webhook Processing Error: {e}")

    return "EVENT_RECEIVED", 200

  return "Method not allowed", 405


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
  