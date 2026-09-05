# DONANIM + YEREL LLM ARAŞTIRMASI — RTX 3070 8 GB / Ryzen 5 7600 / 32 GB DDR5

**Tarih:** 2026-08-23 · **Soru:** "2×3090 mı, 1×5090 mı, 64 GB RAM mi?"
**Kısa cevap:** **Hiçbiri. 2 TB SATA SSD al, gerisi yazılım işi.**

---

## 0. ÖLÇÜLEN SİSTEM

| | |
|---|---|
| GPU | RTX 3070, **8 GB**, compute 8.6, VRAM bant genişliği **448 GB/s** |
| CPU | Ryzen 5 7600, 6C/12T, AM5 |
| RAM | 32 GB DDR5-5200 (2×16), ölçülen gerçek bant genişliği **~49,4 GB/s** |
| Anakart | **Gigabyte A620M H** — 1× PCIe 4.0 x16 + 1× PCIe **3.0 x1**, **2 DIMM**, **1 M.2**, 4 SATA |
| Depolama | 500 GB WD Green SN350 (Gen3, DRAM'siz QLC) — okuma ~2,4 GB/s, **SLC cache dolunca yazma 105 MB/s** |

---

## 1. 🔴 EN ÖNEMLİ BULGU — DECODE HIZI ZATEN 8 KAT FAZLA

**TTS metni ~6–8 Türkçe token/saniye tüketir.** Mevcut RTX 3070, Qwen3.5-9B
Q4_K_M ile **55–58 tok/s** üretiyor.

> Yani ekran kartı, sesin tüketebildiğinden **yaklaşık 8 kat hızlı.**
> Fazlası kullanıcıya ulaşmıyor.

1,5 saniyelik hedefi belirleyen şey token/saniye değil:

| Bileşen | Gecikme |
|---|---|
| VAD (konuşma bitti kararı) | 150–300 ms |
| STT (Whisper **small**, large-v3 değil) | 200–500 ms |
| LLM TTFT | 100–400 ms |
| İlk cümlenin decode'u (~15-20 token) | ~300 ms |
| Piper ilk ses | ~50 ms |

**Hiçbiri donanımla çözülmez.** Dördü de yazılım/mimari.

---

## 2. "8 GB VRAM İLE 700B MODEL" — ÖLÇÜLMÜŞ GERÇEK

Teknik çekirdek doğru (MoE'de toplam ≠ aktif parametre), sonuç yanlış.

**Gerçek ölçümler:**

| Sistem | Model | Sonuç |
|---|---|---|
| RTX 3090 24GB + **96 GB** RAM + Gen5 NVMe (12,4 GB/s) | DeepSeek-R1 671B Q2_K_XL (212 GiB) | **1,29 tok/s** |
| Ryzen 9 9950X3D2 + RTX 5090 + AVX-512 | GLM-5.2 744B int4, SSD stream | **1,23 tok/s** |
| Ryzen 9 9950X + PCIe 5.0 NVMe (8,81 GB/s) | aynı | **0,28 tok/s** |
| RTX PRO 2000 8 GB, CPU offload | gpt-oss-120b | **0,5–1 tok/s** |
| RTX 6000 Ada 48 GB, AirLLM | Kimi K3 | **292 saniye/token** |

Birinci satırdaki makine **senden 3× RAM, 3× VRAM, 5× SSD hızına** sahip.

**KTransformers** (iddianın en ciddi hali) minimum donanımı: **14 GB VRAM +
382 GB DRAM**. Benchmark donanımı: çift soket Xeon Gold 6454S (64 çekirdek) +
**1 TB DDR5**. Dolaşan "255/286 tok/s" rakamları **prefill**, decode değil —
decode hiçbir konfigürasyonda 14 tok/s'yi geçmiyor.

**Sonuç:** Türkçe bir cümle ~60–90 token. 1 tok/s'te **bir buçuk dakika**.
Hedef 1,5 saniye. İki büyüklük mertebesi fark — optimizasyonla kapanmaz,
bant genişliği fiziği. **Sesli asistan için parti numarası.**

---

## 3. 8 GB'DA GERÇEKTEN ÇALIŞAN MODELLER (ölçülmüş)

| Model | Kuant | Dosya | Decode | Not |
|---|---|---|---|---|
| **Qwen3.5-9B** | Q4_K_M | **5,68 GB** | **55–58 tok/s** | 32K bağlamda tepe VRAM 6,96 GB — **tek "her bağlamda sığan" model** |
| Llama 3.1 8B | Q4_K_M | 4,9 GB | 59,6 tok/s | |
| GLM-4.6V-Flash | Q4_K_M | 6,17 GB | 17,4 tok/s | 32K'da taşıyor |
| Gemma 3 12B | Q4_K_M | 7,30 GB | **4,3 tok/s** | ⚠️ "sığıyor" ama KV cache patlatıyor |

> **8 GB kartta pratik tavan ~6 GB model dosyası.** 7,3 GB'lık model sığmış
> görünüp katman katman RAM'e taşar ve 4,3 tok/s'ye düşer.

### MoE + `--n-cpu-moe` — 2026'nın gerçek değişimi
Uzman katmanları RAM'e, attention + KV cache GPU'da:

| Sistem | Model | Sonuç |
|---|---|---|
| 8 GB VRAM | Qwen3-Coder-30B-A3B | **32,49 tok/s** |
| GTX 1060 **6 GB** + 24 GB DDR4 | Qwen3.6-35B-A3B, 256K bağlam | **17 tok/s** (bayrak öncesi 3 → sonrası 10 → optimize 17) |

Senin DDR5-5200'ün DDR4'ün ~1,8 katı → **20–30 tok/s beklentisi** [TAHMİN].
Bu, "ara sıra ağır iş" senaryon için fazlasıyla yeterli.

---

## 4. 🇹🇷 TÜRKÇE — YENİ VE ÖNEMLİ BULGU

### Turkish-Gemma-9b-T1 (YTÜ COSMOS) — 9B, 8 GB'a sığar
İnsan değerlendirmesi, 1450 soru, 18 değerlendirici:

| Model | Kazanma oranı |
|---|---|
| **Turkish-Gemma-9b-T1** | **68,65%** |
| Qwen3-32B | 67,20% |
| gemma-3-27b-it | 65,81% |

Türkçe GSM8K **77,41** — Qwen2.5-32B ile başa baş. **9B model, 32B'leri geçiyor.**
GGUF mevcut. Zayıflığı: Gemma 2 tabanlı (2024), bağlam 8K, uzun bağlam/araç
kullanımı için uygun değil.

### Cetvel benchmark'ını yanlış okuma
Kumru-7B liderlik tablosunda 1. (41,58) ama **8K bağlam, akıl yürütme yok,
araç çağırma yok, kod yok.** Omurga olamaz — Türkçe düzeltici/özetleyici
yardımcı olur.

### ⚠️ Türkçe tokenizer cezası — sesli asistanı doğrudan vuruyor
Türkçe, İngilizce'ye göre kelime başına **~1,9 kat** token harcıyor.
Yani 55 tok/s'lik ham hız, **Türkçe-eşdeğer ~34 tok/s**'dir.
(Yine de TTS'in tükettiğinin 4–5 katı.)

---

## 5. ÜCRETSİZ KAZANÇLAR — DONANIMDAN ÖNCE BUNLAR

| # | İş | Ölçülmüş kazanç |
|---|---|---|
| 1 | llama.cpp'yi **Mayıs 2026 sonrası** build'e güncelle | prompt caching yavaşlık hatası düzeltmesi → **TTFT'de %93'e kadar azalma** |
| 2 | `-fa on -ctk q8_0 -ctv q8_0` | KV VRAM **%50 azalır**, PPL kaybı **<%0,1** |
| 3 | Sesli hatta `/no_think` zorla | thinking bloğu 500+ token = bütçeyi tek başına yer |
| 4 | İlk cümle biter bitmez Piper'a stream et | tüm cevabı beklemek 3–5 s eder |
| 5 | `--n-cpu-moe` ile 35B-A3B'yi ağır işe kur | 3 → 17 tok/s (ölçülmüş) |

**⚠️ Q4 KV cache KULLANMA:** DeepSeek +%3,0 PPL, Llama 3.1 +%2,8 PPL, ve
64K bağlamda **%92'ye kadar DAHA YAVAŞ** (dequantize maliyeti kazancı yiyor).

**⚠️ Speculative decoding KURMA:** 8 GB'ta Qwen3.5-9B 6,96 GB tutuyor,
draft modele ~1 GB kalıyor. GPU yükseltmesinden sonra tekrar bak.

### Motor seçimi: **llama.cpp / llama-server**
| Motor | batch=1 | Karar |
|---|---|---|
| **llama.cpp** | referans | ✅ `--n-cpu-moe` CPU-expert offload'ı olgun **tek** motor |
| Ollama | llama.cpp ile başa baş | kolaylık için olur, hız avantajı yok |
| vLLM | concurrency=1'de Ollama'nın **altında** | ❌ sürekli batch'leme tek kullanıcıda ölü ağırlık |
| TensorRT-LLM | en iyi TTFT | ❌ engine build zorunlu, CPU-MoE offload yok |
| ExLlamaV3 | 2–8 bit | ❌ modelin tamamen VRAM'e sığmasını ister |

### Cascade ≠ Router — karıştırma
- **Cascade** (küçük üret → yetersizse büyüğe geç): her yükseltmede küçük
  modelin gecikmesini **EKLER**. Sesli asistanda felaket.
- **Router** (üretmeden önce sınıflandır): ek gecikme ~50 ms. ✅ Doğrusu bu.
  CLAUDE.md'deki "deterministik routing = güvenlik özelliği" ilkesiyle örtüşüyor.

---

## 6. SATIN ALMA KARARI

> **BU KARARIN KAPSAMI:** yalnızca **bu PC'nin** LLM çıkarım donanımı
> (GPU / RAM / depolama). Aşağıdaki "başka hiçbir şey" ifadesi **ev
> otomasyonu donanımını kapsamaz** — ayrı HA kutusu (Raspberry Pi 5),
> Zigbee koordinatörü ve ESP32 uyduları başka bir problemi çözer ve
> `automation/FAZ4_ADIM_ONERISI.md` §1'de ayrıca değerlendirilir.
> Bu iki karar birbirinin alternatifi değildir.

### Piyasa bağlamı (Ağustos 2026) — karar için belirleyici
- DDR5 32 GB kit: kriz öncesi ~$90 → şimdi **$380–589** (~4 kat)
- NAND spot: Ağu 2025 → Oca 2026 arası **5 kat**
- RTX 50 SUPER serisi **2027'ye ertelendi**
- Normalleşme beklentisi: **2028**

→ "Bekle ucuzlar" geçerli bir tavsiye değil. Karar "ne zaman" değil,
**"bu para gerçekten bir problemi çözüyor mu"** olmalı.

### Türkiye fiyatları (epey.com, Ağustos 2026)
| | En ucuz |
|---|---|
| RTX 5090 32 GB | **255.999 TL** |
| RTX 5070 Ti 16 GB | **63.049 TL** |
| RTX 5060 Ti 16 GB | 35.805 TL |
| 32 GB DDR5 modül | 25.599 TL |
| 1200 W PSU | 8.399 TL |
| 2 TB NVMe Gen4 | ~15.359 TL |

### ❌ SEÇENEK A — 2× RTX 3090: ELENDİ
1. **Anakart taşımıyor.** A620M H: 1× PCIe 4.0 x16 + 1× PCIe **3.0 x1**
   (~985 MB/s). İkinci kart ne elektriksel ne fiziksel mümkün.
2. Gerçek maliyet kartlar değil: **anakart + 1200W PSU + kasa + riser =
   ~70.000–150.000 TL**
3. **Ölçülen veri karşı çıkıyor:** 34B sınıfında **tek RTX 5090 (52 tok/s),
   çift RTX 3090'ı (35 tok/s) geçiyor** — tensor parallel yükü avantajı yiyor
4. 7/24 boşta **40–60 W** sadece GPU'lar; yük altında 700 W
5. 5–6 yaşında, muhtemelen madencilik silikonu, **garanti yok**

### ❌ 64 GB RAM: ÖLÜ BÖLGE
2 DIMM yuvası → mevcut 2×16 **atılır**, 2×32 alınır = **~51.200 TL**.
- 32 GB'ta zaten çalışan: 35B-A3B Q4 (16,6 GB), Gemma 4 26B-A4B Q4 (~15 GB)
- 64 GB'ın **yeni açtığı**: 35B-A3B **Q8** (~37 GB) — kalite kazancı marjinal,
  üstelik token başına 2× okuma → **daha yavaş**
- 64 GB'la **hâlâ açılmayan**: gpt-oss-120b (63 GB), Qwen3.5-122B (~65 GB)

### ✅ ÖNERİ: 2 TB **SATA** SSD (~8.000–12.000 TL). Başka hiçbir şey.

**Neden SATA, NVMe değil:**
1. A620M H'de **tek M.2 yuvası** var → NVMe almak Windows migrasyonu demek
2. **4 boş SATA portu** var
3. Model *kütüphanesi* için 550 MB/s yeterli: 16,6 GB model 30 saniyede yüklenir,
   ve bu **7/24 açık serviste yılda birkaç kez** yaşanır
4. Sıcak modeli (Qwen3.5-9B, 5,7 GB) mevcut NVMe'de tut, kütüphaneyi SATA'ya al

**Neden GPU değil:** 255.999 TL, hâlihazırda **8 kat fazla hızlı** olan bir
decode yolunu 2,5 kat daha hızlandırır. Ölçülebilir kullanıcı faydası **sıfır**.
Üstelik J0 ses hattı **henüz Phase B'yi bile koşmadı** — ölçülmemiş bir hattın
darboğazını donanımla kapatmak, tanımı gereği tahmine para vermektir.

### İkinci en iyi: **RTX 5070 Ti 16 GB — 63.049 TL**
"Bir GPU alacağım" kararı verilmişse fiyat/fayda kırılma noktası burada:
- 3070'e göre **+%60 decode** (87,5 vs ~55 tok/s)
- **+%180 prompt processing** (3.654 vs ~1.300 t/s)
- **2× VRAM** → Gemma 4 26B-A4B Q4 ve gpt-oss-20b tamamen VRAM'e sığar
- Tek yuva, ~300 W, garantili, **5090'ın dörtte biri fiyat**

### ⚠️ RTX 5060 Ti 16 GB ALMA (35.805 TL)
Bant genişliği 3070 ile **aynı** (448 GB/s) → 8B/16K'da **51,41 tok/s**,
yani mevcut kartından **daha yavaş**. Kapasite artar, hız artmaz. Yatay hamle.

### 5090 alınacaksa 3 ön koşul (sırayla)
1. Kasa iç açıklığını **ölç** (5090'lar 3,5 slot / 350 mm'ye çıkıyor — mATX
   kasa büyük ihtimalle almaz)
2. PSU wattajı + konnektör (12V-2x6 / 3× 8-pin); 1000 W altındaysa +~10.000 TL
3. **Önce §5'teki ücretsiz işleri bitir ve ÖLÇ.** Hâlâ 1,5 s tutmuyorsa rakamla gel.

---

## 7. DEPOLAMA — GERÇEK TEHLİKE

Sağlıklı bir JARVIS çalışma seti sadece **~36 GB**:
```
Qwen3.5-9B Q4_K_M         5,7 GB   (ses hattı, VRAM'de)
Qwen3.6-35B-A3B Q4       ~20 GB   (ağır iş, --n-cpu-moe)
Turkish-Gemma-9b-T1 Q4    ~5,5 GB  (Türkçe karşılaştırma)
Qwen3.5-2B Q4             ~1,5 GB  (router/sınıflandırıcı)
Whisper small             ~3 GB
Piper Türkçe sesler       ~0,1 GB
```
500 GB bunu rahat alır. Gerçek sorun **biriktirme** — aynı modelin 6 farklı
kuantizasyonu 100 GB'ı bir haftada yer.

### 🔴 ASLA İZİN VERME
Model RAM'e sığmadığı an llama.cpp mmap sayfa hatalarını SSD'den karşılamaya
başlar → **~1 tok/s + sürekli QLC okuma amplifikasyonu**, sistem kilitlenmiş
gibi davranır.

**Kural: model dosyası + KV cache < (RAM − 8 GB).**
32 GB'ta bu **~20 GB model tavanı** demek — yani 35B-A3B Q4 sınır.

---

## 8. YAPILACAKLAR SIRASI

**Ücretsiz (hepsi ölçülebilir):**
1. llama.cpp → Mayıs 2026 sonrası build
2. `-fa on -ctk q8_0 -ctv q8_0` (Q4 KV **değil**)
3. Sesli hatta `/no_think`
4. İlk cümleyi Piper'a stream et
5. Qwen3.5-9B → ses hattı; Qwen3.6-35B-A3B `--n-cpu-moe` → ağır iş; **ölç**
6. ~~Turkish-Gemma-9b-T1 GGUF'unu Türkçe kalite karşılaştırmasına sok~~
   **YAPILDI (2026-09-05).** T1 yerine **v0.1** ölçüldü (T1'in düşünme
   blokları bütçeyi yiyor, §5.3). 64 vakalık takımda `Turkish-Gemma-9b-v0.1`
   **54/64** ile en yüksek puanı aldı; ama tepe VRAM **7076 MB** — §3'teki
   6144 MB tavanının **üstünde** — ve ilk token 420,8 ms (llama3.1'de 30,5).
   `Turkcell-LLM-7b-v1` de ölçüldü: genişletilmiş Türkçe tokenizer iddiası
   **doğrulandı ama küçük çıktı** (%5,8 daha az token; §4'teki 1,9 katsayısını
   kaldırmıyor). Karar verilmedi, `runtime_profiles.json` değişmedi.
   Tam tablo: `automation/MODEL_KIYASI_TURKCE_2026-09-05.md`.

**~10.000 TL:**
7. 2 TB SATA SSD

**Ancak 1–7 bitip ölçüm alındıktan SONRA, hâlâ gerekiyorsa:**
8. RTX 5070 Ti (63.049 TL) veya 5090 (255.999 TL) — kasa + PSU önce ölçülür

**Asla:** 2×3090 · 64 GB RAM · 5060 Ti · 671B modeli sesli asistan olarak

---

## 9. BELİRSİZLİKLER

- **[EMİN DEĞİLİM]** Türkiye'de 2. el RTX 3090: forum 20–30 bin TL, bir ilan
  48.900 TL. Güvenilir pazar verisi **bulunamadı**.
- **[EMİN DEĞİLİM]** RTX 5090 TR fiyatında kaynaklar arası 3 kat fark
  (92.849 / 128.599 / 255.999 / 305.279 TL). epey'in 39 modelli listesi esas
  alındı — **alım öncesi güncel kontrol şart**.
- **[BULUNAMADI]** SATA SSD Türkiye fiyatı; AM5 çift-x16 anakart net TR fiyatı.
- **[TAHMİN]** RTX 3070 prompt processing (~1.300 t/s) — llama.cpp resmî
  scoreboard'unda 3070 satırı yok, bant genişliği oranından türetildi.
- Raporun bir kısmı SEO amaçlı ikincil sitelerden geldi ve `[İKİNCİL KAYNAK]`
  işaretlendi; birincil kaynaklar llama.cpp GitHub tartışmaları, KTransformers
  resmî dokümanı, HuggingFace model kartları, arXiv (Cetvel), epey.com.
