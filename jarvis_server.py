"""JARVIS Web Server v5."""
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import tempfile
import json
from pathlib import Path

try:
    import edge_tts
    TTS_OK = True
except ImportError:
    TTS_OK = False

from jarvis_brain import JarvisBrain
from agents.self_improver import SelfImprover
from agents.proactive_agent import ProactiveAgent
from agents.task_executor import TaskExecutor
from agents.skill_library import SkillLibrary
from tools.document_reader import DocumentReader

app = FastAPI(title="JARVIS API v5")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

brain = JarvisBrain()
improver = SelfImprover()
proactive = ProactiveAgent()
tasks = TaskExecutor()
skills = SkillLibrary()
tasks.start()
# Faz 1 modülleri
try:
    from agents.daily_digest import DailyDigest
    digest = DailyDigest()
except ImportError:
    digest = None

try:
    from agents.auto_updater import AutoUpdater
    updater = AutoUpdater()
except ImportError:
    updater = None


class ChatReq(BaseModel):
    message: str


class ReminderReq(BaseModel):
    text: str
    when: str


class TaskReq(BaseModel):
    type: str
    params: dict
    priority: int = 5


class SkillReq(BaseModel):
    name: str
    triggers: list
    instructions: str
    tags: list = []


@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(UI)


@app.post("/chat")
async def chat(req: ChatReq):
    cevap = brain.chat(req.message)
    return {"response": cevap, "name": brain.profile.get("name", "Kullanıcı")}


@app.post("/speak")
async def speak(req: ChatReq):
    if not TTS_OK:
        return JSONResponse({"error": "TTS yok"}, status_code=503)
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        c = edge_tts.Communicate(req.message, "tr-TR-AhmetNeural")
        await c.save(tmp.name)
        return FileResponse(tmp.name, media_type="audio/mpeg")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    try:
        from tools.voice_io import VoiceIO
        v = VoiceIO()
        data = await audio.read()
        ext = "." + (audio.filename.split(".")[-1] if audio.filename else "wav")
        result = v.transcribe_bytes(data, ext=ext)
        return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/upload_doc")
async def upload_doc(doc: UploadFile = File(...), question: str = ""):
    try:
        Path("uploads").mkdir(exist_ok=True)
        p = Path("uploads") / doc.filename
        p.write_bytes(await doc.read())
        result = brain.analyze_document(str(p), question or None)
        return {"file": doc.filename, "analysis": result}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/status")
async def status():
    return {
        "online": True,
        "name": brain.profile.get("name"),
        "model": brain.MODEL,
        "city": brain.profile.get("city"),
        "tts": TTS_OK,
        "vector_memory": brain.memory.stats() if brain.memory else None,
        "conv_count": _conv_count(),
        "task_status": tasks.status(),
        "pending_question": improver.get_pending_question(),
    }


@app.get("/briefing/morning")
async def morning():
    return {"briefing": proactive.morning_briefing()}


@app.get("/briefing/evening")
async def evening():
    return {"briefing": proactive.evening_summary()}


@app.post("/reminder")
async def add_rem(req: ReminderReq):
    proactive.add_reminder(req.text, req.when)
    return {"ok": True}


@app.get("/reminders/due")
async def due_rems():
    return {"reminders": proactive.get_due()}


@app.get("/improvement/analyze")
async def improve():
    return improver.analyze_weaknesses()


@app.get("/improvement/latest")
async def latest_imp():
    return improver.get_latest_report()


@app.post("/task")
async def add_task(req: TaskReq):
    tid = tasks.add(req.type, req.params, req.priority)
    return {"task_id": tid}


@app.get("/tasks/status")
async def tasks_status():
    return tasks.status()


@app.get("/skills")
async def list_skills():
    return {"skills": skills.list_all()}


@app.post("/skill")
async def add_skill(req: SkillReq):
    skills.add(req.name, req.triggers, req.instructions, req.tags)
    return {"ok": True}

