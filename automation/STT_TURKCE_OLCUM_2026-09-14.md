# STT Türkçe — ölçüm ve öneri (KART_STT_TURKCE, ADIM 1–3)

**Ölçen:** Claude Code · **Tarih:** 2026-09-14 · **Dal:** `auto/opencode-deepseek`
**Kart:** `automation/KART_STT_TURKCE.md` · **Başlangıç HEAD:** `3331e32`
**Kayıt:** 15 cümle, aygıt "Mikrofon (HyperX SoloCast)", Ahmet'in sesi —
repo **dışında** (`%TEMP%\jarvis_stt_kayit\20260914-185533`). Bu rapor yalnız
metin taşır; ses dosyası repoya girmedi. Referans = ekrandaki metin (hiçbir
cümle düzeltilmedi).
**Ölçüm:** `scripts/olc_stt_turkce.py olc` (`9069314`) — CPU/int8, AMD Family 25
Model 97 (12 mantıksal çekirdek); model önbellekten, ağsız
(`HF_HUB_OFFLINE=1`), indirme yok. Ölçüm sırasında başka iş koşmadı.
**`voice/stt.py`'de hiçbir varsayılan değişmedi.**

---

## 0. Özet

- **Kusur A:** mevcut `small`/beam 1 → WER **0,171** (76 kelimede 13 hata),
  p50 **1252 ms**. `small`/beam 5 → **0,132** (10 hata), p50 1305 ms. `medium`
  0,105 / 0,079 ama p50 ~**3,6 s**.
- **Öneri:** `small` + `beam_size=5` — **zayıf olumlu** (3 hata farkı, tek
  koşu). Uygulanmadı; `beam_size` kodda sabit, dışarı alınması öneriliyor.
- **PUSULA:** CPU'da STT **tek başına** 1500 ms bütçenin %83–93'ünü yiyor.
  Bütçeyi beam değil CPU belirliyor. GPU yolu kapalı.
- **Kusur B:** bu kayıtta **doğrulanmadı** — beş eşiğin hiçbirinde başlamayan
  ya da erken kesilen yok. Eşik değişikliği önerilmiyor. Ama tarama bu kayıtta
  **zayıf bir sınavdı** (§3).
- **`j0_mic_check.py`'ye medyan teşhis dalı** eklendi — kartın dediği
  ortalama değil, çünkü ortalama 15 cümlenin 15'inde eşiğin üstünde.

---

## 1. İki "ortalama" yan yana — fark yöntemden

| ölçüm | ortalama rms | pencere | eşik (0,01) üstü |
|---|---|---|---|
| `j0_mic_check.py`, 2026-09-09 | **0,00781** | sabit 6 s, 200 × 30 ms parça | %19 |
| sonda, 2026-09-14, cümle başına | **0,0137–0,0352** | Enter → Enter, 2,4–3,3 s | %36–63 |

İkisi de aynı büyüklük: 30 ms'lik parça rms'lerinin pencere üzerindeki
ortalaması. Sayıyı belirleyen, **pencerenin ne kadarının sessizlik olduğu.**
`j0_mic_check` 6 saniye boyunca ölçer ve o 6 saniyenin ne kadarında
konuşulduğu kayıtlı değildir — sessizlik de paydadadır. Sondanın penceresi
cümleye sarılıdır. İki sayı bu yüzden **karşılaştırılamaz**; 0,00781 "konuşma
eşiğin altında" demek değildir.

**Kartın öncülü bu kayıtta tutmadı:** 15 cümlenin 15'inde ortalama eşiğin
üstünde. *[EMİN DEĞİLİM: iki oturum farklı günlerde; mikrofona uzaklık ve ses
yüksekliği ölçülmedi.]*

## 2. Medyan — sinyal nerede

| ölçü | 15 cümlede aralık | eşik altında |
|---|---|---|
| tam pencere medyanı (p50) | 0,0006–0,0242 | **10/15** |
| konuşma aralığının medyanı (ilk → son eşik-üstü parça) | 0,0217–0,0531 | **0/15** |
| konuşma öncesi gerçek taban (p50) | ~0,00000 (14 kayıt) · 0,00061 (`cumle_15`) | — |

