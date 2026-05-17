# Faz -1 / 0 / 1 Kontrol Notları

Bu yama üç şeyi düzeltir:

1. Snapshot boot güvenliği
   - `agents/` klasörü yoksa `jarvis_server.py` import sırasında çökmez.
   - Eksik agent modülleri için Null fallback sınıfları eklendi.
   - `requirements.txt` eklendi.

2. Ana chat blokajı
   - `jarvis_brain.chat()` yeniden düzenlendi.
   - Başarılı LLM yolunda artık cevap kesinlikle `return` edilir.
   - `_should_remember()` ve `_handle_explicit_memory()` temiz ayrıldı.
   - Önceki ölü kod kaldırıldı.
   - `chat()` hiçbir path'te `None` döndürmemeli.

3. Server chat çağrısı
   - `/chat` ve `/ws/chat` içinde `brain.chat()` `asyncio.to_thread()` ile çalışır.
   - WebSocket `NoneType.split()` hatasına karşı sigortalandı.

## Çalıştırma

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python jarvis_server.py
```

## Minimum test

```bash
python -m py_compile jarvis_brain.py jarvis_server.py
python -c "from jarvis_brain import JarvisBrain; b=JarvisBrain(); r=b.chat('merhaba'); print(type(r), r[:120])"
```

Not: Ollama kapalıysa test cevap yerine kontrollü hata döndürür; bu normaldir. Önemli olan `None` dönmemesidir.
