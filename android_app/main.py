# Aira: Kivy Android assistant starter with API settings, avatars, RGB themes and app commands.
# Voice recognition and app intents use Android APIs when available. Background hotword listening is not implemented.
import json, os, threading, urllib.request, urllib.error, urllib.parse, webbrowser
from pathlib import Path
from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import StringProperty, ListProperty, NumericProperty
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.graphics import Color, Ellipse, Line, RoundedRectangle

try:
    from jnius import autoclass
    from android import activity
    ANDROID = True
except Exception:
    ANDROID = False

KV = r'''
#:import dp kivy.metrics.dp
ScreenManager:
    ChatScreen:
    SettingsScreen:
<ChatScreen>:
    name: 'chat'
    BoxLayout:
        orientation: 'vertical'; padding: '12dp'; spacing: '8dp'
        BoxLayout:
            size_hint_y: None; height: '48dp'; spacing: '8dp'
            Label:
                text: app.assistant_name.upper() + '  •  AI ASSISTANT'
                bold: True; font_size: '18sp'
            Button:
                text: '⚙'; size_hint_x: None; width: '48dp'
                on_release: app.root.current = 'settings'
        AvatarWidget:
            id: avatar
            face_type: app.face_type
            glow_color: app.rgb_color
            size_hint_y: None; height: '170dp'
        Label:
            text: 'Voice commands: YouTube song, WhatsApp, open app, or chat'
            size_hint_y: None; height: '32dp'; font_size: '12sp'
        ScrollView:
            Label:
                id: chatlog
                text: root.chat_text
                size_hint_y: None; height: max(self.texture_size[1] + dp(24), dp(120))
                text_size: self.width, None; halign: 'left'; valign: 'top'; markup: True
        BoxLayout:
            size_hint_y: None; height: '46dp'; spacing: '6dp'
            TextInput:
                id: prompt; hint_text: 'Bolo ya type karo…'; multiline: False
                on_text_validate: root.send_message()
            Button:
                text: 'Send'; size_hint_x: None; width: '72dp'
                on_release: root.send_message()
        BoxLayout:
            size_hint_y: None; height: '48dp'; spacing: '6dp'
            Button:
                text: '🎙 Speak'; on_release: root.listen_once()
            Button:
                text: '▶ YouTube'; on_release: root.run_command('youtube song search')
            Button:
                text: 'WhatsApp'; on_release: root.run_command('open whatsapp')
<SettingsScreen>:
    name: 'settings'
    BoxLayout:
        orientation: 'vertical'; padding: '12dp'; spacing: '7dp'
        Label:
            text: 'AIRA SETTINGS'; bold: True; font_size: '20sp'; size_hint_y: None; height: '38dp'
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                orientation: 'vertical'; spacing: '7dp'; size_hint_y: None
                height: self.minimum_height
                Label:
                    text: 'AI / OpenRouter'; size_hint_y: None; height: '26dp'; bold: True
                TextInput:
                    id: base_url; hint_text: 'API URL'; text: root.base_url; multiline: False; size_hint_y: None; height: '44dp'
                TextInput:
                    id: api_key; hint_text: 'OpenRouter API key'; text: root.api_key; password: True; multiline: False; size_hint_y: None; height: '44dp'
                TextInput:
                    id: model; hint_text: 'Model ID'; text: root.model; multiline: False; size_hint_y: None; height: '44dp'
                Label:
                    text: 'Assistant name'; size_hint_y: None; height: '26dp'; bold: True
                TextInput:
                    id: assistant_name; hint_text: 'Aira'; text: root.assistant_name; multiline: False; size_hint_y: None; height: '44dp'
                Label:
                    text: 'Demo face'; size_hint_y: None; height: '26dp'; bold: True
                Spinner:
                    id: face_type; text: root.face_type; values: ['Female', 'Male', 'Anime Girl', 'Anime Boy']; size_hint_y: None; height: '44dp'
                Label:
                    text: 'RGB glow colour'; size_hint_y: None; height: '26dp'; bold: True
                Spinner:
                    id: rgb_color; text: root.rgb_color; values: ['Cyan', 'Purple', 'Blue', 'Red', 'Pink', 'Green', 'Rainbow']; size_hint_y: None; height: '44dp'
                Label:
                    text: 'Custom command (simple)'; size_hint_y: None; height: '26dp'; bold: True
                TextInput:
                    id: trigger; hint_text: 'Trigger e.g. open WhatsApp'; multiline: False; size_hint_y: None; height: '44dp'
                TextInput:
                    id: action; hint_text: 'Action e.g. whatsapp'; multiline: False; size_hint_y: None; height: '44dp'
                Button:
                    text: 'Add custom command'; size_hint_y: None; height: '44dp'; on_release: root.add_custom_command()
                Label:
                    text: root.status; size_hint_y: None; height: '54dp'; text_size: self.width, None
                Button:
                    text: 'Save all settings'; size_hint_y: None; height: '48dp'; on_release: root.save_settings()
                Button:
                    text: 'Back'; size_hint_y: None; height: '44dp'; on_release: app.root.current = 'chat'
'''

