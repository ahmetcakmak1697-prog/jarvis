# KART — STT Türkçeyi bozuyor: iki ayrı kusur, aynı semptom

**Kime:** Claude Code (VS Code) · **Veren:** Ahmet, 2026-09-14
**Dal:** `auto/opencode-deepseek` · **Taban:** `78e1b80`
**Sınıf:** Ölçüm + öneri. Ayar değişikliği **uygulanmaz**, önerilir.

---

## 0. Neden — canlı gözlem, 2026-09-14

Ahmet ilk kez JARVIS'le sesli konuştu. **Model tarafı çalıştı:**

```
Sen:    "Merhaba dostum iyi misin?"   (söylenen)
STT:    "Mahbubar dostum iyi misin?"  (duyulan)
Jarvis: "Efendim, iyiyim — sistemler yerinde, keyfim de. Siz nasılsınız?"
```

İkinci turda STT `Çalıklıya biliyor musun?` üretti; DeepSeek **uydurmadı**,
*"Çalıklı hakkında bilgim yok — bu konuşmanın kaydında öyle bir yer ya da
konu geçmiyor"* dedi. Doğru davranış.

Üçüncü turda hiç duymadı: `stt_no_input: no_speech_detected`.

**Sonuç: darboğaz artık modelde değil, kulakta.** Ve bu, 2026-09-09'da
`SES_HATTI_COZUMLEME` §4'te kaydedilen bulgunun doğrulanmasıdır —
*"'Türkçesi kötü' izlenimi kısmen Whisper'ı ölçüyor."* Model DeepSeek'e
geçti, bozulma sürüyor: **model değiştirmek STT'yi düzeltmiyor.**

## 1. İki ayrı kusur — karıştırma

### Kusur A — kelime bozulması

`voice/stt.py` mevcut ayarlar, hepsi hız için doğruluktan feragat:

| ayar | değer | nerede |
|---|---|---|
| `model_size` | `"small"` | `:352` varsayılan; `build_default_voice_io:184` de `"small"`, `main.py` **ezmiyor** |
| `beam_size` | `1` (greedy) | `:409` **kodda sabit**, dışarıdan geçilemiyor |
| `compute_type` | `"int8"` | `:355` |
| `device` | `"cpu"` | `:354` |

`device="cpu"` bilinçli ve gerekçesi kodda yazılı. **Doğrulandı
(2026-09-14):** `cublas64_12.dll`, `cudnn_ops64_9.dll`, `cublas64_11.dll`
— üçü de yok, PATH'te de yok. `ctranslate2` 4.8.1 kurulu ama CUDA
kütüphaneleri eksik. **GPU kaçış yolu kapalı**; doğruluk artışının bedeli
CPU'da süre olarak ödenecek.

Ayrıca VRAM dar: RTX 3070'in 6.040 MiB'ı Ollama'da, 1.979 MiB boş.

### Kusur B — cümle algılanmıyor / erken kesiliyor

```
DEFAULT_SILENCE_THRESHOLD = 0.01    (voice/stt.py:45)
DEFAULT_SILENCE_DURATION_S = 1.5    (:46)
```

Ahmet'in mikrofon ölçümü (`j0_mic_check.py`, 2026-09-09):

```
tepe rms     : 0.07968   > 0.01  ✓
ortalama rms : 0.00781   < 0.01  ✗
esik ustu    : 38/200 parca (%19)
```

**Ortalama konuşma seviyesi eşiğin altında.** Yalnız tepeler geçiyor.
`MicrophoneRecorder` 1,5 saniye ardışık sessizlik görünce cümleyi
bitiriyor — ortalama altta kalınca cümle içindeki doğal duraklamalar
"sessizlik" sayılabilir.

**Ve `j0_mic_check.py`'nin kör noktası bu:**

```python
if s["tepe"] < a.threshold:   # yalnız TEPE'ye bakıyor
```

Tepe eşiği geçtiği için "UYUMLU" dedi ve **kendi kriterine göre haklıydı**.
Kriter eksik: ortalama hiç sınanmıyor.

---

## 2. Görev

### ADIM 0 — Sabit ses kaydı al (her şeyin ön koşulu)

`VoiceListener.listen()` ses örneklerini transcriber'a verip **atıyor**
(`voice/stt.py:448-460`). Aynı kayıt üzerinde A/B yapılamıyor.

