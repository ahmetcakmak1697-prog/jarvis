# FAZ-4 ADIM ÖNERİSİ — döngünün yakıtı

> **Durum:** 🔴 ÖNERİ — Ahmet onaylayana kadar `roadmap_state.json`'a **yazılmaz.**
> Sözleşme §7: *"`roadmap_state.json`'ın kendisini değiştirmek"* = insan kapısı.
>
> **Tarih:** 2026-08-27 · **Sebep:** `roadmap_state.json`'da `pending` adım YOK.
> 13 done, 1 imza bekliyor. Otonom döngü bugün silahlansa **ilk turda durur.**

---

## 0. NEDEN BU ADIMLAR, NEDEN ŞİMDİ

**Sert kısıt:** Ahmet'in donanımı **eylülün 1-2. haftası** geliyor. Bu tarih
bizim kontrolümüzde değil. `JARVIS_BACKLOG.md`'nin kendi sıralaması ev
otomasyonunu iki sprint sonraya koyuyor (J0B → J1 → J2/J5) — o sıra korunursa
donanım kutuda bekler.

**Tasarım ilkesi:** donanım gerektirmeyen **yazılım hazırlığını şimdi** yap,
donanım gelince sadece **takıp doğrula.** Böylece eylülde kaybedilen gün olmaz.

**Bu, J1'i (hafıza) iptal etmez** — sadece sıraya sonra alır. Hafıza yükseltmesi
her zaman yapılabilir; donanımın geliş tarihi tekrarlanamaz.

---

## 1. ELDEKİ DONANIM (envanter, 26.08 görsellerinden)

| Parça | Adet | Rolü |
|---|---|---|
| ESP32-S3 SuperMini | 5 | ses uydusu beyni |
| INMP441 I2S mikrofon | 5 | uydunun kulağı |
| MAX98357A I2S amfi | 6 | uydunun sesi (hoparlörü sürer) |
| 3W 4Ω hoparlör | 4 | çıkış |
| LD2410C mmWave radar | 4 | **varlık algılama** (hareketsiz insanı da görür) |
| Grove Vision AI V2 | 2 | modül üstünde görüntü işleme |
| Pi kamera modülü | 2 | kapı/oda görüşü |
| WS2812B LED şerit | 5 m | durum göstergesi |
| OLED 128x64 | — | uydu ekranı |
| M5StickS3 | 1 | ekranlı taşınabilir ESP32 |
| MG90S servo | 4 | hareket |
| Level shifter | 12 | 3.3V↔5V |
| PC817 optokuplör | 4 | izolasyon |

> 🔴 **5. UYDU EKSİK PARÇA:** plan 5 uydu diyor (§2 `FAZ-4C.2` + `FAZ-4C.3`),
> ama **hoparlör 4** ve **LD2410C radar 4** adet. Beşinci uydunun beyni
> (ESP32-S3), kulağı (INMP441) ve amfisi (MAX98357A) var; **sesi ve varlık
> algısı yok.** Ya 5. uydu "yalnızca dinleyen" olarak tanımlanır, ya da
> **1× 3W 4Ω hoparlör + 1× LD2410C** alım listesine eklenir (ikisi birlikte
> birkaç yüz TL). Karar Ahmet'in.

**Alınacak:** Raspberry Pi 5 **8 GB** + aktif soğutucu + 27W PSU + NVMe HAT/SSD ·
**Sonoff MG24** Zigbee dongle (Thread/Matter destekli) · USB uzatma kablosu
(dongle'ı Pi'den uzaklaştırmak için — USB 3.0 paraziti Zigbee menzilini düşürür).
**Ek (yukarıdaki eksik nedeniyle):** 1× 3W 4Ω hoparlör + 1× LD2410C —
5 uydunun beşi de tam olsun isteniyorsa.

**Zaten çalışan:** 2× Airfel klima (ESPHome, fiber, sabit IP, 18/18 kontrol,
bakım teşhisi) · panel + geçmiş · Tailscale · Codex denetçi hattı.

---

## 2. ÖNERİLEN ADIMLAR

### 🟢 FAZ-4A — Donanımsız yazılım hazırlığı (ŞİMDİ, otonom koşabilir)

Bu grubun tamamı `autonomy: auto`. Donanım beklemez, makine kriteri var,
insan kriteri yok — yani döngü bunları kendi başına yürütebilir.

---

**`FAZ-4A.1` — Ses uydusu ESPHome config üreteci**

- **kind:** implement · **autonomy:** auto · **depends_on:** []
- **Ne:** `gen_climate.py`'nin klimalar için yaptığını ses uyduları için yapan
  üretici. Girdi: oda adı, sabit IP, pin haritası. Çıktı: geçerli ESPHome yaml.
- **Neden üretici:** 5 uydu × elle yaml = 5 kez aynı hatayı yapma riski.
  Klimalarda `gen_climate.py` kaybolduğu için yaml'lar tek doğruluk kaynağı
  oldu (§7e); bu sefer üreteci repoda tutuyoruz.