# ════════════════════════════════════════════════════
    # A) WebSocket Streaming
    # ════════════════════════════════════════════════════
    @app.websocket("/ws/chat")
    async def websocket_chat(ws: WebSocket):
        await ws.accept()
        try:
            while True:
                data = await ws.receive_json()
                msg = data.get("message", "").strip()
                if not msg:
                    continue

                # Brain'den cevap al (streaming için Ollama'yı direkt çağırırız)
                import requests as rq
                
                # Brain'in tam mantığını kullanmak için chat() çağırıp
                # cevabı kelime kelime gönder (semi-streaming)
                full_response = brain.chat(msg)

                # Kelime kelime gönder
                words = full_response.split()
                for i, w in enumerate(words):
                    await ws.send_json({
                        "type":    "token",
                        "content": w + (" " if i < len(words)-1 else ""),
                    })
                    import asyncio
                    await asyncio.sleep(0.04)  # Akış efekti

                await ws.send_json({
                    "type": "done",
                    "name": brain.profile.get("name", "Kullanıcı"),
                    "turn": getattr(brain, 'turn_count', 0),
                })
        except WebSocketDisconnect:
            pass
        except Exception as e:
            try:
                await ws.send_json({"type": "error", "content": str(e)})
            except:
                pass


    # ════════════════════════════════════════════════════
    # G) Daily Digest
    # ════════════════════════════════════════════════════
    @app.get("/digest/generate")
    async def gen_digest():
        if not digest:
            return {"error": "daily_digest modülü yok"}
        return digest.generate()


    @app.get("/digest/latest")
    async def latest_digest():
        if not digest:
            return {}
        return digest.get_latest()


    # ════════════════════════════════════════════════════
    # I) Tool Discovery
    # ════════════════════════════════════════════════════
    @app.get("/tools/list")
    async def list_tools():
        """JARVIS'in şu an kullanabildiği tüm araçlar"""
        out = []
        if hasattr(brain, '_tools'):
            for name in brain._tools.keys():
                fn = brain._tools[name]
                doc = (fn.__doc__ or "").strip().split("\n")[0][:120]
                out.append({"name": name, "description": doc})
        return {"tools": out, "count": len(out)}


    # ════════════════════════════════════════════════════
    # J) Auto-Update
    # ════════════════════════════════════════════════════
    @app.get("/update/check")
    async def check_update():
        if not updater:
            return {"available": False, "reason": "auto_updater yok"}
        return updater.has_updates()


    @app.post("/update/apply")
    async def apply_update():
        if not updater:
            return {"ok": False, "error": "auto_updater yok"}
        return updater.update(restart_after=False)


    # ════════════════════════════════════════════════════
    # F) Memory cleanup
    # ════════════════════════════════════════════════════
    @app.post("/memory/cleanup")
    async def cleanup_memory(days: int = 30):
        if not getattr(brain, 'scorer', None):
            return {"ok": False, "error": "scorer yok"}
        deleted = brain.scorer.cleanup_old(days=days)
        return {"ok": True, "deleted": deleted}



@app.get("/dashboard_data")
async def dash_data():
    p = Path("memory/conversations.json")
    if not p.exists():
        return {"convs": []}
    try:
        cs = json.loads(p.read_text(encoding='utf-8'))
        return {
            "total": len(cs),
            "evaluated": sum(1 for c in cs
                             if c.get("metadata", {}).get("evaluated")),
            "avg_score": _avg_score(cs),
            "high_quality": sum(
                1 for c in cs
                if c.get("metadata", {}).get("quality_score", 0) >= 7),
        }
    except:
        return {"error": "Veri okunamadı"}


def _conv_count():
    p = Path("memory/conversations.json")
    if not p.exists():
        return 0
    try:
        return len(json.loads(p.read_text(encoding='utf-8')))
    except:
        return 0


def _avg_score(cs):
    s = [c.get("metadata", {}).get("quality_score", 0) for c in cs
         if c.get("metadata", {}).get("evaluated")]
    return round(sum(s) / len(s), 1) if s else 0