Tam pencere medyanı da pencerede ne kadar sessizlik olduğuna bağlı: Enter →
Enter penceresinin başında 180–540 ms, sonunda Enter'a kadar sessizlik var.
**Konuşmanın kendi içinde** parçaların yarısından fazlası 15 cümlenin 15'inde
eşiğin üstünde, 2–5 katı. Bu kayıttaki sinyal "konuşma eşiğin altında" değil,
**"pencere sessizlik taşıyor".**

---

## 3. Kusur B — üretim kaydedicisi kayıt üzerinde

`MicrophoneRecorder`'ın kendisi, mikrofon yerine kayıttan beslenen parçalarla
koştu (mantığı kopyalanmadı). Sessizlik süresi 1,5 s.

| eşik | başlamayan | erken kesilen | tutulan / toplam (p50) |
|---|---|---|---|
| 0,002 | 0 | 0 | 0,88 |
| 0,003 | 0 | 0 | 0,88 |
| 0,005 | 0 | 0 | 0,87 |
| 0,007 | 0 | 0 | 0,87 |
| **0,01** (mevcut) | **0** | **0** | 0,87 |

### Taramanın sınırı — bu kayıtta zayıf bir sınav

15 kaydın 15'i **her eşikte** `source_exhausted` ile bitti: Ahmet Enter'a
1,5 saniyelik sessizlik birikmeden bastı. Yani tarama **normal cümle sonunu hiç
çalıştırmadı.** Sınadığı tek iki şey: konuşma başlıyor mu, ve cümle **içinde**
1,5 s'lik eşik-altı bir aralık var mı. Okunan kısa cümlelerde ikisi de olmadı.
Doğal konuşmada cümle ortası duraklamalar daha uzun olabilir. Bu tarama Kusur
B'yi **çürütmez**, yalnız bu kayıtta **göstermez.**

### Baştan kırpılma — taramanın ölçmediği yan

Üretim kaydedicisi ilk eşik-üstü parçadan **önceki** parçaları atar. 6 kayıtta
konuşmanın hemen önünde 0,0047–0,0081 seviyesinde, yani eşiğin altında kalan
yumuşak bir başlangıç var ve atılıyor. `small`/beam 1'i tam kayıtla ve üretim
kesmesiyle karşılaştırdım:

| | hata / 76 kelime |
|---|---|
| tam kayıt | 13 |
| üretim kesmesiyle (eşik 0,01) | **11** |

6 cümlenin metni iki yönde değişti. Biri kırpılmayla tutarlı:
"Son commit'te" → *"Tonkomite'ye"*. Biri tersine düzeldi: *"Sestler"* →
"Testler". **Tutarlı bir hasar yok; kanıtlanmadı.**

### `cumle_15` — konuşma dışı ses değil

Baş gürültü tabanı p50 0,02759 çıkmıştı. Parça zarfı: ilk 5 parça (~150 ms)
0,000–0,001, sonra sürekli konuşma (0,016–0,171, "Güle güle"), ~210 ms
duraklama, yine konuşma. Ahmet Enter'dan **~180 ms sonra** başlamış.
**Kusur sondanın ölçüsünde:** "baş gürültü tabanı"nı ilk 0,4 saniyeden
hesaplıyor ve bu kayıtta sessizliği değil konuşmayı ölçmüş (§6). Gerçek taban
(konuşma öncesi) p50 0,00061. **Simülasyonu yanıltmıyor:** kaydedici 6.
parçada, yani gerçek konuşma başlangıcında başlıyor; 210 ms'lik duraklama
1,5 s'nin çok altında.

### Canlı gözlem bu kayıtta tekrarlanmadı

"Merhaba dostum iyi misin" dört kombinasyonun **dördünde de doğru**;
`no_speech_detected` hiçbir eşikte yok. Canlı oturumdaki iki kusurun sebebi
bu kartta **ölçülmedi** [EMİN DEĞİLİM]. Adaylar: okuma ile doğal konuşma farkı,
mikrofona uzaklık, `DEFAULT_START_TIMEOUT_S` (8 s) içinde konuşmaya başlamamak.

### ADIM 1 önerisi: `DEFAULT_SILENCE_THRESHOLD` değişmesin (0,01)

Dayanağı medyan ve tarama, ortalama değil:

1. **Tarama:** beş eşiğin hiçbirinde başlamayan ya da erken kesilen yok →
   düşürmenin bu kayıtta ölçülmüş bir faydası yok.