- **allowed_paths:** `scripts/gen_uydu.py`, `tests/test_gen_uydu.py`
- **machine:**
  - `py -3.11 -m pytest tests/test_gen_uydu.py -q --tb=short`
  - `py -3.11 scripts/gen_uydu.py --oda test --ip 192.168.1.50 --dry-run` (0 döner)
- **human:** *(boş — otonom koşar)*
- **notes:** Yaml üretir, **flash etmez.** Flash ayrı insan kapısı.

---

**`FAZ-4A.2` — LD2410C mmWave varlık verisi modeli**

- **kind:** implement · **autonomy:** auto · **depends_on:** [`FAZ-4A.1`]
- **Ne:** mmWave radarın UART çerçevesini ayrıştıran saf fonksiyon +
  varlık durumu modeli (var/yok, mesafe, hareketli/hareketsiz).
- **Neden ayrı adım:** Airfel'de öğrendik — bayt haritası **ölçümle** çıkar,
  tahminle değil. Bu adım *parser iskeletini* ve *testleri* kurar; gerçek
  bayt doğrulaması donanım gelince yapılır (4D.4).
- **allowed_paths:** `agents/presence_model.py`, `tests/test_presence_model.py`
- **machine:** `py -3.11 -m pytest tests/test_presence_model.py -q --tb=short`
- **human:** *(boş)*
- **notes:** Örnek çerçeveler **üretici dokümanından** alınır; gerçek ünite
  farklı davranırsa 4D.4'te düzeltilir. Sensöre bağlama YOK, sadece model.

---

**`FAZ-4A.3` — Panel: N cihaza genelleştirme**

- **kind:** refactor · **autonomy:** auto · **depends_on:** []
- **Ne:** `tools/panel.py` şu an **2 klimaya sabit** (`UNITELER` listesi).
  Cihaz tipi kavramı yok. Uydu/varlık/kamera eklenince çöker.
- **Ne yapılacak:** cihaz kaydını tipli hale getir (`tip: klima | uydu |
  varlik`), panel her tipi kendi kartıyla çizsin, bilinmeyen tip **sessizce
  atlanmasın** — görünür "bilinmeyen cihaz tipi" uyarısı versin.
- **allowed_paths:** `tools/panel.py`, `tools/panel.html`, `tests/test_panel_model.py`
- **machine:**
  - `py -3.11 -m pytest tests/test_panel_model.py -q --tb=short`
  - `py -3.11 -c "import ast; ast.parse(open('tools/panel.py',encoding='utf-8').read())"`
  - `node --check` ile panel JS sözdizimi
- **human:** *(boş)*
- **notes:** **Mevcut klima davranışı bozulmayacak** — regresyon testi zorunlu.
  Panel şu an Ahmet'in kullandığı canlı araç.

---

### 🟡 FAZ-4B — Pi + Home Assistant (donanım gelince, insan kapısı)

---

**`FAZ-4B.1` — Pi 5 hazırlığı ve HA kurulumu**

- **kind:** integration · **autonomy:** **human_required**
- **depends_on:** [] (donanım bekler)
- **Ne:** Pi 5 8GB kurulumu, NVMe'den boot, Home Assistant OS.
- **human:**
  - Pi 5 + aktif soğutucu + 27W PSU + NVMe takıldı ve boot ediyor
  - HA OS kuruldu, web arayüzü açılıyor
  - **HA SD karttan DEĞİL NVMe'den çalışıyor** (SD kart HA yazma yükünde ölür)
  - Pi'ye sabit IP verildi ve not edildi
- **machine:** *(yok — fiziksel kurulum)*
- **notes:** Claude kurulum komutu **çalıştırmaz**; Ahmet kurar, Claude
  doğrulama sorularını sorar. Kural: *"No installation without Ahmet manually
  running the command."*

---

**`FAZ-4B.2` — Zigbee koordinatörü**

