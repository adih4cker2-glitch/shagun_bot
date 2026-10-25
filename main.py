#!/usr/bin/env python3
"""JARVIS + AI companion starter for Termux. Configure AI_BASE_URL, AI_API_KEY and AI_MODEL in .env."""
import os, json, datetime, subprocess, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MEMORY_FILE = ROOT / 'memory.json'

def load_env():
    p = ROOT / '.env'
    if p.exists():
        for line in p.read_text(encoding='utf-8').splitlines():
            line=line.strip()
            if not line or line.startswith('#') or '=' not in line: continue
            k,v=line.split('=',1)
            os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))
load_env()

SYSTEM = ("You are Aira, a friendly AI companion and practical JARVIS-style assistant. "
          "Speak naturally in Hindi/Hinglish when the user does. Be warm, respectful, honest that you are an AI, "
          "and concise. Never claim to control phone features unless a command actually succeeded.")

def memory_load():
    try: return json.loads(MEMORY_FILE.read_text(encoding='utf-8'))
    except Exception: return []

def memory_save(msgs):
    MEMORY_FILE.write_text(json.dumps(msgs[-20:], ensure_ascii=False, indent=2), encoding='utf-8')

def speak(text):
    try:
        subprocess.run(['termux-tts-speak', text[:1200]], timeout=30, check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (FileNotFoundError, subprocess.TimeoutExpired): pass

def listen():
    try:
        r = subprocess.run(['termux-speech-to-text'], capture_output=True, text=True, timeout=45)
        return r.stdout.strip() if r.returncode == 0 else ''
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print('Voice input ke liye Termux:API app aur termux-api package install karo.')
        return ''

def local_command(q):
    s=q.lower().strip()
    if s in ('exit','quit','band karo','bye'): return '__EXIT__'
    if any(x in s for x in ('time kya','kitne baje','samay')):
        return 'Abhi time hai ' + datetime.datetime.now().strftime('%I:%M %p')
    if any(x in s for x in ('aaj ki date','date kya','aaj date')):
        return 'Aaj ki date hai ' + datetime.datetime.now().strftime('%d %B %Y')
    if s in ('help','commands','madad'):
        return 'Commands: time kya hai, aaj ki date, /voice, /clear, /exit. Baaki sawalon ke liye .env mein AI API set karo.'
    if s == '/clear':
        memory_save([]); return 'Chat memory clear kar di.'
    return None

def ask_ai(history, user_text):
    base=os.getenv('AI_BASE_URL','').strip().rstrip('/')
    key=os.getenv('AI_API_KEY','').strip()
    model=os.getenv('AI_MODEL','').strip()
    if not (base and key and model):
        return 'AI API abhi set nahi hai. .env.example ko .env banao aur apna API URL, key aur model add karo. Local time/date commands bina API bhi chalte hain.'
    # OpenAI-compatible Chat Completions endpoint
    url=base if base.endswith('/chat/completions') else base + '/chat/completions'
    messages=[{'role':'system','content':SYSTEM}] + history[-12:] + [{'role':'user','content':user_text}]
    body=json.dumps({'model':model,'messages':messages,'temperature':0.8}).encode()
    req=urllib.request.Request(url, data=body, headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=60) as resp: data=json.loads(resp.read().decode())
        return data['choices'][0]['message']['content'].strip()
    except urllib.error.HTTPError as e:
        detail=e.read().decode(errors='replace')[:300]
        return f'API error ({e.code}): {detail}'
    except Exception as e:
        return f'API connect nahi hua: {e}'

def main():
    history=memory_load()
    print('\n🤖 AIRA — JARVIS + AI COMPANION')
    print('Hindi/Hinglish mein baat karo. /voice = bolkar input, /clear = memory clear, /exit = band.\n')
    while True:
        try: q=input('You > ').strip()
        except (EOFError, KeyboardInterrupt): print('\nBye!'); break
        if not q: continue
        if q.lower()=='/voice':
            q=listen()
            if not q: continue
            print('You (voice) >',q)
        if q.lower() in ('/exit','exit','quit','bye','band karo'): print('Aira > Bye! Phir milenge.'); break
        if q.lower()=='/clear':
            memory_save([]); history=[]; print('Aira > Chat memory clear kar di.'); continue
        answer=local_command(q)
        if answer is None: answer=ask_ai(history,q)
        print('\nAira > '+answer+'\n')
        if answer!='__EXIT__' and not q.startswith('/'):
            history.extend([{'role':'user','content':q},{'role':'assistant','content':answer}])
            memory_save(history)
        if os.getenv('VOICE_REPLY','0')=='1': speak(answer)

if __name__=='__main__': main()