2. **Medyan:** konuşma aralığının medyanı 15 cümlenin 15'inde eşiğin 2–5 katı.
3. **Marj:** gerçek taban eşiğin ~1000 kat altında; ayarın iki yanında da pay
   var.

Kusur B'yi gerçekten sınamak için **doğal konuşma** kaydı gerekir (okuma değil,
cümle ortasında duraklamalı, sonunda Enter'a basmadan) — bu kartta alınmadı.

### `j0_mic_check.py` — medyan teşhis dalı (araç düzeltmesi)

- `dinle()` medyanı da döndürüyor; SONUÇ satırlarına `medyan rms` eklendi.
- Yeni dal "UYUMLU"dan hemen önce: tepe eşiği geçiyor ama **medyan** altındaysa
  uyarır ve `medyan × 0,5` önerir (taban 0,0005, mevcut dalla aynı). Mevcut üç
  dal — ölü akış, `tepe × 0,4`, seyrek — **değişmedi.**
- **Kartın "ortalama kontrolü" yerine medyan:** ortalama 15/15'te eşiğin
  üstünde; bir ortalama kontrolü bu mikrofonda hiç ateşlemezdi. Kart metninden
  sapma bu veriye dayanıyor.
- **2026-09-09 ölçümü** (tepe 0,07968, eşik üstü %19): medyan eşiğin
  altındaydı. Eski teşhis "UYUMLU" dedi; yeni dal uyarırdı (testle kilitli).