SYSTEM = ("You are a friendly AI assistant named {name}. Speak Hindi/Hinglish when the user does. "
          "Be concise and honest. If asked to do a phone action, clearly explain if the app cannot perform it.")
COLORS = {'Cyan':(0.0,0.9,1.0,1),'Purple':(0.68,0.25,1,1),'Blue':(0.15,0.4,1,1),'Red':(1,0.15,0.25,1),'Pink':(1,0.2,0.65,1),'Green':(0.1,1,0.45,1),'Rainbow':(0.5,0.35,1,1)}

from kivy.uix.widget import Widget
class AvatarWidget(Widget):
    face_type = StringProperty('Female')
    glow_color = StringProperty('Cyan')
    phase = NumericProperty(0)
    def __init__(self, **kwargs):
        super().__init__(**kwargs); Clock.schedule_interval(self._tick, .08)
        self.bind(pos=self.draw_face, size=self.draw_face, face_type=self.draw_face, glow_color=self.draw_face)
    def _tick(self, dt):
        self.phase += dt; self.draw_face()
    def draw_face(self, *args):
        self.canvas.clear()
        with self.canvas:
            c = COLORS.get(self.glow_color, COLORS['Cyan'])
            if self.glow_color == 'Rainbow':
                import colorsys
                h=(self.phase*.15)%1; c=(*colorsys.hsv_to_rgb(h,.75,1),1)
            Color(.025,.035,.09,1); RoundedRectangle(pos=self.pos,size=self.size,radius=[18])
            Color(*c); Line(rounded_rectangle=(self.x+10,self.y+10,self.width-20,self.height-20,22),width=1.5)
            cx=self.center_x; cy=self.center_y+4; r=min(self.width*.22,self.height*.34)
            Color(*c); Line(circle=(cx,cy,r*1.24),width=1.5)
            Color(.08,.12,.22,1); Ellipse(pos=(cx-r,cy-r),size=(2*r,2*r))
            Color(*c); Line(circle=(cx,cy,r),width=1.3)
            # Code-drawn stylized face, not a photo. Four variations.
            hair = self.face_type in ('Female','Anime Girl')
            anime = self.face_type in ('Anime Girl','Anime Boy')
            Color(.88,.67,.53,1); Ellipse(pos=(cx-r*.62,cy-r*.70),size=(r*1.24,r*1.40))
            if hair:
                Color(.16,.08,.10,1); Ellipse(pos=(cx-r*.70,cy+r*.05),size=(r*1.40,r*.75))
                Color(.88,.67,.53,1); Ellipse(pos=(cx-r*.58,cy-r*.70),size=(r*1.16,r*1.25))
            Color(.05,.06,.10,1)
            eye_r=r*(.105 if anime else .07)
            Ellipse(pos=(cx-r*.34-eye_r,cy+r*.02-eye_r),size=(2*eye_r,2*eye_r))
            Ellipse(pos=(cx+r*.34-eye_r,cy+r*.02-eye_r),size=(2*eye_r,2*eye_r))
            Color(*c); Line(points=[cx-r*.20,cy-r*.30,cx,cy-r*.35,cx+r*.20,cy-r*.30],width=1.2)
            Color(1,.45,.58,1); Line(points=[cx-r*.20,cy-r*.48,cx,cy-r*.54,cx+r*.20,cy-r*.48],width=1.5)
            Color(*c); Line(circle=(cx,cy,r*1.34),width=1)

