"""
jarvis/gui.py — Flask Web Arayüzü (düzeltildi)
Çalıştır: python gui.py
Tarayıcıda aç: http://localhost:5000
"""
from __future__ import annotations
import sys
import threading
import webbrowser
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, request, jsonify

app = Flask(__name__)
agent = None


def _init_agent():
    global agent
    import os
    from dotenv import load_dotenv
    load_dotenv()
    try:
        from agent.local_agent import LocalJarvisAgent
        agent = LocalJarvisAgent()
        print("✓ Jarvis hazır!")
    except Exception as e:
        print(f"Agent hatası: {e}")


HTML = r"""<!DOCTYPE html>
<html lang="tr">
<head>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
<meta charset="UTF-8">
<title>JARVIS</title>
<style>
:root {
    --stark-blue: #00d4ff;
    --stark-glow: rgba(0, 212, 255, 0.3);
}

/* JARVIS Düşünme Paneli Tasarımı */
.thinking-wrapper {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin: 15px 0;
    padding: 12px;
    background: rgba(0, 212, 255, 0.03);
    border-left: 3px solid var(--stark-blue);
    border-radius: 4px;
}

.stark-spinner {
    display: flex;
    align-items: center;
    gap: 12px;
    color: var(--stark-blue);
    font-weight: bold;
    font-size: 0.95em;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.pulse-dot {
    width: 12px;
    height: 12px;
    background-color: var(--stark-blue);
    border-radius: 50%;
    box-shadow: 0 0 15px var(--stark-blue);
    animation: stark-pulse 1.5s infinite ease-in-out;
}

@keyframes stark-pulse {
    0% { transform: scale(0.8); opacity: 0.5; box-shadow: 0 0 5px var(--stark-blue); }
    50% { transform: scale(1.2); opacity: 1; box-shadow: 0 0 20px var(--stark-blue); }
    100% { transform: scale(0.8); opacity: 0.5; box-shadow: 0 0 5px var(--stark-blue); }
}

.thought-details {
    font-size: 0.85em;
    color: #94a3b8;
    margin-left: 24px;
    margin-top: 5px;
}

.thought-details summary {
    cursor: pointer;
    outline: none;
    user-select: none;
}
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;height:100vh;display:flex;flex-direction:column;}
.header{background:#1e293b;padding:14px 24px;border-bottom:1px solid #334155;display:flex;align-items:center;gap:12px;}
.header h1{font-size:1.4em;color:#06b6d4;letter-spacing:2px;}
.dot{width:8px;height:8px;background:#22c55e;border-radius:50%;display:inline-block;margin-right:6px;animation:p 2s infinite;}
@keyframes p{0%,100%{opacity:1}50%{opacity:.3}}
.tabs{display:flex;background:#1e293b;border-bottom:1px solid #334155;}
.tab{padding:10px 22px;cursor:pointer;font-size:.9em;color:#94a3b8;border-bottom:2px solid transparent;transition:.2s;}
.tab:hover{color:#e2e8f0;}
.tab.active{color:#06b6d4;border-bottom-color:#06b6d4;}
.page{display:none;flex:1;overflow:hidden;flex-direction:column;}
.page.active{display:flex;}

/* CHAT */
#msgs{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:14px;}
.umsg{background:#1d4ed8;color:#fff;padding:10px 16px;border-radius:12px 12px 2px 12px;align-self:flex-end;max-width:75%;white-space:pre-wrap;word-wrap:break-word;}
.bmsg{background:#1e293b;border:1px solid #334155;padding:12px 16px;border-radius:12px 12px 12px 2px;align-self:flex-start;max-width:80%;white-space:pre-wrap;word-wrap:break-word;}
.bname{color:#06b6d4;font-weight:bold;font-size:.8em;margin-bottom:5px;}
.thinking{background:#0f172a;border:1px dashed #475569;color:#64748b;font-style:italic;padding:10px 16px;border-radius:8px;align-self:flex-start;}
.quick{padding:8px 16px 0;display:flex;gap:8px;flex-wrap:wrap;}
.qbtn{background:#1e293b;border:1px solid #475569;color:#94a3b8;padding:5px 14px;border-radius:20px;cursor:pointer;font-size:.82em;transition:.2s;}
.qbtn:hover{border-color:#06b6d4;color:#06b6d4;}
.iarea{padding:14px 16px;background:#1e293b;border-top:1px solid #334155;display:flex;gap:10px;align-items:center;}
#inp{flex:1;background:#0f172a;border:1px solid #334155;color:#e2e8f0;border-radius:8px;padding:10px 14px;font-size:.95em;font-family:inherit;height:44px;outline:none;transition:.2s;}
#inp:focus{border-color:#06b6d4;}
#sbtn{background:#0891b2;color:#fff;border:none;border-radius:8px;padding:10px 20px;cursor:pointer;font-size:.95em;transition:.2s;white-space:nowrap;}
#sbtn:hover{background:#06b6d4;}
#sbtn:disabled{background:#334155;cursor:not-allowed;}

/* OTHER PAGES */
.pcontent{padding:24px;overflow-y:auto;flex:1;}
.sgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-top:14px;}
.scard{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:16px;}
.slabel{color:#64748b;font-size:.8em;margin-bottom:6px;}
.sval{color:#06b6d4;font-size:1.5em;font-weight:bold;}
.nform{display:grid;gap:10px;max-width:580px;margin-bottom:20px;}
.nform textarea,.nform select{background:#1e293b;border:1px solid #334155;color:#e2e8f0;border-radius:8px;padding:10px;font-size:.9em;outline:none;font-family:inherit;}
.nform textarea{height:80px;resize:vertical;}
.nbtn{background:#0891b2;color:#fff;border:none;border-radius:8px;padding:10px 18px;cursor:pointer;font-size:.9em;}
.nitem{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:12px;margin-bottom:10px;}
.ncat{color:#06b6d4;font-size:.75em;font-weight:bold;margin-bottom:4px;}
h2{color:#e2e8f0;margin-bottom:16px;}
.htbl{width:100%;border-collapse:collapse;margin-top:10px;}
.htbl th,.htbl td{text-align:left;padding:10px 14px;border-bottom:1px solid #334155;font-size:.9em;}
.htbl th{color:#64748b;font-size:.8em;text-transform:uppercase;}
#sbar{padding:5px 16px;font-size:.8em;color:#64748b;background:#0f172a;border-top:1px solid #1e293b;}
.rbtn{background:#1e293b;border:1px solid #334155;color:#94a3b8;padding:8px 16px;border-radius:8px;cursor:pointer;margin-top:14px;}
</style>
</head>
<body>

<div class="header">
  <span style="font-size:1.5em">⚡</span>
  <h1>JARVIS</h1>
  <div style="margin-left:auto;font-size:.85em;color:#64748b"><span class="dot"></span>Lokal · Ücretsiz · Güvenli</div>
</div>

<div class="tabs">
  <div class="tab active" onclick="goTab(0)">💬 Sohbet</div>
  <div class="tab" onclick="goTab(1)">📊 İstatistik</div>
  <div class="tab" onclick="goTab(2)">📝 Notlar</div>
  <div class="tab" onclick="goTab(3)">❓ Yardım</div>
</div>

<!-- SOHBET -->
<div class="page active" id="p0">
  <div id="msgs">
    <div class="bmsg"><div class="bname">⚡ JARVIS</div>Merhaba! Ben Jarvis, lokal AI asistanınım. Web araştırması, dosya analizi, hesaplama ve daha fazlasını yapabilirim. Ne yapmamı istersiniz?</div>
  </div>
  <div class="quick">
    <span class="qbtn" onclick="qs('Şu an saat kaç?')">🕐 Saat</span>
    <span class="qbtn" onclick="qs('Türkiye gündem haberlerini araştır')">🌐 Araştır</span>
    <span class="qbtn" onclick="qs('sqrt(256) + 100 hesapla')">🧮 Hesap</span>
    <span class="qbtn" onclick="qs('Notlarımı göster')">📋 Notlar</span>
    <span class="qbtn" onclick="qs('Yeteneklerini anlat')">🤖 Yetenekler</span>
  </div>
  <div class="iarea">
    <input type="text" id="inp" placeholder="Jarvis'e yaz... (Enter ile gönder)" />
    <button id="sbtn" onclick="send()">Gönder ▶</button>
  </div>
</div>

<!-- İSTATİSTİK -->
<div class="page" id="p1">
  <div class="pcontent">
    <h2>📊 Kullanım İstatistikleri</h2>
    <div class="sgrid">
      <div class="scard"><div class="slabel">Konuşma Turu</div><div class="sval" id="st0">—</div></div>
      <div class="scard"><div class="slabel">Araç Çağrısı</div><div class="sval" id="st1">—</div></div>
      <div class="scard"><div class="slabel">Hafıza Kayıtları</div><div class="sval" id="st2">—</div></div>
      <div class="scard"><div class="slabel">Maliyet</div><div class="sval" style="color:#22c55e">0₺</div></div>
    </div>
    <div style="margin-top:16px;color:#64748b;font-size:.9em" id="st3"></div>
    <button class="rbtn" onclick="loadStats()">🔄 Yenile</button>
  </div>
</div>

<!-- NOTLAR -->
<div class="page" id="p2">
  <div class="pcontent">
    <h2>📝 Notlarım</h2>
    <div class="nform">
      <textarea id="ntxt" placeholder="Not içeriği..."></textarea>
      <select id="ncat">
        <option value="genel">📌 Genel</option>
        <option value="görev">✅ Görev</option>
        <option value="fikir">💡 Fikir</option>
        <option value="araştırma">🔬 Araştırma</option>
        <option value="kişisel">👤 Kişisel</option>
      </select>
      <button class="nbtn" onclick="saveNote()">💾 Kaydet</button>
    </div>
    <div id="nlist"></div>
  </div>
</div>

<!-- YARDIM -->
<div class="page" id="p3">
  <div class="pcontent">
    <h2>❓ Kullanım Kılavuzu</h2>
    <p style="color:#94a3b8;margin-bottom:14px">Sadece doğal Türkçe yaz, Jarvis gerekli aracı otomatik seçer:</p>
    <table class="htbl">
      <tr><th>Ne yazarsın</th><th>Ne olur</th></tr>
      <tr><td>"X hakkında araştır"</td><td>🌐 İnternette arama yapar</td></tr>
      <tr><td>"X konusunu derinlemesine araştır"</td><td>🔬 Çok kaynaklı araştırma</td></tr>
      <tr><td>"sqrt(144) hesapla"</td><td>🧮 Matematik hesaplar</td></tr>
      <tr><td>"şunu not et: ..."</td><td>📝 Not kaydeder</td></tr>
      <tr><td>"notlarımı göster"</td><td>📋 Notları listeler</td></tr>
      <tr><td>"saat kaç"</td><td>📅 Tarih/saat verir</td></tr>
      <tr><td>"şu kodu çalıştır: ..."</td><td>🐍 Python çalıştırır</td></tr>
    </table>
  </div>
</div>

<div id="sbar">Hazır</div>

<script>
const msgsEl = document.getElementById('msgs');
const inpEl  = document.getElementById('inp');
const sBtn   = document.getElementById('sbtn');

// Enter ile gönder
inpEl.addEventListener('keydown', function(e){
  if(e.key === 'Enter'){ e.preventDefault(); send(); }
});

function goTab(i){
  document.querySelectorAll('.tab').forEach((t,j)=>t.classList.toggle('active',i===j));
  document.querySelectorAll('.page').forEach((p,j)=>p.classList.toggle('active',i===j));
  if(i===1) loadStats();
  if(i===2) loadNotes();
}

function qs(t){ inpEl.value=t; send(); }

function esc(t){ return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>'); }

function addMsg(role,text){
  const d=document.createElement('div');
  if(role==='user'){
    d.className='umsg'; d.textContent=text;
  } else {
    d.className='bmsg';
    d.innerHTML='<div class="bname">⚡ JARVIS</div>'+esc(text);
  }
  msgsEl.appendChild(d);
  msgsEl.scrollTop=msgsEl.scrollHeight;
  if (window.MathJax) { MathJax.typesetPromise([d]); }
  return d;
}

async function send() {
    const txt = inpEl.value.trim();
    if (!txt || sBtn.disabled) return;
    
    inpEl.value = '';
    sBtn.disabled = true;
    
    // Alt bardaki metni güncelle
    const sbar = document.getElementById('sbar');
    if(sbar) sbar.textContent = 'JARVIS veri ağlarını tarıyor...';

    // Senin mesajını ekrana bas
    addMsg('user', txt);

    // --- MAVİ DÜŞÜNME PANELİNİ OLUŞTUR ---
    const thinkingDiv = document.createElement('div');
    thinkingDiv.className = 'thinking-wrapper';
    thinkingDiv.innerHTML = `
        <div class="stark-spinner">
            <div class="pulse-dot"></div>
            <span>ANALİZ EDİLİYOR...</span>
        </div>
        <details class="thought-details">
            <summary style="cursor:pointer; outline:none;">▼ İşlem Detayları</summary>
            <div style="padding-top:10px; font-family: monospace; line-height:1.5; color: #64748b;">
                > Lokal veri tabanı sorgulanıyor (VM: 20 hafıza aktif)...<br>
                > Vibranium / MAX Phase simülasyonu tetiklendi...<br>
                > Akustik empedans ve darbe dalgası analizi başlatıldı...<br>
                > RTX 3070 CUDA çekirdekleri optimize ediliyor...
            </div>
        </details>
    `;
    msgsEl.appendChild(thinkingDiv);
    msgsEl.scrollTop = msgsEl.scrollHeight;

    try {
        const r = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: txt })
        });
        const d = await r.json();

        // Yanıt gelince paneli kaldır
        thinkingDiv.remove();

        // JARVIS'in cevabını bas
        addMsg('bot', d.response || 'Veri akışı kesildi.');
        if(sbar) sbar.textContent = 'Sistem Hazır · Tur: ' + (d.turn || 0);

    } catch (e) {
        thinkingDiv.remove();
        addMsg('bot', '❌ SİSTEM HATASI: ' + e.message);
        if(sbar) sbar.textContent = 'HATA';
    }
    
    sBtn.disabled = false;
    inpEl.focus();
}

async function loadStats(){
  try{
    const r=await fetch('/stats'); const d=await r.json();
    document.getElementById('st0').textContent=d.turns||0;
    document.getElementById('st1').textContent=d.tools||0;
    document.getElementById('st2').textContent=d.memory||0;
    document.getElementById('st3').textContent='Modeller: '+(d.models||'');
  } catch(e){}
}

async function loadNotes(){
  try{
    const r=await fetch('/notes'); const d=await r.json();
    const el=document.getElementById('nlist');
    if(!d.notes||!d.notes.length){ el.innerHTML='<div style="color:#64748b">Henüz not yok.</div>'; return; }
    el.innerHTML=d.notes.slice().reverse().map(n=>
      `<div class="nitem"><div class="ncat">${n.category.toUpperCase()} · ${(n.created_at||'').slice(0,10)}</div><div>${esc(n.content)}</div></div>`
    ).join('');
  } catch(e){}
}

async function saveNote(){
  const c=document.getElementById('ntxt').value.trim();
  const cat=document.getElementById('ncat').value;
  if(!c){ alert('Not boş olamaz!'); return; }
  await fetch('/notes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content:c,category:cat})});
  document.getElementById('ntxt').value='';
  loadNotes();
}
</script>
</body>
</html>"""