UI = """<!DOCTYPE html>
<html lang="tr"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JARVIS v5</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:-apple-system,system-ui,sans-serif}
body{background:linear-gradient(135deg,#0a0e27 0%,#1a1f3a 100%);color:#fff;min-height:100vh;display:flex;flex-direction:column}
header{background:rgba(0,0,0,0.4);padding:20px;text-align:center;border-bottom:1px solid rgba(0,255,255,0.2)}
h1{font-size:32px;letter-spacing:8px;background:linear-gradient(90deg,#00f0ff,#00d4ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.subtitle{font-size:12px;opacity:0.6;margin-top:4px;letter-spacing:2px}
.tabs{display:flex;background:rgba(0,0,0,0.3);border-bottom:1px solid rgba(0,255,255,0.2)}
.tab{flex:1;padding:12px;text-align:center;cursor:pointer;font-size:13px;opacity:0.6;transition:0.2s}
.tab.active{opacity:1;border-bottom:2px solid #00f0ff;background:rgba(0,255,255,0.05)}
.panel{flex:1;overflow-y:auto;padding:20px;display:none}
.panel.active{display:flex;flex-direction:column}
.chat{flex:1;display:flex;flex-direction:column;gap:12px}
.msg{max-width:85%;padding:12px 16px;border-radius:18px;line-height:1.4;word-wrap:break-word}
.user{align-self:flex-end;background:linear-gradient(135deg,#1e88e5,#1976d2);border-bottom-right-radius:4px}
.jarvis{align-self:flex-start;background:rgba(0,255,255,0.1);border:1px solid rgba(0,255,255,0.3);border-bottom-left-radius:4px}
.jarvis::before{content:"JARVIS";display:block;font-size:10px;opacity:0.6;margin-bottom:4px;letter-spacing:2px}
.input-area{background:rgba(0,0,0,0.6);padding:16px;border-top:1px solid rgba(0,255,255,0.2);display:flex;gap:10px}
input,textarea{flex:1;background:rgba(255,255,255,0.1);border:1px solid rgba(0,255,255,0.3);color:#fff;padding:14px 18px;border-radius:24px;font-size:16px}
input:focus,textarea:focus{outline:none;border-color:#00f0ff}
button{background:linear-gradient(135deg,#00d4ff,#0099cc);color:#000;border:none;padding:14px 24px;border-radius:24px;font-weight:bold;cursor:pointer;font-size:14px}
button:active{transform:scale(0.95)}
.mic-btn{padding:14px 18px}
.mic-btn.listening{background:#ff4444;color:#fff;animation:pulse 1s infinite}
@keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.1)}}
.status{font-size:11px;opacity:0.5;text-align:center;padding:4px}
.card{background:rgba(0,255,255,0.05);border:1px solid rgba(0,255,255,0.2);border-radius:12px;padding:16px;margin-bottom:12px}
.card h3{color:#00f0ff;margin-bottom:8px;font-size:14px;letter-spacing:1px}
.stat-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px}
.stat{background:rgba(0,255,255,0.08);padding:12px;border-radius:8px;text-align:center}
.stat-val{font-size:24px;color:#00f0ff;font-weight:bold}
.stat-lbl{font-size:11px;opacity:0.7}
.briefing-text{white-space:pre-wrap;line-height:1.6;font-size:14px}
.upload-zone{border:2px dashed rgba(0,255,255,0.4);border-radius:12px;padding:24px;text-align:center;margin-bottom:12px}
</style></head>
<body>
<header>
  <h1>J A R V I S</h1>
  <div class="subtitle">v5 — OPERATION OVERMIND</div>
</header>
<div class="tabs">
  <div class="tab active" onclick="t('chat')">💬 Sohbet</div>
  <div class="tab" onclick="t('brief')">🌅 Brifing</div>
  <div class="tab" onclick="t('docs')">📄 Doküman</div>
  <div class="tab" onclick="t('stats')">📊 Durum</div>
</div>

<div class="panel active" id="chat">
  <div class="chat" id="chatbox"></div>
</div>

<div class="panel" id="brief">
  <div class="card">
    <h3>🌅 Sabah Brifingi</h3>
    <div id="morning-text" class="briefing-text">Yükleniyor...</div>
    <button onclick="loadBriefing('morning')" style="margin-top:12px">Yenile</button>
  </div>
  <div class="card">
    <h3>🌙 Akşam Özeti</h3>
    <div id="evening-text" class="briefing-text">-</div>
    <button onclick="loadBriefing('evening')" style="margin-top:12px">Üret</button>
  </div>
</div>

<div class="panel" id="docs">
  <div class="upload-zone">
    <div style="margin-bottom:12px">📤 PDF/Excel/Word yükle</div>
    <input type="file" id="docfile" style="margin-bottom:12px">
    <input type="text" id="docq" placeholder="Soru (isteğe bağlı)" style="margin-bottom:12px">
    <button onclick="uploadDoc()">Analiz Et</button>
  </div>
  <div id="doc-result" class="briefing-text"></div>
</div>

<div class="panel" id="stats">
  <div class="stat-grid" id="stat-grid"></div>
  <div class="card" id="pending-q" style="display:none">
    <h3>❓ JARVIS sana soruyor</h3>
    <div id="pending-text"></div>
  </div>
  <button onclick="loadStats()" style="width:100%">Yenile</button>
</div>

<div class="status" id="status">Bağlantı kuruluyor...</div>
<div class="input-area">
  <input id="msg" placeholder="Bir şey söyleyin efendim..." onkeydown="if(event.key==='Enter')send()">
  <button class="mic-btn" id="micBtn" onclick="toggleMic()">🎤</button>
  <button onclick="send()">Gönder</button>
</div>

<script>
const HEADERS={'Content-Type':'application/json','ngrok-skip-browser-warning':'true'};
const chatbox=document.getElementById('chatbox');
const input=document.getElementById('msg');
const status=document.getElementById('status');
const micBtn=document.getElementById('micBtn');

let recognition=null,listening=false;
if('webkitSpeechRecognition' in window||'SpeechRecognition' in window){
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  recognition=new SR();recognition.lang='tr-TR';recognition.continuous=false;recognition.interimResults=false;
  recognition.onresult=(e)=>{input.value=e.results[0][0].transcript;send()};
  recognition.onend=()=>{listening=false;micBtn.classList.remove('listening')};
  recognition.onerror=()=>{listening=false;micBtn.classList.remove('listening')};
}
function toggleMic(){
  if(!recognition){alert('Ses desteklenmiyor');return}
  listening?recognition.stop():(recognition.start(),listening=true,micBtn.classList.add('listening'));
}

function t(name){
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById(name).classList.add('active');
  if(name==='stats')loadStats();
  if(name==='brief')loadBriefing('morning');
}

function addMsg(text,user){
  const d=document.createElement('div');
  d.className='msg '+(user?'user':'jarvis');
  d.textContent=text;
  chatbox.appendChild(d);chatbox.scrollTop=chatbox.scrollHeight;
}

let ws = null;
  function ensureWs(){
    if(ws && ws.readyState === WebSocket.OPEN) return ws;
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(proto + '//' + location.host + '/ws/chat');
    return ws;
  }

  async function send(){
    const txt=input.value.trim();if(!txt)return;
    input.value='';
    document.getElementById('status').textContent='JARVIS düşünüyor...';
    addMsg(txt, true);

    const thinking=document.createElement('div');
    thinking.className='thinking-wrapper';
    thinking.innerHTML='<div class="stark-spinner" style="color:#00d4ff; font-size:12px; margin:10px 0;">⚡ JARVIS SİSTEMLERİ TARANIYOR...</div>';
    chatbox.appendChild(thinking);
    chatbox.scrollTop = chatbox.scrollHeight;

    try {
      const sock = ensureWs();
      let botDiv = null;
      let fullText = "";

      sock.onopen = () => sock.send(JSON.stringify({message: txt}));
      if(sock.readyState === WebSocket.OPEN) sock.send(JSON.stringify({message: txt}));

      sock.onmessage = (ev) => {
        const d = JSON.parse(ev.data);
        if(d.type === 'token'){
          if(thinking.parentNode) thinking.remove();
          if(!botDiv){
            botDiv = document.createElement('div');
            botDiv.className='msg jarvis';
            chatbox.appendChild(botDiv);
          }
          fullText += d.content;
          botDiv.textContent = fullText;
          chatbox.scrollTop = chatbox.scrollHeight;
        } else if(d.type === 'done'){
          speak(fullText);
          document.getElementById('status').textContent = 'Hazır · Tur: ' + (d.turn||0);
          input.focus();
        } else if(d.type === 'error'){
          if(thinking.parentNode) thinking.remove();
          addMsg('❌ ' + d.content, false);
        }
      };

      sock.onerror = () => {
        if(thinking.parentNode) thinking.remove();
        fallbackHttp(txt);
      };
    } catch(e){
      if(thinking.parentNode) thinking.remove();
      fallbackHttp(txt);
    }
  }

  async function fallbackHttp(txt){
    try{
      const r=await fetch('/chat',{method:'POST',headers:HEADERS,body:JSON.stringify({message:txt})});
      const d=await r.json();
      addMsg(d.response||'', false);
      speak(d.response);
      document.getElementById('status').textContent='Hazır · Tur: '+(d.turn||0);
    }catch(e){
      addMsg('❌ '+e.message, false);
    }
  }

async function speak(text){
  try{
    const r=await fetch('/speak',{method:'POST',headers:HEADERS,body:JSON.stringify({message:text})});
    if(!r.ok)return;
    const blob=await r.blob();new Audio(URL.createObjectURL(blob)).play();
  }catch(e){}
}

async function loadBriefing(kind){
  const id=kind+'-text';
  document.getElementById(id).textContent='Yükleniyor...';
  try{
    const r=await fetch('/briefing/'+kind,{headers:HEADERS});
    const d=await r.json();
    document.getElementById(id).textContent=d.briefing;
  }catch(e){document.getElementById(id).textContent='Hata: '+e.message}
}

async function uploadDoc(){
  const f=document.getElementById('docfile').files[0];
  const q=document.getElementById('docq').value;
  if(!f){alert('Dosya seç');return}
  const fd=new FormData();fd.append('doc',f);
  document.getElementById('doc-result').textContent='Analiz ediliyor...';
  try{
    const r=await fetch('/upload_doc?question='+encodeURIComponent(q),
      {method:'POST',body:fd,headers:{'ngrok-skip-browser-warning':'true'}});
    const d=await r.json();
    document.getElementById('doc-result').textContent=d.analysis||d.error;
  }catch(e){document.getElementById('doc-result').textContent='Hata: '+e.message}
}

async function loadStats(){
  try{
    const s=await(await fetch('/status',{headers:HEADERS})).json();
    const d=await(await fetch('/dashboard_data',{headers:HEADERS})).json();
    const grid=document.getElementById('stat-grid');
    grid.innerHTML=`
      <div class="stat"><div class="stat-val">${d.total||0}</div><div class="stat-lbl">Toplam Konuşma</div></div>
      <div class="stat"><div class="stat-val">${d.evaluated||0}</div><div class="stat-lbl">Değerlendirildi</div></div>
      <div class="stat"><div class="stat-val">${d.avg_score||0}</div><div class="stat-lbl">Ort. Kalite</div></div>
      <div class="stat"><div class="stat-val">${d.high_quality||0}</div><div class="stat-lbl">Kaliteli (≥7)</div></div>
      <div class="stat"><div class="stat-val">${(s.vector_memory||{total:0}).total}</div><div class="stat-lbl">Hafıza</div></div>
      <div class="stat"><div class="stat-val">${s.task_status?.pending||0}</div><div class="stat-lbl">Bekleyen Görev</div></div>
    `;
    if(s.pending_question){
      document.getElementById('pending-q').style.display='block';
      document.getElementById('pending-text').textContent=s.pending_question;
    }
  }catch(e){console.error(e)}
}

fetch('/status',{headers:HEADERS}).then(r=>r.json()).then(d=>{
  status.textContent=`v5 ${d.online?'🟢':'🔴'} | ${d.name||'?'} | ${d.model} | ${d.conv_count} konuşma`;
  addMsg(`Merhaba ${d.name||'efendim'}, JARVIS v5 sistemleri çevrimiçi.`,false);
}).catch(()=>{status.textContent='Bağlantı yok'});
</script></body></html>"""


if __name__ == "__main__":
    import socket, threading, subprocess, time
    import requests as req
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close()
    except:
        ip = "localhost"
    print("\n" + "="*60)
    print("🚀 JARVIS v5 — OPERATION OVERMIND")
    print("="*60)
    print(f"💻 PC:    http://localhost:8000")
    print(f"📱 WiFi:  http://{ip}:8000")

    def ngrok():
        time.sleep(2)
        try:
            subprocess.Popen(["ngrok", "http", "8000"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(4)
            r = req.get("http://localhost:4040/api/tunnels", timeout=3)
            ts = r.json().get("tunnels", [])
            if ts:
                print(f"🌍 DÜNYA: {ts[0]['public_url']}")
        except Exception as e:
            print(f"⚠️  Ngrok: {e}")

    threading.Thread(target=ngrok, daemon=True).start()
    print("="*60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