- **kind:** integration · **autonomy:** **human_required** · **depends_on:** [`FAZ-4B.1`]
- **human:**
  - Sonoff MG24 dongle **USB uzatma kablosuyla** takıldı (Pi'ye doğrudan değil —
    USB 3.0 paraziti 2.4 GHz'i boğar)
  - HA'da ZHA veya Zigbee2MQTT ayağa kalktı
  - En az 1 test cihazı eşleşti
- **notes:** MG24 seçildi çünkü Thread/Matter de destekliyor; MG21 sadece Zigbee.

---

**`FAZ-4B.3` — Airfel klimaları HA'ya taşı**

- **kind:** implement · **autonomy:** auto · **depends_on:** [`FAZ-4B.1`]
- **Ne:** İki klima zaten ESPHome'da; HA onları otomatik keşfeder.
  Bu adım keşfi **doğrular** ve panelin HA'yla çakışmadığını test eder.
- **machine:** `py -3.11 -m pytest tests/test_ha_kesif.py -q --tb=short`
- **human:** *(boş)*
- **notes:** ⚠️ **Panel ölmeyecek.** İki kontrol yolu (panel + HA) aynı anda
  çalışacak; hangisinin kazandığı test edilmeli.

---

### 🟠 FAZ-4C — Ses hattı (Wyoming)

---

**`FAZ-4C.1` — Wyoming STT/TTS sunucuları**

- **kind:** integration · **autonomy:** **human_required** · **depends_on:** [`FAZ-4B.1`]
- **human:**
  - Pi'de Wyoming faster-whisper (Türkçe) ayakta
  - Wyoming Piper (tr_TR sesi) ayakta
  - HA "Assist" bunları görüyor
  - **Gerçek Türkçe konuşmayla** ilk transkripsiyon alındı, gecikme ölçüldü
- **notes:** ⚠️ **`wyoming-satellite` ARŞİVLENDİ** (`OSS_HARVEST_REPORT` §1.1).
  Halefi `OHF-Voice/linux-voice-assistant`, ESPHome protokolü kullanıyor.
  Wyoming *protokolü* yaşıyor; ölen uydu implementasyonu. **Uydu tarafında
  ESPHome yolu seçilmeli.**
  ⚠️ **Piper GPL-3.0** — subprocess temiz, in-process linkleme değil (§1.2).

---

**`FAZ-4C.2` — İlk ses uydusu (1 adet)**

- **kind:** integration · **autonomy:** **human_required** · **depends_on:** [`FAZ-4A.1`, `FAZ-4C.1`]
- **human:**
  - ESP32-S3 + INMP441 + MAX98357A + hoparlör lehimlendi
  - 4A.1'in ürettiği yaml ile flash edildi
  - Wake word tetikleniyor, LED durum gösteriyor
  - **Uçtan uca:** "Hey Jarvis, salon klimasını aç" → klima açıldı
- **notes:** **Önce BİR tane.** Beşini birden kurmak, hata olursa hangisinde
  olduğunu bilememek demek. Airfel'de salon/yatak odası ayrımı bunu öğretti.

---

**`FAZ-4C.3` — Kalan 4 uydu**

- **kind:** integration · **autonomy:** **human_required** · **depends_on:** [`FAZ-4C.2`]
- **notes:** 4C.2 **tam çalışmadan** başlamaz.

---

### 🔵 FAZ-4D — Varlık ve görüş

---

**`FAZ-4D.4` — mmWave bayt haritası doğrulaması**

- **kind:** implement · **autonomy:** auto · **depends_on:** [`FAZ-4A.2`, `FAZ-4C.2`]
- **Ne:** Gerçek LD2410C çerçevelerini kaydet, 4A.2'deki modeli **ölçümle**
  doğrula veya düzelt.
- **machine:** `py -3.11 -m pytest tests/test_presence_model.py -q --tb=short`
- **notes:** Airfel grup-1 yöntemi: **iki kararlı durumu karşılaştır**
  (odada kimse yok / odada hareketsiz oturan biri var). Tahminle bayt
  ismi verme — ölç, gör, sonra bağla.

---

## 3. ⛔ BU ÖNERİDE BİLEREK OLMAYANLAR

| Ne | Neden yok |
|---|---|
| **Yüz tanıma / kişi kimliklendirme** | P hattı; rızalı kayıt modeli ayrı karar ister. Donanım (Grove Vision AI) var ama tasarım kararı verilmedi. |
| **Ağ güvenliği (S hattı)** | Ayrı cephe, eylül teslimini bekletmemeli. |
| **Kask / mobil ses (R2)** | R0 (Tailscale) zaten çalışıyor; kask modu ses hattı oturduktan sonra. |
| **J1 hafıza yükseltmesi** | İptal değil, **sonraya**. Donanım tarihi tekrarlanamaz, hafıza her zaman yapılabilir. |
| **Otonom döngünün silahlandırılması** | Sözleşme imzalanmadan **hayır**. Bu adımlar yakıt; motoru çalıştırmak ayrı karar. |

---

## 4. AHMET'İN ONAYLAMASI GEREKENLER

1. **Sıralama değişikliği:** J2/J5 (ev otomasyonu) J1'den (hafıza) **öne alınsın mı?**
2. **Adım listesi:** yukarıdaki 10 adım `roadmap_state.json`'a yazılsın mı?
3. **FAZ-4A otonom mu?** Üç adımın (`4A.1`, `4A.2`, `4A.3`) `autonomy: auto`
   olması — yani sözleşme imzalanınca Claude bunları kendi başına yürütmesi.
4. **Pi 5 8 GB + MG24 dongle** alım kararı kesinleşti mi?
5. **Beşinci uydu:** eksik hoparlör + radar alınsın mı, yoksa 5. uydu
   "yalnızca dinleyen" mi olsun? (bkz. §1 kırmızı not)

---

## 5. ONAYDAN SONRA CLAUDE NE YAPAR

1. Adımları `roadmap_state.json`'a ekler (`updated` alanını da düzeltir —
   şu an 2026-06-18'de takılı, içerik 06-28'e kadar canlı)
2. `HUMAN_NEEDED.md` ↔ roadmap tutarsızlığını kapatır (K4)
3. Letta ifadesini düzeltir (K5)
4. `AUTONOMY_RULES.md` ↔ `CLAUDE.md` auto-fix retry çelişkisini hizalar
5. `FAZ-4A.1`'den başlar — **her adım sonunda Codex denetimi**, `codex_denetle.ps1`