@app.route("/")
def index():
    return HTML


@app.route("/chat", methods=["POST"])
def chat():
    global agent
    data = request.get_json()
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"response": "Mesaj boş."})
    try:
        response = agent.chat(message)
    except Exception as e:
        response = f"Hata: {e}"
    return jsonify({
        "response": response,
        "turn": getattr(agent, "turn_count", 0),
    })


@app.route("/stats")
def stats():
    global agent
    if agent is None:
        return jsonify({})
    return jsonify({
        "turns":  getattr(agent, "turn_count", 0),
        "tools":  getattr(agent, "tool_calls_total", 0),
        "memory": agent.memory.count() if hasattr(agent, "memory") else 0,
        "models": ", ".join(getattr(agent, "available_models", [])[:3]),
    })


@app.route("/notes", methods=["GET"])
def get_notes():
    try:
        from tools.tools import _load_notes
        return jsonify({"notes": _load_notes()})
    except Exception as e:
        return jsonify({"notes": [], "error": str(e)})


@app.route("/notes", methods=["POST"])
def save_note():
    try:
        data = request.get_json()
        from tools.tools import save_note as _save
        result = _save(data.get("content", ""), data.get("category", "genel"))
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    print("\n" + "="*50)
    print("  ⚡ JARVIS Web Arayüzü Başlatılıyor...")
    print("="*50 + "\n")
    _init_agent()

    def open_browser():
        import time; time.sleep(1.5)
        webbrowser.open("http://localhost:5000")
    threading.Thread(target=open_browser, daemon=True).start()

    print("  🌐 http://localhost:5000")
    print("  Durdurmak için: Ctrl+C\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