class ChatScreen(Screen):
    chat_text=StringProperty('[b]Aira:[/b] Namaste! Settings mein API key save karo. 🎙 button se ek voice command try kar sakte ho.\n\n')
    history=[]
    def send_message(self):
        msg=self.ids.prompt.text.strip()
        if not msg:return
        self.ids.prompt.text=''
        self.chat_text += f'\n[b]You:[/b] {msg}\n'
        if self.run_command(msg): return
        self.chat_text += '[b]'+App.get_running_app().assistant_name+':[/b] Soch rahi hoon…\n'
        threading.Thread(target=self._ask,args=(msg,),daemon=True).start()
    def _ask(self,msg):
        app=App.get_running_app(); cfg=app.load_config(); answer=''
        if not cfg.get('api_key') or not cfg.get('model'):
            answer='Pehle Settings mein OpenRouter API key aur model ID save karo.'
        else:
            url=cfg.get('base_url','https://openrouter.ai/api/v1').rstrip('/')+'/chat/completions'
            messages=[{'role':'system','content':SYSTEM.format(name=app.assistant_name)}]+self.history[-10:]+[{'role':'user','content':msg}]
            body=json.dumps({'model':cfg['model'],'messages':messages,'temperature':0.7}).encode()
            req=urllib.request.Request(url,data=body,headers={'Authorization':'Bearer '+cfg['api_key'],'Content-Type':'application/json','HTTP-Referer':'https://localhost','X-Title':'Aira Assistant'},method='POST')
            try:
                with urllib.request.urlopen(req,timeout=60) as r: data=json.loads(r.read().decode())
                answer=data['choices'][0]['message']['content'].strip()
                self.history.extend([{'role':'user','content':msg},{'role':'assistant','content':answer}])
            except urllib.error.HTTPError as e: answer=f'API error {e.code}: {e.read().decode(errors="replace")[:180]}'
            except Exception as e: answer=f'Connection error: {e}'
        Clock.schedule_once(lambda dt:self._append(answer),0)
    def _append(self,answer):
        marker='[b]'+App.get_running_app().assistant_name+':[/b] Soch rahi hoon…'
        self.chat_text=self.chat_text.rsplit(marker,1)[0]+'[b]'+App.get_running_app().assistant_name+':[/b] '+answer+'\n\n'
    def run_command(self, text):
        t=text.lower().strip(); app=App.get_running_app(); cfg=app.load_config()
        # User-created commands are intentionally restricted to allowlisted actions.
        for item in cfg.get('custom_commands',[]):
            if item.get('trigger','').lower() in t and item.get('trigger'):
                t=item.get('action','').lower(); break
        if any(x in t for x in ('whatsapp','व्हाट्सएप')) and any(x in t for x in ('open','kholo','खोल','whatsapp')):
            ok=app.open_app('com.whatsapp')
            self.chat_text += ('WhatsApp kholne ki koshish ki.\n\n' if ok else 'WhatsApp installed nahi mila ya Android ne launch block kiya.\n\n'); return True
        if 'youtube' in t or 'यूट्यूब' in t:
            query=t
            for word in ['youtube','par','search','play','song','gaana','gana','chalao','chala','sad','sad song','open','karo','please']:
                query=query.replace(word,' ')
            query=' '.join(query.split()).strip() or 'sad songs'
            app.open_url('https://www.youtube.com/results?search_query='+urllib.parse.quote(query))
            self.chat_text += f'YouTube par "{query}" search khol diya. Agar auto-play supported na ho, song par tap karna padega.\n\n'; return True
        if t in ('time','time batao','samay batao'):
            from datetime import datetime
            self.chat_text += 'Abhi time: '+datetime.now().strftime('%I:%M %p')+'\n\n'; return True
        if t in ('date','date batao','aaj ki date'):
            from datetime import date
            self.chat_text += 'Aaj ki date: '+date.today().strftime('%d-%m-%Y')+'\n\n'; return True
        return False
    def listen_once(self):
        app=App.get_running_app()
        if not ANDROID:
            self.chat_text+='Voice recognition Android APK mein hi available hogi.\n\n'; return
        try:
            Intent=autoclass('android.content.Intent'); RecognizerIntent=autoclass('android.speech.RecognizerIntent')
            intent=Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE,'hi-IN')
            intent.putExtra(RecognizerIntent.EXTRA_PROMPT,'Aira ko command dein')
            app._listen_pending=True
            activity.bind(on_activity_result=app.on_activity_result)
            PythonActivity=autoclass('org.kivy.android.PythonActivity')
            PythonActivity.mActivity.startActivityForResult(intent,987)
        except Exception as e:self.chat_text+='Voice start nahi hua: '+str(e)+'\n\n'

