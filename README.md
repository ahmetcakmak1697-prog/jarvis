# 🤖 JARVIS v5 — OPERATION OVERMIND

> Iron Man'in JARVIS'i tarzında, **%100 lokal**, sürekli öğrenen, proaktif AI asistan.
> Türkçe konuşur, hallucination yapmaz, bilmediğini araştırır, sen uyurken çalışır.

---

## 🎯 ÖZELLİKLER (22 + 1 ekstra)

### Beyin
- 🧠 **Multi-step reasoning** — Düşün → Araştır → Cevapla
- 🚫 **Hallucination shield** — Bilmediğini söyler, asla uydurmaz
- 🎯 **Confidence-aware** — Güven skorla, düşükse araştır
- 💾 **Vector memory** (ChromaDB) — Geçmişi anlamca hatırlar

### Araştırma
- 🌐 **Multi-source** — Wikipedia (TR/EN) + Google + DuckDuckGo + ArXiv
- 📚 **Cache** — Aynı soruyu iki kez aramaz

### Doküman
- 📄 **PDF/Excel/Word/CSV oku** — Yükle, sor, analiz al
- 📝 **Excel/Word/PDF üret** — Rapor hazırlatabilirsin

### Ses
- 🎤 **Whisper (local)** — Mikrofona Türkçe konuş
- 🔊 **Edge-TTS** — Türkçe sesli cevap

### Otonom
- 🌅 **Sabah brifingi** (08:00 otomatik)
- 🌙 **Akşam özeti** (22:00 otomatik)
- 🧪 **Gece curation** (02:00 — verileri puanlar)
- 🔍 **Self-improvement** — Saatlik zayıflık analizi
- 📊 **Günlük özet** (23:00 — günü özetler)

### Görev & Skill
- ⚙️ **Task Queue** — Paralel görev kuyruğu
- 📚 **Skill Library** — Tekrarlanan işleri öğrenir

### Sistem
- 🔧 **Health Monitor** — Düşerse kendini onarır
- 🌐 **Web UI + API** — Telefondan da kullan
- 🚀 **Tek komut çalıştırma** — `python auto_runner.py`

---

## 🚀 KURULUM (5 dakika)

### 1. Eski klasörü yedekle
```powershell
Copy-Item C:\Users\Ahmedov\Desktop\Jarvis\jarvis -Destination C:\Users\Ahmedov\Desktop\Jarvis\jarvis_BACKUP -Recurse
```

### 2. Yeni dosyaları yerleştir
ZIP'i aç, içindekileri `C:\Users\Ahmedov\Desktop\Jarvis\jarvis\` içine kopyala.
**Üzerine yaz** dediğinde **Evet**.

### 3. Setup'ı çalıştır
```powershell
cd C:\Users\Ahmedov\Desktop\Jarvis\jarvis
.\venv\Scripts\Activate.ps1
python setup.py
```

### 4. Ollama hazır mı?
```powershell
ollama list
# mistral-nemo:latest görmelisin. Yoksa:
ollama pull mistral-nemo
```

---

## ▶️ ÇALIŞTIRMA

### Tek komut, her şey 7/24 (önerilen)
```powershell
python auto_runner.py
```
Bu komut:
- Server'ı başlatır (port 8000)
- Ngrok başlatır (dünyaya açar)
- Scheduler aktive eder (sabah/akşam brifing, gece curation)
- Health monitor çalışır (5 dakikada bir kontrol)

### Sadece web server
```powershell
python jarvis_server.py
```

### Dashboard görmek için
```powershell
python training/dashboard.py
```

---

## 🎮 KULLANIM

### Web arayüzü
- **Sohbet sekmesi**: Yaz veya 🎤 ile konuş
- **Brifing sekmesi**: Sabah/akşam özetleri
- **Doküman sekmesi**: PDF/Excel/Word yükle, soru sor
- **Durum sekmesi**: Tüm istatistikler, JARVIS'in sana sorduğu şeyler

