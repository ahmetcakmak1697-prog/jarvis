"""
JARVIS Desktop v2 — Profesyonel Masaüstü Uygulaması
Çalıştır: python jarvis_desktop.py
"""
from __future__ import annotations
import sys, os, time, threading, webbrowser
from pathlib import Path

JARVIS_DIR = Path(__file__).parent
sys.path.insert(0, str(JARVIS_DIR))

from flask import Flask, request, jsonify
flask_app = Flask(__name__)
agent = None

def init_agent():
    global agent
    try:
        from dotenv import load_dotenv
        load_dotenv(JARVIS_DIR / ".env")
    except: pass
    try:
        from agent.local_agent import LocalJarvisAgent
        agent = LocalJarvisAgent()
        print("✓ JARVIS hazır")
    except Exception as e:
        print(f"Agent hatası: {e}")

def get_sysinfo():
    try:
        import psutil
        c = psutil.cpu_percent(interval=0.1)
        r = psutil.virtual_memory()
        return {"cpu": c, "ram_pct": r.percent,
                "ram_used": r.used//(1024**3), "ram_total": r.total//(1024**3)}
    except:
        return {"cpu": 0, "ram_pct": 0, "ram_used": 0, "ram_total": 32}

@flask_app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    msg = data.get("message","").strip()
    if not msg: return jsonify({"response":"Mesaj boş."})
    try: response = agent.chat(msg)
    except Exception as e: response = f"Hata: {e}"
    return jsonify({"response": response,
                    "turn": getattr(agent,"turn_count",0),
                    "tools": getattr(agent,"tool_calls_total",0)})

@flask_app.route("/api/sysinfo")
def api_sysinfo():
    from datetime import datetime
    s = get_sysinfo()
    n = datetime.now()
    days = ["PAZARTESİ","SALI","ÇARŞAMBA","PERŞEMBE","CUMA","CUMARTESİ","PAZAR"]
    s.update({
        "time": n.strftime("%H:%M:%S"), "date": n.strftime("%d.%m.%Y"),
        "day": days[n.weekday()],
        "models": ", ".join(getattr(agent,"available_models",[])[:2]) if agent else "—",
        "memory": agent.memory.count() if agent and hasattr(agent,"memory") and agent.memory else 0,
        "turns": getattr(agent,"turn_count",0),
        "tools_used": getattr(agent,"tool_calls_total",0),
    })
    return jsonify(s)

@flask_app.route("/api/clear", methods=["POST"])
def api_clear():
    if agent: agent.clear_history()
    return jsonify({"ok":True})

@flask_app.route("/api/notes", methods=["GET"])
def api_notes_get():
    try:
        from tools.tools import _load_notes
        return jsonify({"notes": _load_notes()})
    except: return jsonify({"notes":[]})

@flask_app.route("/api/notes", methods=["POST"])
def api_notes_post():
    try:
        d = request.get_json()
        from tools.tools import save_note
        return jsonify({"result": save_note(d.get("content",""), d.get("category","genel"))})
    except Exception as e: return jsonify({"error":str(e)})

@flask_app.route("/")
def index(): return HTML

HTML = r"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8"><title>JARVIS</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;900&family=Rajdhani:wght@300;400;600&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<style>
:root{
  --c: #00e5ff; --c2: #0097a7; --c3: #006064;
  --bg: #020c14; --bg2: #04151f; --bg3: #061a27;
  --glow: 0 0 8px #00e5ff, 0 0 20px #00e5ff33;
  --glow2: 0 0 6px #00e5ff66;
  --border: #00e5ff22;
}
*{margin:0;padding:0;box-sizing:border-box;}
html,body{width:100vw;height:100vh;overflow:hidden;background:var(--bg);}
body{font-family:'Rajdhani',sans-serif;color:var(--c);}

/* NOISE TEXTURE */
body::after{
  content:'';position:fixed;inset:0;
  background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
  pointer-events:none;z-index:9999;opacity:.4;
}

/* SCAN LINE */
body::before{
  content:'';position:fixed;top:-100%;left:0;width:100%;height:3px;
  background:linear-gradient(transparent,rgba(0,229,255,.15),transparent);
  animation:scan 12s linear infinite;z-index:9998;
}
@keyframes scan{to{top:110%;}}

/* HEX GRID */
.hexbg{
  position:fixed;inset:0;z-index:0;pointer-events:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='70'%3E%3Cpolygon points='40,3 77,22 77,48 40,67 3,48 3,22' fill='none' stroke='%2300e5ff' stroke-width='.4' opacity='.07'/%3E%3C/svg%3E");
  animation:hexMove 40s linear infinite;
}
@keyframes hexMove{0%{background-position:0 0}100%{background-position:80px 70px}}

/* CORNER DECO */
.corner{position:fixed;width:70px;height:70px;z-index:100;}
.corner::before,.corner::after{content:'';position:absolute;background:var(--c);box-shadow:var(--glow2);}
.corner::before{width:100%;height:1.5px;top:0;left:0;}
.corner::after{width:1.5px;height:100%;top:0;left:0;}
.corner.tl{top:16px;left:16px;}
.corner.tr{top:16px;right:16px;transform:scaleX(-1);}
.corner.bl{bottom:16px;left:16px;transform:scaleY(-1);}
.corner.br{bottom:16px;right:16px;transform:scale(-1);}
/* Animated corner dots */
.corner.tl::before{animation:cornerGlow 3s ease-in-out infinite;}
.corner.br::before{animation:cornerGlow 3s ease-in-out infinite .5s;}
@keyframes cornerGlow{0%,100%{box-shadow:var(--glow2)}50%{box-shadow:var(--glow)}}

/* HEADER */
.hdr{
  position:fixed;top:0;left:0;right:0;height:52px;z-index:500;
  display:flex;align-items:center;padding:0 90px;
  background:linear-gradient(180deg,rgba(2,12,20,.95) 0%,rgba(2,12,20,.0) 100%);
  border-bottom:1px solid var(--border);
}
.logo{
  font-family:'Orbitron',monospace;font-size:1.6em;font-weight:900;
  letter-spacing:10px;text-shadow:var(--glow);
  animation:logoAnim 5s ease-in-out infinite;
}
@keyframes logoAnim{0%,94%,100%{opacity:1;text-shadow:var(--glow)}95%{opacity:.5}97%{opacity:1}98%{opacity:.6}}
.hdr-mid{flex:1;text-align:center;}
.hdr-mid .sub{font-size:.62em;letter-spacing:5px;color:#00e5ff55;font-family:'Share Tech Mono',monospace;}
.hdr-right{text-align:right;}
#clock{font-family:'Orbitron',monospace;font-size:1.25em;text-shadow:var(--glow2);letter-spacing:3px;}
#hdate{font-size:.65em;color:#00e5ff66;margin-top:2px;letter-spacing:2px;}

/* LAYOUT */
.layout{
  position:fixed;top:52px;bottom:26px;left:0;right:0;
  display:grid;
  grid-template-columns:190px 1fr 190px;
  gap:0;z-index:10;
}

/* PANELS */
.panel{
  padding:10px 8px;display:flex;flex-direction:column;gap:8px;
  overflow:hidden;
}
.panel-left{border-right:1px solid var(--border);}
.panel-right{border-left:1px solid var(--border);}

.pbox{
  background:linear-gradient(135deg,rgba(4,21,31,.9),rgba(6,26,39,.7));
  border:1px solid var(--border);
  padding:10px 12px;
  position:relative;
  backdrop-filter:blur(8px);
  transition:border-color .3s;
}
.pbox:hover{border-color:#00e5ff44;}
.pbox::before{
  content:'';position:absolute;top:-1px;left:8px;
  width:24px;height:1.5px;
  background:var(--c);box-shadow:var(--glow2);
}
.plabel{
  font-size:.58em;letter-spacing:4px;color:#00e5ff55;
  margin-bottom:7px;font-family:'Share Tech Mono',monospace;
  text-transform:uppercase;
}
.pval{font-size:1.15em;font-weight:600;text-shadow:var(--glow2);}
.psmall{font-size:.75em;color:#00e5ff88;margin-top:3px;}

/* BAR */
.bar{background:#001824;height:3px;border-radius:2px;margin-top:5px;overflow:hidden;}
.bar-fill{height:100%;background:linear-gradient(90deg,var(--c3),var(--c));box-shadow:var(--glow2);transition:width .8s ease;}

/* ARC REACTOR */
.arc-wrap{display:flex;flex-direction:column;align-items:center;padding:12px 0;}
.arc{
  width:76px;height:76px;border-radius:50%;
  border:1px solid #00e5ff33;
  display:flex;align-items:center;justify-content:center;
  position:relative;
}
.arc-r1{position:absolute;inset:0;border-radius:50%;border:1px dashed #00e5ff22;animation:rot 20s linear infinite;}
.arc-r2{position:absolute;inset:8px;border-radius:50%;border:1px solid #00e5ff33;animation:rot 10s linear infinite reverse;}
.arc-r3{position:absolute;inset:16px;border-radius:50%;border:1px dashed #00e5ff44;animation:rot 6s linear infinite;}
.arc-core{
  width:22px;height:22px;border-radius:50%;z-index:1;
  background:radial-gradient(circle,#ffffff 0%,var(--c) 35%,transparent 70%);
  box-shadow:0 0 12px var(--c),0 0 25px var(--c),0 0 50px #00e5ff44;
  animation:corePulse 2.5s ease-in-out infinite;
}
@keyframes rot{to{transform:rotate(360deg)}}
@keyframes corePulse{0%,100%{transform:scale(1);box-shadow:0 0 12px var(--c),0 0 25px var(--c)}50%{transform:scale(1.1);box-shadow:0 0 18px var(--c),0 0 40px var(--c),0 0 60px #00e5ff44}}
.online-badge{
  margin-top:8px;font-size:.62em;letter-spacing:3px;
  color:#00e5ff88;font-family:'Share Tech Mono',monospace;
}
.online-dot{
  display:inline-block;width:5px;height:5px;border-radius:50%;
  background:#00ff88;box-shadow:0 0 6px #00ff88;margin-right:5px;
  animation:dotBlink 2s infinite;
}
@keyframes dotBlink{0%,100%{opacity:1}50%{opacity:.3}}

/* QUICK BTN */
.qbtn{
  width:100%;background:transparent;border:1px solid #00e5ff1a;
  color:#00e5ff66;font-family:'Share Tech Mono',monospace;
  font-size:.68em;padding:6px 8px;cursor:pointer;
  letter-spacing:1px;transition:all .25s;text-align:left;
  margin-bottom:4px;
}
.qbtn:hover{border-color:var(--c2);color:var(--c);background:#00e5ff0d;padding-left:14px;}
.qbtn::before{content:'▸ ';opacity:.5;}

/* CHAT AREA */
.chat-area{
  display:flex;flex-direction:column;
  padding:0 16px 0;overflow:hidden;
}

#msgs{
  flex:1;overflow-y:auto;padding:16px 4px;
  display:flex;flex-direction:column;gap:16px;
  scrollbar-width:thin;scrollbar-color:#00e5ff1a transparent;
}
#msgs::-webkit-scrollbar{width:3px;}
#msgs::-webkit-scrollbar-thumb{background:#00e5ff22;border-radius:2px;}

/* MESSAGE BUBBLES */
.mu{
  align-self:flex-end;max-width:68%;
  background:linear-gradient(135deg,#012030,#01344d);
  border:1px solid var(--c2);
  border-radius:10px 10px 2px 10px;
  padding:11px 16px;font-size:.9em;line-height:1.65;
  box-shadow:0 0 15px #00e5ff0d,inset 0 0 15px #00e5ff06;
  position:relative;animation:msgIn .3s ease;
}
.mu::after{
  content:'USER';position:absolute;top:-7px;right:10px;
  font-size:.5em;letter-spacing:3px;color:var(--c2);
  background:var(--bg);padding:0 5px;font-family:'Share Tech Mono',monospace;
}

.mb{
  align-self:flex-start;max-width:84%;
  background:linear-gradient(135deg,rgba(4,21,31,.95),rgba(6,26,39,.9));
  border:1px solid var(--border);
  border-radius:10px 10px 10px 2px;
  padding:13px 16px;font-size:.9em;line-height:1.75;
  position:relative;animation:msgIn .3s ease;
  backdrop-filter:blur(4px);
}
.mb::after{
  content:'⚡ JARVIS';position:absolute;top:-7px;left:10px;
  font-size:.5em;letter-spacing:3px;color:var(--c);
  background:var(--bg);padding:0 5px;text-shadow:var(--glow2);
  font-family:'Share Tech Mono',monospace;
}
.mb-text{white-space:pre-wrap;word-wrap:break-word;}

.mthink{
  align-self:flex-start;padding:9px 16px;
  border:1px dashed #00e5ff1a;font-size:.82em;
  color:#00e5ff44;font-style:italic;
  animation:thinkPulse 1.2s ease-in-out infinite;
}
@keyframes thinkPulse{0%,100%{opacity:.4;border-color:#00e5ff1a}50%{opacity:1;border-color:#00e5ff44}}
@keyframes msgIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}

/* TYPING DOTS */
.tdots span{
  display:inline-block;width:5px;height:5px;background:var(--c);
  border-radius:50%;margin:0 2px;animation:tdot 1.2s infinite;
}
.tdots span:nth-child(2){animation-delay:.2s;}
.tdots span:nth-child(3){animation-delay:.4s;}
@keyframes tdot{0%,80%,100%{transform:translateY(0);opacity:.3}40%{transform:translateY(-6px);opacity:1}}

/* INPUT */
.input-zone{
  padding:10px 4px 12px;
  border-top:1px solid var(--border);
  position:relative;
}
.input-zone::before{
  content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,var(--c3),transparent);
}
.input-row{display:flex;align-items:center;gap:12px;}
.inp-pre{
  font-family:'Share Tech Mono',monospace;font-size:.8em;
  color:var(--c2);letter-spacing:2px;white-space:nowrap;
  animation:preAnim 2s ease-in-out infinite;
}
@keyframes preAnim{0%,100%{color:var(--c2)}50%{color:var(--c)}}
#inp{
  flex:1;background:transparent;border:none;
  border-bottom:1px solid #00e5ff33;
  color:var(--c);font-family:'Rajdhani',sans-serif;
  font-size:.95em;font-weight:600;padding:7px 4px;
  outline:none;caret-color:var(--c);letter-spacing:.5px;
  transition:border-color .3s;
}
#inp:focus{border-bottom-color:var(--c);}
#inp::placeholder{color:#00e5ff22;}
.sbtn{
  background:transparent;border:1px solid var(--c2);
  color:var(--c);font-family:'Orbitron',monospace;
  font-size:.65em;letter-spacing:3px;padding:8px 18px;
  cursor:pointer;transition:all .25s;white-space:nowrap;
}
.sbtn:hover{background:var(--c2);color:var(--bg);box-shadow:var(--glow);}
.sbtn:disabled{opacity:.25;cursor:not-allowed;}

/* QUICK ROW */
.qrow{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;}
.qchip{
  background:transparent;border:1px solid #00e5ff15;
  color:#00e5ff55;font-family:'Share Tech Mono',monospace;
  font-size:.68em;padding:4px 12px;cursor:pointer;
  letter-spacing:1px;transition:all .25s;border-radius:2px;
}
.qchip:hover{border-color:var(--c2);color:var(--c);background:#00e5ff0d;}

/* SCREENSAVER */
#ss{
  position:fixed;inset:0;background:var(--bg);
  z-index:9000;display:none;align-items:center;
  justify-content:center;flex-direction:column;cursor:pointer;
}
#ss.on{display:flex;}
.ss-rings{position:absolute;display:flex;align-items:center;justify-content:center;}
.ss-ring{
  position:absolute;border-radius:50%;border:1px solid transparent;
}
.r1{width:200px;height:200px;border-color:#00e5ff11;animation:rot 25s linear infinite;}
.r2{width:320px;height:320px;border-color:#00e5ff09;animation:rot 40s linear infinite reverse;}
.r3{width:460px;height:460px;border-color:#00e5ff06;animation:rot 60s linear infinite;}
.r4{width:620px;height:620px;border-color:#00e5ff04;animation:rot 80s linear infinite reverse;}
.ss-logo{
  font-family:'Orbitron',monospace;font-size:4.5em;font-weight:900;
  letter-spacing:18px;z-index:1;
  text-shadow:0 0 20px var(--c),0 0 60px var(--c),0 0 120px #00e5ff44;
  animation:ssPulse 4s ease-in-out infinite;
}
.ss-sub{
  font-family:'Share Tech Mono',monospace;
  font-size:.7em;letter-spacing:8px;color:#00e5ff55;
  margin-top:12px;z-index:1;animation:ssPulse 4s ease-in-out infinite .8s;
}
.ss-time{
  font-family:'Orbitron',monospace;font-size:2.5em;
  letter-spacing:6px;margin-top:32px;z-index:1;
  text-shadow:var(--glow2);animation:ssPulse 4s ease-in-out infinite 1.2s;
}
.ss-hint{
  position:absolute;bottom:28px;font-family:'Share Tech Mono',monospace;
  font-size:.6em;color:#00e5ff22;letter-spacing:5px;
  animation:ssPulse 2s ease-in-out infinite;
}
@keyframes ssPulse{0%,100%{opacity:.65}50%{opacity:1}}

/* BOTTOM */
.btm{
  position:fixed;bottom:0;left:0;right:0;height:26px;z-index:500;
  border-top:1px solid var(--border);
  background:linear-gradient(0deg,rgba(2,12,20,.95) 0%,transparent 100%);
  display:flex;align-items:center;padding:0 90px;gap:30px;
  font-family:'Share Tech Mono',monospace;font-size:.58em;color:#00e5ff33;letter-spacing:2px;
}
#sbar{flex:1;}
</style>
</head>
<body>
<div class="hexbg"></div>
<div class="corner tl"></div><div class="corner tr"></div>
<div class="corner bl"></div><div class="corner br"></div>

<!-- HEADER -->
<div class="hdr">
  <div class="logo">JARVIS</div>
  <div class="hdr-mid">
    <div class="sub">JUST A RATHER VERY INTELLIGENT SYSTEM</div>
  </div>
  <div class="hdr-right">
    <div id="clock">--:--:--</div>
    <div id="hdate">— —</div>
  </div>
</div>

<!-- LAYOUT -->
<div class="layout">

  <!-- LEFT PANEL -->
  <div class="panel panel-left">
    <div class="arc-wrap">
      <div class="arc">
        <div class="arc-r1"></div><div class="arc-r2"></div><div class="arc-r3"></div>
        <div class="arc-core"></div>
      </div>
      <div class="online-badge"><span class="online-dot"></span>ONLINE</div>
    </div>

    <div class="pbox">
      <div class="plabel">CPU</div>
      <div class="pval" id="cpu">—</div>
      <div class="bar"><div class="bar-fill" id="cpubar" style="width:0"></div></div>
    </div>

    <div class="pbox">
      <div class="plabel">BELLEK</div>
      <div class="pval" id="ram">—</div>
      <div class="bar"><div class="bar-fill" id="rambar" style="width:0"></div></div>
      <div class="psmall" id="ramdet">—</div>
    </div>

    <div class="pbox">
      <div class="plabel">SİSTEM</div>
      <div class="psmall" style="color:var(--c)">RTX 3070 8GB</div>
      <div class="psmall">RYZEN 5 7600</div>
      <div class="psmall">32 GB DDR5</div>
    </div>

    <div class="pbox">
      <div class="plabel">AKTİF MODEL</div>
      <div class="psmall" id="mdl" style="color:var(--c);line-height:1.6">—</div>
    </div>
  </div>

  <!-- CHAT -->
  <div class="chat-area">
    <div id="msgs">
      <div class="mb"><div class="mb-text">Sistemler aktif. Merhaba efendim. Ben JARVIS — kişisel AI asistanınızım. Web araştırması, veri analizi, hesaplama ve daha fazlasını yapabilirim. Nasıl yardımcı olabilirim?</div></div>
    </div>
    <div class="input-zone">
      <div class="input-row">
        <span class="inp-pre">▶ //</span>
        <input id="inp" type="text" placeholder="KOMUT GİRİN..." autocomplete="off"/>
        <button class="sbtn" id="sbtn" onclick="send()">EXECUTE</button>
      </div>
      <div class="qrow">
        <button class="qchip" onclick="qs('Türkiye gündem haberlerini araştır')">🌐 GÜNDEM</button>
        <button class="qchip" onclick="qs('Polimer endüstrisindeki son gelişmeleri araştır')">⚗ POLİMER</button>
        <button class="qchip" onclick="qs('İş güvenliği mevzuatında son değişiklikler')">⚠ İŞ GÜV</button>
        <button class="qchip" onclick="qs('Notlarımı göster')">📋 NOTLAR</button>
        <button class="qchip" onclick="qs('Kendini tanıt ve yeteneklerini anlat')">🤖 YETENEKLERİN</button>
        <button class="qchip" onclick="clearChat()">✕ TEMİZLE</button>
      </div>
    </div>
  </div>

  <!-- RIGHT PANEL -->
  <div class="panel panel-right">
    <div class="pbox">
      <div class="plabel">KONUŞMA</div>
      <div class="pval" id="s-turns">0</div>
      <div class="psmall">TOPLAM TUR</div>
    </div>
    <div class="pbox">
      <div class="plabel">ARAÇ ÇAĞRISI</div>
      <div class="pval" id="s-tools">0</div>
      <div class="psmall">KULLANILAN</div>
    </div>
    <div class="pbox">
      <div class="plabel">HAFIZA</div>
      <div class="pval" id="s-mem">0</div>
      <div class="psmall">KAYIT</div>
    </div>
    <div class="pbox">
      <div class="plabel">MALİYET</div>
      <div class="pval" style="color:#00ff88;text-shadow:0 0 10px #00ff88">0₺</div>
      <div class="psmall">100% LOKAL</div>
    </div>
    <div class="pbox">
      <div class="plabel">HIZLI ERİŞİM</div>
      <button class="qbtn" onclick="qs('Saat kaç, tarih nedir?')">SAAT / TARİH</button>
      <button class="qbtn" onclick="qs('Güncel haber başlıklarını araştır')">SON HABERLER</button>
      <button class="qbtn" onclick="qs('sqrt(144) + sin(pi/4) hesapla')">HESAP MAK.</button>
      <button class="qbtn" onclick="qs('Kendini geliştirmek için ne önerirsin?')">GELİŞİM</button>
    </div>
  </div>
</div>

<!-- BOTTOM -->
<div class="btm">
  <span id="sbar">SİSTEM HAZIR</span>
  <span>JARVIS v2.0</span>
  <span>LOKAL · GÜVENLİ · ÜCRETSİZ</span>
  <span id="bdate">—</span>
</div>

<!-- SCREENSAVER -->
<div id="ss" onclick="wakeUp()">
  <div class="ss-rings">
    <div class="ss-ring r1"></div><div class="ss-ring r2"></div>
    <div class="ss-ring r3"></div><div class="ss-ring r4"></div>
  </div>
  <div class="ss-logo">JARVIS</div>
  <div class="ss-sub">JUST A RATHER VERY INTELLIGENT SYSTEM</div>
  <div class="ss-time" id="ss-clk">--:--</div>
  <div class="ss-hint">DEVAM ETMEK İÇİN TIKLAYIN</div>
</div>

<script>
const msgsEl=document.getElementById('msgs');
const inpEl=document.getElementById('inp');
const sBtn=document.getElementById('sbtn');

// CLOCK
function tick(){
  const n=new Date();
  const t=n.toLocaleTimeString('tr-TR');
  document.getElementById('clock').textContent=t;
  document.getElementById('ss-clk').textContent=t.slice(0,5);
  const days=['PAZAR','PAZARTESİ','SALI','ÇARŞAMBA','PERŞEMBE','CUMA','CUMARTESİ'];
  const ds=n.toLocaleDateString('tr-TR');
  document.getElementById('hdate').textContent=days[n.getDay()]+' · '+ds;
  document.getElementById('bdate').textContent=ds;
}
setInterval(tick,1000);tick();

// SYS INFO
async function sysinfo(){
  try{
    const d=await(await fetch('/api/sysinfo')).json();
    document.getElementById('cpu').textContent=d.cpu.toFixed(1)+'%';
    document.getElementById('cpubar').style.width=d.cpu+'%';
    document.getElementById('ram').textContent=d.ram_pct.toFixed(1)+'%';
    document.getElementById('rambar').style.width=d.ram_pct+'%';
    document.getElementById('ramdet').textContent=d.ram_used+'GB / '+d.ram_total+'GB';
    document.getElementById('mdl').textContent=d.models||'—';
    document.getElementById('s-turns').textContent=d.turns||0;
    document.getElementById('s-tools').textContent=d.tools_used||0;
    document.getElementById('s-mem').textContent=d.memory||0;
  }catch(e){}
}
setInterval(sysinfo,3000);sysinfo();

// SCREENSAVER
let idle=null;
const IDLE=5*60*1000;
function resetIdle(){clearTimeout(idle);idle=setTimeout(()=>document.getElementById('ss').classList.add('on'),IDLE);}
function wakeUp(){document.getElementById('ss').classList.remove('on');resetIdle();}
['mousemove','keydown','click'].forEach(e=>document.addEventListener(e,resetIdle));
resetIdle();

// ENTER
inpEl.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();send();}});

function esc(t){return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>');}

function addMsg(cls,html){
  const d=document.createElement('div');
  d.className=cls;
  if(cls==='mb') d.innerHTML='<div class="mb-text">'+esc(html)+'</div>';
  else d.textContent=html;
  msgsEl.appendChild(d);
  msgsEl.scrollTo({top:msgsEl.scrollHeight,behavior:'smooth'});
  return d;
}

function qs(t){inpEl.value=t;send();}

async function send(){
  const txt=inpEl.value.trim();
  if(!txt||sBtn.disabled)return;
  inpEl.value='';
  sBtn.disabled=true;
  document.getElementById('sbar').textContent='İŞLENİYOR...';
  addMsg('mu',txt);

  // Typing indicator
  const th=document.createElement('div');
  th.className='mb mthink';
  th.innerHTML='<div class="tdots"><span></span><span></span><span></span></div>';
  msgsEl.appendChild(th);
  msgsEl.scrollTo({top:msgsEl.scrollHeight,behavior:'smooth'});

  try{
    const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:txt})});
    const d=await r.json();
    th.remove();
    addMsg('mb',d.response||'YANIT ALINAMADI');
    document.getElementById('sbar').textContent='HAZIR · TUR: '+(d.turn||0)+' · ARAÇ: '+(d.tools||0);
    sysinfo();
  }catch(e){
    th.remove();
    addMsg('mb','⚠ BAĞLANTI HATASI: '+e.message);
    document.getElementById('sbar').textContent='HATA';
  }
  sBtn.disabled=false;
  inpEl.focus();
}

async function clearChat(){
  await fetch('/api/clear',{method:'POST'});
  msgsEl.innerHTML='';
  addMsg('mb','Geçmiş temizlendi efendim. Hazırım.');
  document.getElementById('sbar').textContent='SİSTEM HAZIR · GEÇMİŞ TEMİZLENDİ';
}

inpEl.focus();
</script>
</body>
</html>"""

def start_flask():
    flask_app.run(host="127.0.0.1", port=5001, debug=False, use_reloader=False)

if __name__=="__main__":
    print("\n"+"═"*52)
    print("  ⚡  J A R V I S  v2.0")
    print("═"*52+"\n")
    init_agent()
    threading.Thread(target=start_flask,daemon=True).start()
    time.sleep(1.5)
    try:
        import webview
        print("  🖥  Pencere açılıyor...")
        webview.create_window("JARVIS","http://127.0.0.1:5001",
            width=1440,height=900,min_size=(1100,650),background_color="#020c14")
        webview.start(debug=False)
    except ImportError:
        print("  🌐  http://127.0.0.1:5001")
        webbrowser.open("http://127.0.0.1:5001")
        flask_app.run(host="127.0.0.1",port=5001,debug=False)