- Dalın iki yorumu var ve mesaj ikisini de söylüyor: sürekli konuşulmadıysa
  pencere sessizlik taşır (§2'deki etki) — önce tekrar denenmeli; sürekliyse
  seviye eşiğe yakındır.
- `medyan × 0,5` katsayısı başarısız bir kayıtla **doğrulanmadı**
  [DOĞRULANMADI] — bu kayıtta hiçbir eşikte kesilme çıkmadı.
- Test: `tests/test_j0_mic_check_medyan.py`, 5 test, önce kırmızı görüldü.
- **Dokunulmadı:** `dinle()`'deki bloklayan `read()` (`voice/stt.py` bu yolun
  bazı host API'lerinde sıfır döndürdüğünü yazıyor) ve K13'teki geçersiz kaçış
  dizisi — ikisi de bu kartın kapsamı dışında.

---

## 4. Kusur A — doğruluk/süre matrisi

Aynı 15 kayıt, tam hâliyle; ısınma vakası sayılmadı.

| model | beam | WER | hata / 76 | p50 ms | p90 ms | max ms | RTF p50 | yükleme |
|---|---|---|---|---|---|---|---|---|
| `small` | 1 (mevcut) | 0,171 | 13 | **1252** | 1298 | 1301 | 0,45 | 1,2 s |
| `small` | 5 | **0,132** | 10 | **1305** | 1388 | 1426 | 0,47 | 1,2 s |
| `medium` | 1 | 0,105 | 8 | 3671 | 3774 | 3870 | 1,31 | 2,8 s |
| `medium` | 5 | 0,079 | 6 | 3618 | 3741 | 3843 | 1,32 | 2,8 s |

- **Süre kayıt uzunluğundan neredeyse bağımsız:** 2,4–3,3 s'lik kayıtlarda
  `small` 1,25–1,30 s. *Açıklama (ölçülmedi, mimari bilgisi):* Whisper
  kodlayıcısı 30 saniyelik sabit pencere işler; kısa kayıtta süreyi kodlayıcı
  belirler. RTF bu yüzden kısa cümlede yanıltıcıdır.
- **Yükleme oturum başına bir kez:** `small` 1,2 s, `medium` 2,8 s.

### Cümle tablosu

En az bir kombinasyonda hata olan 8 cümle; öteki 7 cümle dördünde de hatasız.
Parantez içi: kelime hatası.

| # | referans | small/1 | small/5 | medium/1 | medium/5 |
|---|---|---|---|---|---|
| 2 | Hey Jarvis, nerede kaldık? | Heyecan mısın? Nerede kaldık? (2) | Heyecan mısın? Nerede kaldık? (2) | Hey Jarvis, nerede kaldık? (0) | Hey Jervis, nerede kaldık? (1) |
| 6 | Son commit'te neyi değiştirdik? | Son komitte neyi değiştirdik? (1) | Son komitte neyi değiştirdik? (1) | Son committe neyi değiştirdik? (0) | Son committe neyi değiştirdik? (0) |
| 8 | DeepSeek'in cevabı neden bu kadar uzun sürdü? | Deep-sik'in … (2) | Deepsik'in … (1) | Deep Sea 2'nin … (3) | Zipsik'in … (1) |
| 9 | Testler iki sırada da yeşil geçti mi? | Sestler iki yarıda da … (2) | Sesler iki yarıda da … (2) | Sesler iki yerde de … (3) | Sesler iki yarıda da … (2) |
| 10 | Çocuklar okuldan dönünce bana haber ver. | Çocukları kuldan dönünce … (2) | doğru (0) | doğru (0) | doğru (0) |
| 11 | Şu dosyayı açıp özetini çıkarır mısın? | … çıkartır mısın? (1) | … çıkartır mısın? (1) | … çıkartır mısın? (1) | … çıkartır mısın? (1) |
| 13 | Klimayı biraz daha serin yap. | Kulüme biraz daha serin yap. (1) | Kulüme biraz daha serinyab (3) | Kulümeyi biraz daha serin yap. (1) | Kulümeyi biraz daha serin yap. (1) |
| 15 | Güle güle, sonra görüşürüz. | Bile bile sonra görüşürüz. (2) | doğru (0) | doğru (0) | doğru (0) |

- **PUSULA cümlesinin kendisi `small`'da bozuk:** "Hey Jarvis" iki beam'de de
  *"Heyecan mısın"*; `medium`/1 doğru.
- **Model büyütmek her şeyi düzeltmiyor:** "Testler" → *"Sesler"* ve
  "Klimayı" → *"Kulüme"* dört kombinasyonun dördünde de var.
- **beam 5'in 3 hatalık kazancı** iki cümleden (#10, #15) ve bir kısmi
  düzelmeden (#8) geliyor; **bir cümle kötüleşti** (#13, 1 → 3).

---

## 5. ADIM 3 — öneri: `small` + `beam_size=5` (UYGULANMADI)

Üç gerekçe (ETAP 1 şablonu):

1. **Ölçüldü mü?** Evet — aynı 15 kayıt, aynı çağrı: 13 → 10 hata (76 kelime),
   p50 +53 ms, p90 +90 ms.
2. **Bütçeye sığıyor mu?** STT tek başına `small`/5 p90 1388 ms < 1500 ms —
   ama bütçenin %93'ü. `small`/1 de %87 (p90 1298). Beam 5'in maliyeti mevcut
   STT süresinin ~%4'ü; **bütçeyi belirleyen beam değil CPU.** `medium`
   tek başına p50 3,6 s — bütçenin 2,4 katı, **reddedildi** (kartın kuralı:
   doğruluk kazanıp bütçeyi delmek çözüm değil).
3. **Oynaklık payı var mı?** **Neredeyse yok.** Fark 3 hata / 76 kelime, tek
   koşu, tek konuşmacı, okunan metin; kazanç üç cümleden geliyor ve bir cümle
   kötüleşti. Süre tarafında `small`'un yayılımı dar (p50 → max +%9).

**Kararın niteliği:** ucuz ve geri alınabilir, ama **kanıtlanmış bir iyileşme
değil.** Daha çok kayıtla (farklı gün, doğal konuşma) doğrulanmalı.

**`beam_size` kodda sabit** (`voice/stt.py`, `FasterWhisperTranscriber.__call__`,
`beam_size=1`). Öneri: `FasterWhisperTranscriber.__init__`'e
`beam_size: int = 1` parametresi (varsayılan bugünkü davranış), değeri
`build_default_voice_io` üzerinden yapılandırmadan geçirmek. **Bu kartta
yapılmadı.**

**Ölçülmemiş aday:** özel isimler (Jarvis, DeepSeek, Ollama, commit) için
faster-whisper'ın `initial_prompt` / `hotwords` parametresi — mevcut
kütüphanenin parametresi, yeni teknoloji değil. Ayrı ölçüm ister.

**GPU — şu an kapalı:** `cublas64_12.dll`, `cudnn_ops64_9.dll`,
`cublas64_11.dll` yok (kart §1, 2026-09-14 doğrulandı); `ctranslate2` kurulu
ama CUDA kütüphaneleri eksik; RTX 3070'te 1.979 MiB boş (6.040 MiB Ollama'da).
**Ölçülmedi** — kurulum ayrı bir karardır.

**PUSULA'ya not:** CPU'da STT tek başına 1,25–1,39 s. `CLAUDE.md` §7.0 bulut
gidiş-dönüşünü ~500–2000 ms diye yazıyor. İkisi yan yana konunca 1,5 s hedefi
CPU STT ile beam ne olursa olsun erişilemez görünüyor. *[Bu bir çıkarımdır:
STT ölçüldü, bulut süresi burada ölçülmedi.]*

---

## 6. Sondanın bilinen kusuru

`kaydet`'in "baş gürültü tabanı" ilk 0,4 saniyeden hesaplanıyor; konuşmacı
yarım saniye beklemeden başlarsa konuşmayı ölçer (`cumle_15`). Bu raporda
doğru ölçü kullanıldı: **konuşma başlangıcından önceki** parçalar. Sonda bu
kartta düzeltilmedi.

---

## 7. Kapı

```
pytest tests -q  alfabetik           : 2007 geçti / 0 başarısız (2 xfail, 3 uyarı)
pytest tests -q  ters sıra           : 2007 geçti / 0 başarısız (2 xfail, 2 uyarı)
ruff check .                         : 283  (taban 283)
pytest tests -q  alfabetik, yeniden  : 2007 geçti / 0 başarısız (2 xfail, 2 uyarı)
```

**İlk alfabetik koşudaki 3. uyarı tekrarlanmadı.** Metni:
`tests/test_z_chaos_fuzzer.py::test_fuzz_tokenizer_jaccard_never_crashes` →
`<unknown>:1: DeprecationWarning: invalid escape sequence '\.'`. Fuzzer tek
başına 8 koşunun 8'inde temiz; tam alfabetik süitin yeniden koşusu 2 uyarı; bu
oturumun önceki 10 alfabetik koşusunda da yoktu. Fuzzer'ın sınadığı yol
(`agents.knowledge_card_retriever`) bu kartın dosyalarına dokunmuyor.
**Kaynağı ölçülmedi** [EMİN DEĞİLİM]. Bir aday: `j0_mic_check.py` değiştiği
için bayatlayan `.pyc`'nin değişiklikten sonraki ilk koşuda yeniden derlenmesi
— dosyanın docstring'i K13'teki `'\.'`'yı taşıyor. Ama `<unknown>:1` imzası
dosyadan derlemeyle tam uyuşmuyor.

Çalışma ağacında yalnız üç dosya: `scripts/j0_mic_check.py` (+37 satır, silme
yok — mevcut dallar olduğu gibi), `tests/test_j0_mic_check_medyan.py`, bu
rapor. `voice/` farkı boş; repoda WAV yok.

---

## 8. Ara rapor (tek paragraf)

15 cümlelik kayıt üzerinde STT matrisi CPU'da koşuldu: mevcut `small`/beam 1
WER 0,171 ve p50 1252 ms; `small`/beam 5 WER 0,132 ve p50 1305 ms; `medium`
0,105/0,079 ama p50 ~3,6 s olduğu için bütçe kuralıyla elendi. Öneri
`small` + `beam_size=5` — ucuz ama zayıf kanıtlı (76 kelimede 3 hata farkı,
bir cümle kötüleşti); `beam_size` kodda sabit, dışarı alınması öneriliyor,
uygulanmadı. Asıl bulgu bütçe: CPU'da STT tek başına 1500 ms'nin %83–93'ünü
yiyor. Kusur B bu kayıtta doğrulanmadı — beş eşiğin hiçbirinde kesilme ya da
başlamama yok, ama kayıtlar Enter'la bittiği için tarama normal cümle sonunu
hiç çalıştırmadı; eşik değişikliği önerilmiyor. Kartın "ortalama eşiğin
altında" öncülü yöntemden kaynaklanıyordu (6 s'lik pencere 0,00781,
cümleye sarılı pencere 0,0137–0,0352); tam pencere medyanı da sessizliğe bağlı,
konuşma aralığının medyanı 15/15 eşiğin üstünde. `j0_mic_check.py`'ye medyan
teşhis dalı eklendi — 2026-09-09 ölçümünde "UYUMLU" yerine uyarırdı.
