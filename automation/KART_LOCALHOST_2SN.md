# KART — `localhost` her istekte 2 saniye yakıyor (kapsamı ölçüldü)

**Kime:** Claude Code (VS Code) · **Veren:** Ahmet, 2026-09-13
**Dal:** `auto/opencode-deepseek` · **Taban:** `a692d87`
**Sınıf:** Düpedüz hata — **imza gerekmiyor.** Doğru davranış tartışmalı değil.

---

## 0. Ölçüm (bağımsız doğrulandı, 2026-09-13)

```
socket.create_connection, 5 deneme, bu makine:

  localhost    p50  2057,63 ms   (min 2031,83  max 2099,20)
  127.0.0.1    p50     0,25 ms   (min    0,22  max    0,26)

urllib + /api/tags, 3 deneme:

  http://localhost:11434    p50  2039,3 ms
  http://127.0.0.1:11434    p50    15,1 ms
```

**~8200 kat.** Bu makinede `localhost` önce IPv6'ya (`::1`) çözülüyor,
Ollama orayı dinlemiyor, bağlantı zaman aşımına uğrayıp IPv4'e düşüyor.
Her istek bu bedeli ödüyor.

## 1. KAPSAM — ses yolu ETKİLENMEMİŞ

Bu, kartın en önemli maddesi ve panik ile gerçeği ayırıyor.

`agent/local_agent.py` Ollama'ya **`ollama` Python paketiyle** gidiyor
(`:590` `import ollama`, `:918` `self._ollama.chat(...)`). Ölçüldü:

```
ollama paketi varsayilan base_url : http://127.0.0.1:11434
ollama.list() p50                 : 3,0 ms
OLLAMA_HOST env                   : tanimsiz
```

**Paket zaten `127.0.0.1` çözüyor.** Ses yolu, `scripts/olc_llm_anatomisi.py`
(o da `ajan._ollama.chat` kullanıyor) ve dünkü gecikme sayıları
(llama 464 / 1160 / 15890 ms) **temiz ve geçerli.**

### Etkilenenler — `urllib`/`requests` ile doğrudan `localhost` yazanlar

| Nerede | Ne | Dokunulsun mu |
|---|---|---|
| `config/runtime_profiles.json` | üç profilde `ollama_url` | **EVET** |
| `eval/run_turkish_quality.py:529` | `/api/generate` | **EVET** |
| `eval/run_turkish_quality.py:572` | `/api/tags` | **EVET** |
| `agents/ollama_executor.py:92` | fallback dize | **EVET** |
| `agents/model_registry.py:44,181` | varsayılan + fallback | **EVET** |
| `agents/daily_digest.py:32` | park edilmiş cephe | **HAYIR** (§9) |
| `agents/orchestrator.py:27` | park edilmiş cephe | **HAYIR** (§9) |
| `agents/proactive_agent.py:77` | park edilmiş cephe | **HAYIR** (§9) |
| `agents/self_improver.py:46` | park edilmiş cephe | **HAYIR** (§9) |

Park edilmiş cephelere dokunmak §9 ihlalidir. Kusuru **gör, söyle, silme** —
bu kart onları listeler, düzeltmez.

## 2. Görev

### ADIM 1 — Önce düşen testi yaz, KIRMIZI GÖR

- İzlenen üretim yollarında (`config/runtime_profiles.json`,
  `agents/model_registry.py`, `agents/ollama_executor.py`,
  `eval/run_turkish_quality.py`) `localhost:11434` **geçmiyor**.
- Park edilmiş dört dosya bu testin kapsamı **dışında** ve bu bilerek —
  testin docstring'i sebebini yazsın, yoksa biri "eksik" sanıp genişletir.

### ADIM 2 — Değiştir

`localhost` → `127.0.0.1`. Başka hiçbir şeye dokunma.

`ollama` paketini kullanan yollar zaten doğru; **onlara dokunma.**

### ADIM 3 — Kazancı ÖLÇ

Düzeltmeden önce ve sonra, aynı koşu:

```
python eval/run_turkish_quality.py --model llama3.1:latest --limit 5
```

Toplam süre yazılır. Beklenen: vaka başına ~2 saniye düşüş (5 vakada
~10 s). **Düşmezse söyle** — o zaman teşhis eksik demektir.

Ayrıca: bu düzeltme **puanları değiştirmemeli.** Kalite koşusunun
sonucu (aynı model, aynı vakalar) aynı kalmalı; yalnız süre düşmeli.
Değişirse **DUR** — süre düzeltmesi puana dokunuyorsa başka bir şey
olmuş demektir.

## 3. Sınırlar

- Park edilmiş dört dosya (`daily_digest`, `orchestrator`,
  `proactive_agent`, `self_improver`): **DOKUNMA** (§9).
- `agent/local_agent.py`, `voice/`: dokunmaya **gerek yok**, zaten temiz.
- Kalite eşikleri, dedektörler, `passing_threshold`: dokunma.
- Kapı: `pytest tests -q` **iki sırada**, `ruff check .` **≤ 283**.
- Push yok. Bitince **DUR**.

## 4. Bitti sayılma ölçütü

- Test var, önce kırmızı görüldü; park edilmiş dosyaların kapsam dışı
  olduğu docstring'de gerekçeli.
- İzlenen üretim yollarında `localhost:11434` kalmadı.
- Kazanç **ölçüldü** ve öncesi/sonrası süre yazılı.
- Aynı koşunun **puanı değişmedi** (yalnız süre düştü).
- Kapı iki sırada yeşil, ruff ≤ 283.
