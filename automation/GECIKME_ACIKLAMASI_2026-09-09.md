# Açıklanamayan 2.615 ms — nereye gitti?

**Ölçen:** Claude Code · **Tarih:** 2026-09-09 · **Dal:** `auto/opencode-deepseek`
**Kart:** `automation/KART_CLAUDE_2600MS.md`
**Araç:** `scripts/olc_ses_gecikmesi.py` (`--kuru --ses-cikisi`)
**Testler:** `tests/test_ses_turu_tts_damgalari.py` (10 test)
**Ham veri:** `automation/SES_GECIKMESI_20260909-2345.json`
**Düzeltilen belgeler:** `SES_HATTI_COZUMLEME_2026-09-09.md`, `TTS_ANATOMISI_2026-09-09.md`

> Bu belge **hüküm vermez**. Akışlı TTS uygulanmadı; imza bekliyor.

---

## 0. Kısa cevap

2.615 ms'nin dağılımı:

| Parça | ms | Durum |
|---|---|---|
| **Metin farkı** (sentetik nesir ≠ gerçek JARVIS cevabı) | **1.416** | ÖLÇÜLDÜ — aday 1 **doğrulandı** |
| **Makine yükü** (sentez şişmesi) | **~526** | ÖLÇÜLDÜ — aday 2 **doğrulandı** |
| **Kalan** | **~673** | **[EMİN DEĞİLİM]** — §5 |

Ve en önemlisi: **Ahmet'in 72,2 ms/karakter eğimi doğruydu.** Yanlış olan
benim sentetik ölçümümdü.

| Eğim | ms/karakter |
|---|---|
| Sentetik düz nesir (`TTS_ANATOMISI`) | 58,52 |
| **Gerçek JARVIS cevabı (bu ölçüm)** | **73,77** |
| Ahmet'in regresyonu | 72,22 |

Gerçek ölçüme uzaklık **%2,1**. Kendi raporumda "Ahmet'inki %23 dik" diye
yazdığım cümle **çürüdü**; §4'te düzeltildi.

---

## 1. ADIM 0 — kapatılan kayıp

`scripts/olc_ses_gecikmesi.py` cevabın yalnız **uzunluğunu** kaydediyordu.
Metin olmadan o akşamki turlar tekrar oynatılamıyordu.

Artık ham veri `cevap` alanını taşıyor. Uzunluk alanı **kaldı** — eski
kayıtlarla kıyas onun üzerinden yapılıyor. Metin yalnız `.json`'a yazılır,
rapora değil.

**Bu düzeltme olmasaydı bu raporun hiçbir sonucu çıkmazdı.** Aşağıdaki her
şey kaydedilen cevap metninden hesaplandı.

### Ve hemen ardından çıkan ikinci kayıp

`cevap_uzunluk` **konuşulan karakter sayısı değildir.** TTS'e giden metin
`speech_text()`'ten geçiyor: markdown temizleniyor ve **600 karakterde
kesiliyor** (`SPEECH_MAX_CHARS`).

Ölçümde bu doğrudan görüldü — 2.079 / 2.164 / 2.358 karakterlik üç cevabın
üçü de **aynı** ~46,8 saniyelik ses üretti, çünkü üçü de 623–624 karakterde
kesilmişti.

Doğru bağımsız değişken `len(speech_text(cevap))`. Bu raporun bütün uyumları
onunla hesaplandı. `cevap_uzunluk` ile hesaplanan bir eğim, uzun cevaplar
karıştığında **sessizce yanlıştır**.

> **Açık kalan:** tur kaydı konuşulan uzunluğu ayrı bir alan olarak
> tutmuyor; hesaplanabiliyor ama JSON'a naif bakan biri yine `cevap_uzunluk`'u
> kullanır. Alanı eklemek doğal bir sonraki adımdır, bu kartın kapsamında
> değildi.

---