### Komut satırı
```powershell
# Curation manuel
python training/data_curator.py --once

# Dashboard
python training/dashboard.py

# Format migration
python training/migrate_format.py

# Günlük özet
python training/conversation_summarizer.py
```

### API endpoints (programatik)
- `POST /chat` — `{message: "..."}` → cevap
- `POST /speak` — Metin → MP3
- `POST /transcribe` — Audio → Metin (Whisper)
- `POST /upload_doc` — Dosya analizi
- `GET /briefing/morning` — Sabah brifingi
- `GET /briefing/evening` — Akşam özeti
- `POST /reminder` — Hatırlatma ekle
- `POST /task` — Görev kuyruğa
- `GET /improvement/analyze` — Zayıflık analizi
- `GET /skills` — Skill listesi

---

## 🔧 SORUN ÇÖZME

### "ChromaDB yok"
```powershell
pip install chromadb
```

### "TTS çalışmıyor"
```powershell
pip install edge-tts
```

### "Whisper yok"
```powershell
pip install faster-whisper
```

### Server başlamıyor (port 8000 dolu)
```powershell
Get-Process python | Stop-Process -Force
python jarvis_server.py
```

### Ngrok hatası
```powershell
Get-Process ngrok | Stop-Process -Force
python jarvis_server.py
```

### Database hatası ("table chats has no column...")
```powershell
Remove-Item memory\jarvis_memory.db
python jarvis_server.py
```

---

## 📊 NASIL ÖĞRENİYOR?

```
Sen konuşuyorsun
  ↓
JARVIS kayıt eder (conversations.json + ChromaDB)
  ↓
Gece 02:00: Otomatik puanlama (kalite skoru 1-10)
  ↓
Yüksek puanlılar (≥7) → train_data.jsonl
  ↓
Saatlik: Self-improvement zayıflık tespiti
  ↓
Veri 50+ olunca: Fine-tuning hazır (donanım upgrade'inde)
```

---

## 🎯 ROADMAP

- [x] v1: Temel chat
- [x] v2: Sistem komutu + araştırma
- [x] v3: Database + öğrenme
- [x] v4: Hallucination shield
- [x] **v5: 22 özellik tam paket** ← BURADAYIZ
- [ ] v6: Fine-tuning (2x3090 ile)
- [ ] v7: Kamera/görsel (LLaVA)
- [ ] v8: Akıllı ev (Home Assistant)

---

## 📂 DOSYA YAPISI

```
jarvis/
├── jarvis_brain.py              ⭐ Ana beyin
├── jarvis_server.py             🌐 Web server
├── auto_runner.py               🚀 7/24 orkestrator
├── setup.py                     📦 Kurulum
├── requirements.txt             📋 Bağımlılıklar
├── README.md                    📖 Bu dosya
├── tools/
│   ├── web_research.py          🌐 Multi-source araştırma
│   ├── vector_memory.py         🧠 Anlamsal hafıza
│   ├── document_reader.py       📄 PDF/Excel/Word okur
│   ├── document_writer.py       📝 Rapor üretir
│   ├── voice_io.py              🎤 Whisper + TTS
│   ├── browser_agent.py         🌐 Web kontrolü
│   └── system_control.py        💻 (mevcut)
├── agents/
│   ├── self_improver.py         🔍 Zayıflık tespit
│   ├── proactive_agent.py       🌅 Brifing
│   ├── task_executor.py         ⚙️ Görev kuyruğu
│   └── skill_library.py         📚 Skill öğrenme
└── training/
    ├── quality_evaluator.py     ⭐ Otomatik puanlama
    ├── data_curator.py          🌙 Gece curation
    ├── dashboard.py             📊 Görsel rapor
    ├── migrate_format.py        🔄 Eski veri çevir
    └── conversation_summarizer.py 📝 Günlük özet
```

---

**Sahibi:** Ahmet Fırat
**Versiyon:** 5.0 — OPERATION OVERMIND
**Donanım:** RTX 3070 (8GB) — Mistral-Nemo 12B Q4
