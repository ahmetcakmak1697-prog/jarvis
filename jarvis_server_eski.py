"""
JARVIS Web Server — Telefondan kontrol için
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import asyncio
import edge_tts
import tempfile
from pathlib import Path

from jarvis_brain import JarvisBrain

app = FastAPI(title="JARVIS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

brain = JarvisBrain()


class ChatRequest(BaseModel):
    message: str


@app.get("/", response_class=HTMLResponse)
async def home():
    """Ana sayfa - mobil arayüz"""
    return HTMLResponse(MOBILE_UI)


@app.post("/chat")
async def chat(req: ChatRequest):
    """JARVIS'e mesaj gönder, cevap al"""
    cevap = brain.chat(req.message)
    return {"response": cevap, "name": brain.profile.get("name", "Kullanıcı")}


@app.post("/speak")
async def speak(req: ChatRequest):
    """Metni sese çevir, mp3 döndür"""
    tmp_path = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
    communicate = edge_tts.Communicate(req.message, "tr-TR-AhmetNeural")
    await communicate.save(tmp_path)
    return FileResponse(tmp_path, media_type="audio/mpeg")


@app.get("/status")
async def status():
    """JARVIS durumu"""
    return {
        "online": True,
        "name": brain.profile.get("name"),
        "model": brain.MODEL,
        "city": brain.profile.get("city"),
    }


MOBILE_UI = """
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JARVIS</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; font-family:-apple-system, system-ui, sans-serif; }
body {
  background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
  color: #fff; min-height: 100vh; display:flex; flex-direction:column;
}
header {
  background: rgba(0,0,0,0.4); padding: 20px; text-align: center;
  border-bottom: 1px solid rgba(0,255,255,0.2);
}
h1 {
  font-size: 32px; letter-spacing: 8px;
  background: linear-gradient(90deg, #00f0ff, #00d4ff);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.subtitle { font-size: 12px; opacity: 0.6; margin-top: 4px; letter-spacing: 2px; }
.chat {
  flex: 1; overflow-y: auto; padding: 20px; display:flex; flex-direction:column; gap:12px;
}
.msg {
  max-width: 80%; padding: 12px 16px; border-radius: 18px;
  word-wrap: break-word; line-height: 1.4;
}
.user {
  align-self: flex-end;
  background: linear-gradient(135deg, #1e88e5, #1976d2);
  border-bottom-right-radius: 4px;
}
.jarvis {
  align-self: flex-start;
  background: rgba(0,255,255,0.1);
  border: 1px solid rgba(0,255,255,0.3);
  border-bottom-left-radius: 4px;
}
.jarvis::before { content:"JARVIS"; display:block; font-size:10px; opacity:0.6; margin-bottom:4px; letter-spacing:2px; }
.input-area {
  background: rgba(0,0,0,0.6); padding: 16px;
  border-top: 1px solid rgba(0,255,255,0.2); display: flex; gap: 10px;
}
input {
  flex: 1; background: rgba(255,255,255,0.1); border:1px solid rgba(0,255,255,0.3);
  color: #fff; padding: 14px 18px; border-radius: 24px; font-size: 16px;
}
input:focus { outline:none; border-color: #00f0ff; }
button {
  background: linear-gradient(135deg, #00d4ff, #0099cc); color: #000;
  border: none; padding: 14px 24px; border-radius: 24px; font-weight:bold;
  cursor: pointer; font-size: 16px;
}
button:active { transform: scale(0.95); }
.mic-btn { padding: 14px 18px; }
.mic-btn.listening { background: #ff4444; color: #fff; animation: pulse 1s infinite; }
@keyframes pulse { 0%,100% { transform:scale(1); } 50% { transform:scale(1.1); } }
.status { font-size: 11px; opacity: 0.5; text-align: center; padding: 4px; }
</style>
</head>
<body>
<header>
  <h1>J A R V I S</h1>
  <div class="subtitle">IRON MAN MODE</div>
</header>

<div class="chat" id="chat"></div>

<div class="status" id="status">Bağlantı kuruluyor...</div>

<div class="input-area">
  <input id="msg" placeholder="Bir şey söyleyin efendim..." onkeydown="if(event.key==='Enter')send()">
  <button class="mic-btn" id="micBtn" onclick="toggleMic()">🎤</button>
  <button onclick="send()">Gönder</button>
</div>

<script>
const chat = document.getElementById('chat');
const input = document.getElementById('msg');
const micBtn = document.getElementById('micBtn');
const status = document.getElementById('status');

let recognition = null;
let listening = false;

// Web Speech API
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SR();
  recognition.lang = 'tr-TR';
  recognition.continuous = false;
  recognition.interimResults = false;
  
  recognition.onresult = (e) => {
    const text = e.results[0][0].transcript;
    input.value = text;
    send();
  };
  recognition.onend = () => { listening = false; micBtn.classList.remove('listening'); };
  recognition.onerror = () => { listening = false; micBtn.classList.remove('listening'); };
}

function toggleMic() {
  if (!recognition) { alert('Tarayıcınız sesli komutu desteklemiyor'); return; }
  if (listening) { recognition.stop(); }
  else { recognition.start(); listening = true; micBtn.classList.add('listening'); }
}

function addMsg(text, isUser) {
  const div = document.createElement('div');
  div.className = 'msg ' + (isUser ? 'user' : 'jarvis');
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

async function send() {
  const text = input.value.trim();
  if (!text) return;
  addMsg(text, true);
  input.value = '';
  
  try {
    const r = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text})
    });
    const data = await r.json();
    addMsg(data.response, false);
    speak(data.response);
  } catch (e) {
    addMsg('Bağlantı hatası: ' + e.message, false);
  }
}

async function speak(text) {
  try {
    const r = await fetch('/speak', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text})
    });
    const blob = await r.blob();
    const audio = new Audio(URL.createObjectURL(blob));
    audio.play();
  } catch (e) { console.error(e); }
}

// Status check
fetch('/status').then(r=>r.json()).then(d=>{
  status.textContent = `JARVIS aktif | ${d.name || 'Anonim'} | ${d.model}`;
  addMsg(`Merhaba ${d.name || 'efendim'}, sistemler çevrimiçi.`, false);
}).catch(()=>{ status.textContent = 'Bağlantı yok'; });
</script>
</body>
</html>
"""


if __name__ == "__main__":
    import socket, threading, subprocess, time
    import requests as req
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "localhost"
    
    print("\n" + "="*60)
    print("🚀 JARVIS GLOBAL SERVER")
    print("="*60)
    print(f"💻 PC:        http://localhost:8000")
    print(f"📱 WiFi:      http://{local_ip}:8000")
    
    def start_ngrok():
        time.sleep(2)
        try:
            subprocess.Popen(["ngrok", "http", "8000"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(4)
            r = req.get("http://localhost:4040/api/tunnels", timeout=3)
            tunnels = r.json().get("tunnels", [])
            if tunnels:
                print(f"🌍 DÜNYA:     {tunnels[0]['public_url']}")
        except Exception as e:
            print(f"⚠️  Ngrok hatası: {e}")
    
    threading.Thread(target=start_ngrok, daemon=True).start()
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")