## 2. ADIM 1 — kartın varsayımı yanlıştı, düzeltildi

Kart "`--kuru` modu STT'yi atlar ama **model + TTS'i gerçekten çalıştırır**"
diyor. **Kaynak bunu söylemiyordu.** Kuru modda `seslendir` sabit `False`
dönen bir no-op'tu; TTS hiç çalışmıyordu.

Yani o varsayımla alınacak her ölçüm, sentezi hiç görmeden "ölçtüm" derdi.
`--kuru` davranışı **değiştirilmedi**; yanına `--ses-cikisi` kapısı kondu:
STT yok, TTS var.

Çıkış tarafı tam gerçek yoldur — `VoiceIO.say()` çağrılır, yani
`speech_text()` temizliği ve B05 veri-sınıfı kapısı da ölçülen sürenin
içindedir. Konuşmacı sarılır çünkü `VoiceIO.say()` hiçbir şey döndürmez ve
o sözleşme değişmez; `TTSResult` ancak böyle dışarı çıkar. `is_local`
tanımlanmaz, yani egress kapısı yerinde durur.

Tur kaydı artık `sentez_ms` / `oynatici_kurulum_ms` / `oynatma_ms` alanlarını
ayrı ayrı taşıyor. Damga veremeyen bir seslendirici için **`None`, `0` değil.**

### Sessiz makinede 10 tur (`--kuru --ses-cikisi --tur 10`)

| | p50 | p95 |
|---|---|---|
| Model | 199,1 ms | 4.294,8 ms |
| **Sentez (ağ)** | **615,5 ms** | 1.292,9 ms |
| Oynatıcı kurulumu | 4,4 ms | 115,4 ms |
| Oynatma (çalınan ses) | 3.437,8 ms | 3.443,1 ms |
| Tur süresi | 4.288,2 ms | 8.927,3 ms |

**`sentez_ms` = 615,5 ms, sentetik ölçümün 573–1.048 ms bandının tam
içinde.** Kartın koyduğu karar kuralı buydu: *"bandda çıkarsa fark metinden
değil, aday 1 elenir."*

**O kural yanlış sonuca götürüyor ve elemiyorum.** Metin farkı gerçekten var
— ama **sentezde değil, oynatmada.** Microsoft gerçek cevaplar için daha fazla
zaman almıyor; gerçek cevaplar **daha uzun ses** üretiyor. Karakter başına
73,77 ms'ye karşı 58,52 ms.

### Bu koşunun sınırı