Bir sonda yaz: mikrofondan **10–15 Türkçe cümle** kaydeder ve WAV olarak
saklar. Ahmet cümleleri okur; **söylenen metin elle yazılır** — doğruluk
ölçümünün referansı budur.

> **Kayıtlar Ahmet'in sesidir. Repoya COMMIT EDİLMEZ.** Geçici dizinde
> kalır; `.gitignore`'a gerek yok, yol repo dışında seçilir. Raporda
> yalnız **metin** karşılaştırması yer alır, ses dosyası değil.

Cümleler gerçek kullanımı temsil etsin: selamlama, proje sorusu
("nerede kaldık"), teknik terim, Türkçe özel karakterler (ş, ğ, ı, İ).

### ADIM 1 — Kusur B: eşiği ölç ve öner

Kayıt sırasında **ortalama ve tepe rms** ayrıca yazılır.

`j0_mic_check.py`'nin teşhisine **ortalama kontrolü ekle**: tepe eşiği
geçse bile ortalama altındaysa uyarsın ve eşik önersin. Mevcut
`tepe * 0.4` formülü korunur; yeni dal için gerekçesi yazılır.

Bu bir **araç düzeltmesidir**, ayar değişikliği değil — `DEFAULT_SILENCE_THRESHOLD`'a
**dokunma.** Önerilen sayı rapora yazılır, Ahmet imzalar.

### ADIM 2 — Kusur A: doğruluk/süre matrisi

Aynı WAV kayıtları üzerinde, **CPU'da**:

| model | beam_size | ölç |
|---|---|---|
| `small` | 1 (mevcut) | doğruluk + süre |
| `small` | 5 | doğruluk + süre |
| `medium` | 1 | doğruluk + süre |
| `medium` | 5 | doğruluk + süre |

**Doğruluk nasıl ölçülür:** kelime hata oranı (WER) — referans metinle
karşılaştırma. Türkçe için **ASCII-fold uygulanmaz**; "ş" ile "s" farklı
kelimelerdir ve bu ölçümün konusu tam olarak odur.

**Süre neden kritik:** PUSULA bütçesi 1.500 ms ve STT o bütçenin
**içinde**. `medium` CPU'da `small`'un ~3 katı sürebilir. Doğruluk
kazanıp bütçeyi delmek çözüm değildir — her satırda **ikisi birden**
yazılır.

`medium` modeli diske iner (~1,5 GB). İndirme süresi ölçüme **dahil
edilmez**, ayrı not edilir.

### ADIM 3 — Öner, uygulama

Raporda:

1. Her kombinasyonun WER'i ve p50 süresi.
2. **Önerilen ayar ve üç gerekçesi** (ETAP 1 şablonu): ölçüldü mü,
   bütçeye sığıyor mu, oynaklık payı var mı.
3. `beam_size` şu an **kodda sabit** (`:409`). Değiştirilecekse
   dışarıdan geçilebilir olmalı — ama bu kartta **yapılmaz**, önerilir.
4. GPU seçeneği: `cublas64_12.dll` kurulursa tablo nasıl değişirdi?
   **Ölçme** — kurulum ayrı bir karardır. Yalnız "şu an kapalı, sebebi
   bu" diye yaz.

---

## 3. Sınırlar

- `voice/stt.py`'deki **hiçbir varsayılan değişmez.** Kart ölçer ve önerir.
- `j0_mic_check.py`'ye yalnız **teşhis dalı** eklenir (ADIM 1).
- Ses kayıtları **repoya girmez.**
- `agent/`, `eval/`, `agents/persona.py`: dokunma.
- Kapı: `pytest tests -q` **iki sırada**, `ruff check .` **≤ 283**.
- Push yok. ADIM 0 Ahmet'in konuşmasını gerektirir — **orada DUR ve iste.**

## 4. Bitti sayılma ölçütü

- Sonda var, 10–15 cümle kaydedildi, referans metin yazılı, kayıtlar
  repo dışında.
- Ortalama/tepe rms ölçüldü; `j0_mic_check.py` artık ortalama da sınıyor
  ve testi var.
- Dört kombinasyonun **WER ve süresi** yan yana.
- Önerilen ayar üç gerekçeyle yazılı; PUSULA bütçesine sığıp sığmadığı
  açık.
- Hiçbir varsayılan değişmedi (`git diff` yalnız sonda + mic_check
  teşhis dalı + rapor).
- Kapı iki sırada yeşil, ruff ≤ 283.
