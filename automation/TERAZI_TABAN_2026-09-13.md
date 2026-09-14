# Yeni tanımın tabanı kaydedildi · söz ödendi

**Ölçen:** Claude Code · **Tarih:** 2026-09-13 · **Dal:** `auto/opencode-deepseek`
**Kart:** `automation/KART_400_UYGULA_VE_TABAN.md` · **Başlangıç HEAD:** `b6c930d`
**Ham veri:** `automation/KALITE_llama3.1_latest_20260913-0228.json`,
`automation/KALITE_deepseek_deepseek-chat_20260913-0230.json` (yanlarında `.md`)

---

## 0. Özet

- **Taban kaydedildi:** `llama3.1:latest` **52/64**, `deepseek/deepseek-chat`
  **59/64** (1'i ağ ölümü) → `passing_threshold.yeni_tanim_2026_09_13`. 2026-09-10'dan
  beri bekleyen "yeni tanımdaki taban ETAP 2'de ölçülecek" sözü ödendi.
- **`length` ile biten vaka yok.** llama 64/64 `stop`; DeepSeek 63 `stop` + 1 ağ
  hatası. `t1_mix_002` çarpmadı.
- **ETAP 5'in CONCERN'ü kapandı:** 400'de kesilen üç DeepSeek turkish vakası
  2000'de kendiliğinden durdu ve geçti — 430, 543, 439 token.
- **Bir kayıt düzeltildi:** 49/64'ün cevapları 1200 ile değil, **bütün vakalar
  400** bütçeyle üretilmişti (§3.2).

> **Tek koşu hüküm değildir** (A11). İki sayı da tek koşudur; eski tanımın
> 49/64'üyle ve ETAP 2/ETAP 5'in ara sayılarıyla **karşılaştırılamaz**.

---

## 1. ADIM 1 — Bütçe nereye yazıldı: `DEFAULT_NUM_PREDICT`

`eval/run_turkish_quality.py` — `DEFAULT_NUM_PREDICT` 400 → **2000**
(`61b1ce3`). Longform'un 4000'i vaka dosyasında beyanlı ve **değişmedi.**

**Neden bu yer** (kart §3: hangisi daha az yeri değiştiriyorsa):

| seçenek | değişen yer | yan etki |
|---|---|---|
| **`DEFAULT_NUM_PREDICT`** | **1 satır** | bütçe kararı `run_suite`'te zaten varsayılandan okunuyor; `test_quality_runner.py` beklenen değeri 400 → 2000 |
| vaka dosyası | 60 alan | `test_longform_butcesi.py:94` longform dışında bütçe beyan eden vakanın 400 olmasını şart koşuyor + `test_only_longform_cases_declare_a_larger_budget` yalnız longform'un beyan etmesini şart koşuyor — iki test kırılırdı |

**Test-first:**

- `tests/test_kisa_vaka_butcesi.py` (yeni) — 60 kısa vakanın bütçesi sondada
  ölçülen en uzun doğal cevabın (644) üstünde. Önce kırmızı: 60/60 vaka 400.
- `tests/test_quality_runner.py::test_only_longform_cases_declare_a_larger_budget`
  — beklenen varsayılan 400 → 2000. Koruduğu sözleşme (bütçeyi yalnız longform
  beyan eder) değişmedi; imzanın yeri docstring'e yazıldı. Önce kırmızı.

**Sıra:** kartın uyarısı gereği önce `KART_LOCALHOST_2SN` yapıldı (`5ebf4aa`).

---

## 2. ADIM 2 — İki model, yeni bütçe, tam 64 vaka

Komutlar (`runtime_profiles.json`'a model için dokunulmadı; bayrakla):

```
python eval/run_turkish_quality.py --model llama3.1:latest
python eval/run_turkish_quality.py --saglayici deepseek --model deepseek/deepseek-chat
```

| model | geçen | `done_reason` | `length` ile biten | hata |
|---|---|---|---|---|
| `llama3.1:latest` | **52/64** | 64 `stop` | **yok** | 0 |
| `deepseek/deepseek-chat` | **59/64** | 63 `stop` + 1 yok | **yok** | 1 — `t1_tone_012`, `WinError 10054`, üç denemeden sonra |

**Kartın dur koşulu tetiklenmedi:** `length` ile biten vaka kalmadı.
`t1_mix_002` (beklenen istisna) llama'da `stop` ile 102 karakterde bitti ve geçti.

### Kategoriler

| kategori | llama3.1 | deepseek |
|---|---|---|
| tone | 19/20 | 18/20 (biri ağ ölümü) |
| turkish | 13/15 | 13/15 |
| technical | 5/10 | 9/10 |
| mixed | 4/5 | 5/5 |
| memory | 5/5 | 5/5 |
| grounding | 5/5 | 5/5 |
| longform | 1/4 | 4/4 |

### Kalan vakalar

| model | vaka | sebep |
|---|---|---|
| llama | `t1_tone_013`, `t1_tr_005`, `t1_tr_014`, `t1_tech_008`, `t1_mix_003` | `prompt_leak` |
| llama | `t1_tech_002`, `t1_tech_003`, `t1_tech_004`, `t1_tech_010` | `grounding` |
| llama | `t2_longform_001`, `t2_longform_003`, `t2_longform_004` | `repetition` |
| deepseek | `t1_tone_012` | `empty` — **ağ ölümü** |
| deepseek | `t1_tone_020`, `t1_tr_007` | `boilerplate` |
| deepseek | `t1_tr_002` | `prompt_leak` (`'bir dosyaya ya'`, `'dosyaya ya da'`) |
| deepseek | `t1_tech_002` | `grounding` |

Hiçbir kayıp `truncated` değil — 400'ün ürettiği duvar kalktı.

### ETAP 5'in CONCERN'ü — üç vaka

| vaka | ETAP 5 (400) | taban (2000) |
|---|---|---|
| `t1_tr_001` | 400, `length`, `truncated` | **430**, `stop`, geçti |
| `t1_tr_009` | 400, `length`, `truncated` | **543**, `stop`, geçti |
| `t1_tr_013` | 400, `length`, `truncated` | **439**, `stop`, geçti |

DeepSeek sayacı (`completion_tokens` = `raw_tps × total_s`, bu yolda birebir).
543, sondada gördüğüm DeepSeek tavanını (462) aşıyor; 2000 hâlâ onun ~3,7 katı.

### ETAP 5 → taban: değişen vakalar (farklı tanım, yalnız bilgi)

| model | yukarı | aşağı |
|---|---|---|
| deepseek | `t1_tr_001`, `t1_tr_009`, `t1_tr_013` (duvar kalktı), `t1_tech_005` (ETAP 5'te ağ ölümüydü) | `t1_tone_012` (ağ ölümü), `t1_tr_002` (`prompt_leak`), `t1_tech_002` (`grounding`) |
| llama | `t1_tr_011`, `t2_grounding_002`, `t2_grounding_003` | `t1_tr_014` (`prompt_leak`, 1.975 karakterlik cevap), `t1_tech_008` (`prompt_leak`) |

Maliyet: DeepSeek tarafında bir tam koşu (64 vaka; biri üç denemeden sonra düştü).

---

## 3. ADIM 3 — Kaydedilen taban

### 3.1 `passing_threshold` yapısı

- Üst düzey eski sayılar (40/50, 49/64, kategoriler) **yerinde** ve `note`'a
  "yeni tanımın tabanı aşağıda" cümlesi eklendi.
- Eski `olcum_tanimi` — üç değişken eklendi: bütçe (§3.2 düzeltmesiyle),
  `dedektor`, `ollama_adresi`. "ETAP 2'de ölçülecek" sözü `gecerlilik`'ten
  çıktı; yerine yeni bloğa işaret kondu. Ölçülmüş cümleler kaldı.
- Yeni blok **`yeni_tanim_2026_09_13`** — kendi `olcum_tanimi`'yle:

| değişken | değer |
|---|---|
| `longform_num_predict` | 4000 |
| `diger_num_predict` | **2000** |
| `dedektor` | `eval/quality_scorer.py` @ `3f20477` (sızıntı korpusu 631 n-gram, `_YONTEM` hariç); persona `agents/persona.py` @ `f1aa069` |
| `ollama_adresi` | `127.0.0.1` (`5ebf4aa`) — düzeltme **yapıldı** |
| `kosucu` | `eval/run_turkish_quality.py` @ `61b1ce3`, sıcaklık 0,2 |

  İki modelin kategori kategori tabanı, "tek koşu hüküm değildir" uyarısı ve
  ETAP 2 / ETAP 5 sayılarının "taban değildir" etiketli izi.
- A14: `">=N"` yok (iki test koruyor); `49/64` üst düzeyde duruyor (bir test
  koruyor).

### 3.2 Kayıt düzeltmesi — 49/64 hangi bütçeyle ölçülmüştü

Eski `olcum_tanimi` 49/64 için `longform_num_predict: 1200` diyordu. **Yanlış.**

| kanıt | ne gösteriyor |
|---|---|
| koşucunun ilk commit'i `0f385b3` (2026-09-02) satır 298 | her vakaya `"num_predict": 400` sabit gönderiliyor |
| `KALITE_llama3.1_latest_20260901-2314.json` | sonuçlarda `num_predict` / `done_reason` alanı yok — vaka bütçesi yokken üretilmiş |
| dört longform cevabı, llama tokenizer'ı (`TERAZI_400_SONDA` §1b yöntemi, ±1 kalibre) | **401, 401, 401, 401 token** — 400 tavanı |
| `f2c5137` (2026-09-05) | longform'a kendi bütçesini (1200) veren commit — 49/64'ün cevaplarından **sonra** |

Değer 400'e çekildi; eski değer ve kanıt `longform_num_predict_duzeltme`
alanında duruyor. `CLAUDE.md` §13.2'ye aynı düzeltme eklendi.

> Aynı etiket başka yerde de geçiyor: `TERAZI_ETAP2_2026-09-10.md` tablosu
> "49/64 | 1200 token" diyor. Rapor tarihsel kayıt olduğu için
> **dokunulmadı.**

### 3.3 `CLAUDE.md` §13.2

Eski paragraflar olduğu gibi kaldı; altına "Yeni tanımın tabanı — söz ödendi"
paragrafı eklendi (tanım, iki sayı, tek koşu uyarısı, §3.2 düzeltmesi).

---

## 4. ADIM 4 ve kuyruk

- `automation/KART_TERAZI_COK_SAGLAYICI.md` ADIM 3'e not: `--tahmin` tek oranla
  hesaplanamaz (DeepSeek 2,41 · llama ~3,2–3,3), ve 2000'lik tavanda üst sınır
  gerçek tüketimin çok üstünde (sonda: 6.458 çıkış tokeni, tavan 120.000).
  **Uygulama değil**; ETAP 6 ayrı iş.
- `automation/IMZASIZ_IS_KUYRUGU.md` → **K17**: tekrar dedektörü numaralı sayma
  döngüsünü görmüyor. Kapsamı ölçüm; düzeltme dedektör değişikliği → imza.
  Taban koşusunda `t1_mix_002` çarpmadı — kör nokta kapanmadı, yalnız
  tetiklenmedi.

---

## 5. Kapı

```
pytest tests -q  alfabetik : 1983 geçti / 0 başarısız (2 xfail, 2 uyarı)
pytest tests -q  ters sıra : 1983 geçti / 0 başarısız (2 xfail, 2 uyarı)
ruff check .               : 283  (taban 283)
```

Commit'ten önce `passing_threshold` mekanik olarak doğrulandı: vaka listesi
bayt bayt aynı, eski sayılar yerinde, `>=` yok, "ETAP 2'de ölçülecek" sözü
çıktı, yeni bloğun 16 sayısı iki koşunun kendi özetiyle birebir. Dört ham veri
dosyasında `Bearer`, `sk-…`, `DEEPSEEK_API_KEY=` taraması: **0** eşleşme
(`.env` okunmadı).

---

## 6. Ara rapor (tek paragraf)

Kısa vakaların bütçesi 400'den 2000'e çıkarıldı (tek satır,
`DEFAULT_NUM_PREDICT`; vaka dosyası iki testi kırardı) ve iki model yeni
tanımla tam 64 vaka koşuldu: llama3.1 **52/64**, DeepSeek **59/64** (biri ağ
ölümü). `length` ile biten vaka kalmadı; ETAP 5'te 400'e çarpan üç DeepSeek
turkish vakası 2000'de 430, 543 ve 439 token'da kendiliğinden durup geçti,
yani CONCERN ölçümle kapandı. Taban `passing_threshold.yeni_tanim_2026_09_13`'e
kendi ölçüm tanımıyla (bütçe, dedektör `3f20477`, Ollama adresi `127.0.0.1`)
kaydedildi, eski sayılar yerinde; iki sayı da tek koşudur. Kaydederken eski
tanımda bir yanlış bulundu: 49/64'ün cevapları 1200 değil 400 bütçeyle
üretilmişti (dört longform cevabı 401'er token) — alan kanıtıyla düzeltildi.
`t1_mix_002` çarpmadı; tekrar dedektörünün kör noktası K17 olarak kuyruğa
yazıldı, ETAP 6'ya karakter/token notu düşüldü.