class SettingsScreen(Screen):
    base_url=StringProperty('https://openrouter.ai/api/v1'); api_key=StringProperty(''); model=StringProperty('google/gemma-3-27b-it')
    assistant_name=StringProperty('Aira'); face_type=StringProperty('Female'); rgb_color=StringProperty('Cyan')
    status=StringProperty('API key app-private storage mein save hoti hai. Key share na karein.')
    def on_pre_enter(self,*args):
        c=App.get_running_app().load_config()
        for k,d in [('base_url','https://openrouter.ai/api/v1'),('api_key',''),('model','google/gemma-3-27b-it'),('assistant_name','Aira'),('face_type','Female'),('rgb_color','Cyan')]: setattr(self,k,c.get(k,d))
        for k in ['base_url','api_key','model','assistant_name','face_type','rgb_color']: self.ids[k].text=getattr(self,k)
    def add_custom_command(self):
        trigger=self.ids.trigger.text.strip(); action=self.ids.action.text.strip().lower()
        if not trigger or not action:self.status='Trigger aur action dono bharo.'; return
        if not any(x in action for x in ('youtube','whatsapp','time','date')):
            self.status='Abhi allowed actions: youtube, whatsapp, time, date.'; return
        app=App.get_running_app(); c=app.load_config(); cmds=c.get('custom_commands',[]); cmds.append({'trigger':trigger,'action':action}); c['custom_commands']=cmds; app.save_config(c)
        self.ids.trigger.text=''; self.ids.action.text=''; self.status='Custom command save ho gaya.'
    def save_settings(self):
        app=App.get_running_app(); cfg=app.load_config()
        url=self.ids.base_url.text.strip() or 'https://openrouter.ai/api/v1'
        if not url.startswith('https://'):self.status='HTTPS URL use karo.'; return
        cfg.update({'base_url':url,'api_key':self.ids.api_key.text.strip(),'model':self.ids.model.text.strip(),'assistant_name':self.ids.assistant_name.text.strip() or 'Aira','face_type':self.ids.face_type.text,'rgb_color':self.ids.rgb_color.text})
        app.save_config(cfg); app.apply_config(cfg); self.status='Settings save ho gayi.'

class AiraApp(App):
    assistant_name=StringProperty('Aira'); face_type=StringProperty('Female'); rgb_color=StringProperty('Cyan'); _listen_pending=False
    def build(self):
        self.title='Aira AI Assistant'; root=Builder.load_string(KV); Clock.schedule_once(lambda dt:self.apply_config(self.load_config()),0); return root
    def config_path(self):
        p=Path(self.user_data_dir)/'config.json'; p.parent.mkdir(parents=True,exist_ok=True); return p
    def load_config(self):
        try:return json.loads(self.config_path().read_text(encoding='utf-8'))
        except Exception:return {}
    def save_config(self,cfg):
        p=self.config_path(); p.write_text(json.dumps(cfg,ensure_ascii=False),encoding='utf-8')
        try:os.chmod(p,0o600)
        except OSError:pass
    def apply_config(self,c):
        self.assistant_name=c.get('assistant_name','Aira'); self.face_type=c.get('face_type','Female'); self.rgb_color=c.get('rgb_color','Cyan')
    def open_url(self,url):
        if ANDROID:
            try:
                Intent=autoclass('android.content.Intent'); Uri=autoclass('android.net.Uri'); PythonActivity=autoclass('org.kivy.android.PythonActivity')
                i=Intent(Intent.ACTION_VIEW,Uri.parse(url)); PythonActivity.mActivity.startActivity(i); return True
            except Exception:pass
        try:webbrowser.open(url); return True
        except Exception:return False
    def open_app(self,package):
        if not ANDROID:return False
        try:
            PythonActivity=autoclass('org.kivy.android.PythonActivity'); a=PythonActivity.mActivity
            i=a.getPackageManager().getLaunchIntentForPackage(package)
            if i is None:return False
            a.startActivity(i); return True
        except Exception:return False
    def on_activity_result(self,request_code,result_code,intent):
        if request_code!=987:return
        try:
            Activity=autoclass('android.app.Activity'); RecognizerIntent=autoclass('android.speech.RecognizerIntent')
            if result_code==Activity.RESULT_OK and intent:
                results=intent.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
                if results and len(results)>0:
                    spoken=str(results.get(0)); Clock.schedule_once(lambda dt:self.root.get_screen('chat')._voice_text(spoken),0)
        except Exception as e: print('speech result error',e)
        try:activity.unbind(on_activity_result=self.on_activity_result)
        except Exception:pass

# Add voice-result handler to ChatScreen without fragile KV event plumbing.
def _voice_text(self,text):
    self.ids.prompt.text=text; self.send_message()
ChatScreen._voice_text=_voice_text

if __name__=='__main__': AiraApp().run()