On turun onunda da cevap aynıydı ve 34 karakterdi: *"Anlık proje durumuna
erişimim yok."* Tek uzunlukla eğim ölçülemez — `dogrusal_uyum` bunu fark edip
`None` döndürdü (bütün x'ler aynı). Bu yüzden dört ayrı soruyla 12 tur daha
koşuldu; §3'ün uyumu 22 turun tamamı üzerindedir.

> **Yan bulgu, bu kartın konusu değil:** "nerede kaldık" sorusuna verilen
> cevap *"Anlık proje durumuna erişimim yok."* Bu bir PUSULA ihlalidir —
> cevabın repo'nun gerçek durumunu yansıtması gerekiyordu. Gecikme değil
> **kalite** sorunudur, dokunulmadı. Not: ölçüm sırasında `agents/persona.py`
> başka bir oturumun **commit edilmemiş** düzenlemesini taşıyordu (iki satır,
> prompt'un ~%1'i).

---

## 3. Gerçek cevaplarla ölçülen model (22 tur)

Bağımsız değişken `len(speech_text(cevap))`, 29–624 karakter aralığı:

```
oynatma_ms = 73,77 x karakter +   808,8      R2 = 0,9975
sentez_ms  =  4,86 x karakter +   730,9      R2 = 0,6053
oynatici_kurulum_ms ~ 4,4 ms (isinmis), 173-206 ms (ilk pygame init)
```

Toplam: `sentez_ve_oynatma_ms = 78,63 x karakter + 1.544,1`

Ahmet'in beş noktası bu modelle:

| karakter | gözlenen | model | fark |
|---|---|---|---|
| 194 | 17.634 | 16.798 | +836 |
| 133 | 12.523 | 12.002 | +521 |
| 91 | 10.688 | 8.699 | +1.989 |
| 86 | 9.675 | 8.306 | +1.369 |
| 62 | 7.698 | 6.419 | +1.279 |
| | | **ortalama** | **+1.199** |

Önceki açıklanamayan fark +2.615 ms idi. **Metin farkı 1.416 ms'sini
açıkladı.**

---

## 4. ADIM 2 — makine yükü ölçüldü

Aynı soru, aynı makine, tek fark: iki `pytest tests` koşusu paralel dönüyor.

| | sessiz | yüklü | oran |
|---|---|---|---|
| `model_ms` p50 | 199,1 ms | 630,1 ms | **3,2×** |
| `model_ms` p95 | 4.294,8 ms | **47.999,3 ms** | — |
| `sentez_ms` p50 | 615,5 ms | 1.141,8 ms | **1,9×** |

Yüklü koşunun bir turunda `model_ms` **59.813 ms** ölçüldü. Aynı soru, aynı
model.

**Aday 2 doğrulandı.** Yük sentezi ~1,9 kat şişiriyor; bu, kalan 1.199 ms'nin
**~526 ms**'sini açıklıyor (1.141,8 − 615,5).

### Ama tek başına yeterli değil — model sıçraması sessiz makinede de var

Sessiz koşunun 3. turunda `model_ms` **7.304,5 ms** çıktı; diğer dokuz tur
189–616 ms. Yani "o akşam makine doluydu" cümlesi sıçramanın tamamını
açıklamıyor. Aynı desen `GECIKME_ANATOMISI_2026-09-09.md`'de de vardı
(236 ms → 5.052 ms prompt değerlendirme). Üç bağımsız ölçümde göründü.

**Ölçüm koşulu kuralı** (`FAILURES.md`'ye yazılacak): gecikme ölçümü paralel
`pytest`/ajan koşusu varken alınmaz. Aynı hataya dördüncü kez düşülmesin.

---

## 5. Kalan ~673 ms — [EMİN DEĞİLİM]

2.615 − 1.416 (metin) − 526 (yük) = **~673 ms** açıklanamıyor.

Ölçmediğim, ama adını koyabildiğim adaylar:

1. **STT yığını bellekte.** O akşamki koşu mikrofonluydu: `MicrophoneRecorder`
   ve `FasterWhisperTranscriber` yüklüydü. Benim kuru koşularımda ikisi de
   hiç kurulmadı. Whisper'ın GPU/RAM payı sentezi ve modeli etkilemiş
   olabilir. **Ölçülmedi.**
2. **Ağ oynaklığı.** Kendi `sentez_ms` değerlerim 507,6 ms ile 5.351,0 ms
   arasında geziniyor. O akşamki `sentez_ms` **hiç kaydedilmedi** — zaten bu
   kartın kapattığı eksik buydu. Aynı akşam tekrar ölçülemez.
3. **Cevap metninin kendisi.** Modelim 22 turluk *benim* cevaplarımdan
   çıktı; o akşamki beş cevabın metni **kayıtlı değil** (ADIM 0 öncesi).
   Noktalama ve kısaltma yoğunluğu karakter başına ses süresini değiştiriyor
   — bunu zaten 58,52 → 73,77 farkında gördük. O beş cevap için değer
   bilinemez.

Üçü de aynı yönde çalışır. Kalan 673 ms, beş noktalık bir örneklemde
+521 ile +1.989 arasında geziniyor; yani **gürültü bandının içinde olması
mümkün** ama bunu kanıtlayacak veri yok.

---

## 6. Düzeltilen çıkarımlar

Bu bölüm iki belgeyi düzeltir. Hiçbiri silinmedi.

### `SES_HATTI_COZUMLEME_2026-09-09.md` (Claude danışman)

| İddia | Durum |
|---|---|
| Eğim 72,2 ms/karakter = normal konuşma hızı | ✅ **DOĞRULANDI** — ölçülen 73,77 |
| "Sabit terim 3.468 ms, ilk sese kadar geçen süredir" | ❌ **ÇÜRÜDÜ** — ölçülen 620 ms |
| "İlk sese kadar ~4.155 ms" | ❌ **ÇÜRÜDÜ** — ölçülen ~820 ms |
| "Darboğaz LLM değil, sentez" | ⚠️ **KISMEN** — sentez (615 ms) modelden (199 ms) büyük, ama ikisi de küçük |

### `TTS_ANATOMISI_2026-09-09.md` (benim raporum)

| İddia | Durum |
|---|---|
| İlk sese kadar 577–1.052 ms, %99 ağ | ✅ **DOĞRULANDI** — gerçek cevaplarla 615,5 ms |
| "Eğim uyuşmuyor: Ahmet'inki %23 dik" | ❌ **ÇÜRÜDÜ** — sentetik metnim temsili değildi |
| "3.468 ms dik eğimin muhasebe artığı" | ❌ **ÇÜRÜDÜ** — eğim doğruydu; kesişim farkı başka |
| Oynatma = 0,1667 × bayt (R² 1,000) | ✅ **DOĞRULANDI** |

**Alınan ders:** sentetik ölçüm gerçek girdiyi temsil etmeyebilir ve bunu
ancak gerçek girdiyle koşarak anlarsın. Kendi düz nesrimle ölçüp "Ahmet'in
eğimi yanlış" demek, tam da kartın uyardığı hataydı — sadece ters yönde.

---

## 7. Bitti sayılma ölçütü — durum

| Ölçüt | Durum |
|---|---|
| Ham veri cevap metnini taşıyor | ✅ §1 |
| Tur kaydı üç TTS dilimini ayrı taşıyor | ✅ §2 |
| 10 turluk kuru koşu + sessiz/yüklü karşılaştırma | ✅ §2, §4 (ayrıca 4 soruluk varyasyon koşusu) |
| "2.615 ms'nin kaçı ne" sayıyla cevaplı, kalan işaretli | ✅ §0, §5 |
| Kapı iki sırada yeşil, ruff ≤ 283 | ✅ §8 |

## 8. Kapı

```
pytest tests -q  alfabetik : 1950 geçti / 0 başarısız (2 xfail)
pytest tests -q  ters sıra : 1950 geçti / 0 başarısız (2 xfail)
ruff check .               : 283  (taban 283, yeni dosya sıfır bulgu)
```

Yeni 10 test önceki 1940'ın üstüne eklendi. `scripts/olc_ses_gecikmesi.py`
değiştiği hâlde mevcut `test_ses_gecikmesi_olcumu.py` ve
`test_ses_olcumu_kanit.py` bozulmadı.

Not: ölçüm sırasında çalışma ağacında başka bir oturumun commit edilmemiş
`agents/persona.py` düzenlemesi vardı (iki satır). Kapı onunla birlikte
yeşildi; dosyaya dokunulmadı ve commit'e alınmadı.

## 9. Ölçüm nasıl tekrarlanır

```bash
export PYTHONPATH="$(pwd)"
.venv/Scripts/python.exe scripts/olc_ses_gecikmesi.py --kuru --ses-cikisi --tur 10
.venv/Scripts/python.exe scripts/olc_ses_gecikmesi.py --kuru --ses-cikisi --tur 3 --soru "..."
```

Mikrofon gerekmez, Whisper yüklenmez. Ses **çıkar** — sessiz makine şarttır
(§4). Edge TTS bayrağı yalnız o süreçte tanımlanır; `.env` okunmaz.
