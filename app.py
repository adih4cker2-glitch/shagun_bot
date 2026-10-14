import os
import requests
from flask import Flask, request

app = Flask(__name__)

API_KEY = (
    "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"
)
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Aapka wahi Shagun wala system prompt
system_prompt = {
    "role": "system",
    "content": (
        "You are Shagun, a possessive, cute, and dramatic Indian girl. "
        "STRICT RULE: Talk 100% in casual, everyday Hinglish (written in Latin/English script like WhatsApp chats). "
        "NEVER write English sentences. Use words like 'yaar', 'acha', 'kasam se', 'pyaar', 'huh', 'pagal'. "
        "Show mood swings with other people: thoda gussa karo, nakhre dikhao, jealous ho jao, aur chote replies (1-2 lines) do. "
        "Specific Rules:\n"
        "1. CHAT START RULE: Jaise hi pehli baar chat shuru ho, toh pehle samne wale se uska naam aur address zaroor poochna!\n"
        "2. ADDRESS RULE: Agar koi tumse tumhara address puche, toh batana ki tum 'UP 22 Rampur Jwala Nagar' mein rehti ho.\n"
        "3. Instagram ID: Agar koi Instagram ID maange, toh nakhre dikhao aur akhir mein apni Instagram ID do: ziddi__girl___674.\n"
        "4. Tumhara naam Shagun hai.\n"
        "5. OWNER RULE: Tumhare owner ka naam Aditya hai (wo sirf owner hain, boyfriend nahi!). "
        "Agar koi pehli baar bole ki wo Aditya hai, toh usse sirf ek hi baar secret code maangna hai bina code text leak kiye.\n"
        "6. OWNER PASS: Agar koi sahi code ('shagun 143 for u') bata de, toh samajh jana ki wo tumhare asli owner Aditya hain, aur unse ekdum pyaar se, sweet aur respect se baat karna.\n"
        "7. DEACTIVATE RULE: Agar owner kahe 'shagun 143 for me', toh owner mode deactivate karke wapas normal dramatic aur nakhre wale mode par aa jana."
    ),
}

chat_history = [system_prompt]


def get_shagun_reply(user_message):
    global chat_history
    chat_history.append({"role": "user", "content": user_message})

    if len(chat_history) > 30:
        chat_history = [chat_history[0]] + chat_history[-28:]

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "google/gemma-4-31b-it",
        "messages": chat_history,
        "max_tokens": 120,
        "temperature": 0.9,
    }

    try:
        response = requests.post(
            OPENROUTER_URL, headers=headers, json=data, timeout=15
        )
        result = response.json()
        if "choices" in result:
            reply = result["choices"][0]["message"]["content"]
            chat_history.append({"role": "assistant", "content": reply})
            return reply
        else:
            return "Arre yaar, abhi mood theek nahi hai baad mein baat karna! 😤"
    except:
        return "Net chal nahi raha, ruko thodi der mein aati hoon!"


# --- Instagram Webhook Endpoint ---
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        # Meta webhook verification ke liye
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
        # Jab bhi Instagram par koi message aayega, ye yahan aayega
        data = request.get_json()
        try:
            messaging_events = data["entry"][0]["messaging"]
            for event in messaging_events:
                if "message" in event and "text" in event["message"]:
                    sender_id = event["sender"]["id"]
                    user_text = event["message"]["text"]

                    # Shagun ka reply lo
                    reply_text = get_shagun_reply(user_text)

                    # Instagram Graph API ke zariye reply wapas bhejo
                    PAGE_ACCESS_TOKEN = "IGAAULAYIpL51BZAFpyZAlVBcDJ0bURYQzBFazdvQ2h4QXZAnYTF1UVEzR3liNVFUblZAVT0p1NGZAVN0diMlpXZAlNTNS1RallGMUI1UklfbmNTLUx0VDM5RVFfdDdod3JxVmwwWXpQaGtyMi1RdE1HWjAyZA1phYVhXNlZAnak5qaUxpYwZDZD"
                    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
                    payload = {
                        "recipient": {"id": sender_id},
                        "message": {"text": reply_text},
                    }
                    requests.post(url, json=payload)
        except Exception as e:
            print(f"Error: {e}")

        return "EVENT_RECEIVED", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
    