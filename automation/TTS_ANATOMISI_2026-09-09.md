> ## ⚠️ BU BELGENİN §1'İ ÇÜRÜTÜLDÜ (2026-09-09 gecesi, gerçek cevaplarla)
>
> Düzeltme: `automation/GECIKME_ACIKLAMASI_2026-09-09.md`. Belge **silinmedi**.
>
> | İddia | Durum |
> |---|---|
> | İlk sese kadar 577–1.052 ms, %99 ağ | ✅ **DOĞRULANDI** — gerçek cevaplarla 615,5 ms |
> | Oynatma = 0,1667 × bayt (R² 1,000) | ✅ **DOĞRULANDI** |
> | **"Eğim uyuşmuyor: 58,52'ye karşı 72,22 — Ahmet'inki %23 dik"** | ❌ **ÇÜRÜDÜ** |
> | **"3.468 ms dik eğimin muhasebe artığı"** | ❌ **ÇÜRÜDÜ** |
>
> **Sebebi: sentetik cümlelerim temsili değildi.** Düz nesir 58,52 ms/karakter
> okunuyor; gerçek JARVIS cevapları **73,77 ms/karakter** (22 tur, R² 0,9975).
> Ahmet'in 72,22'si gerçek ölçüme **%2,1** uzaklıkta — yani onun eğimi
> doğruydu, benimki dar bir metin türünden geliyordu.
>
> §1'de "açıklanamıyor" diye bıraktığım **+2.615 ms**'nin **1.416 ms**'si tam
> olarak budur. Kalanın 526 ms'si makine yükü, ~673 ms'si hâlâ açık.
>
> **Ders:** sentetik ölçüm gerçek girdiyi temsil etmeyebilir; bunu ancak gerçek
> girdiyle koşarak anlarsın. "Kendi çıkarımını sına" kuralı kendi ölçümüm için
> de geçerliymiş.

# TTS anatomisi — 3.468 ms'nin içi

**Ölçen:** Claude Code · **Tarih:** 2026-09-09 · **Dal:** `auto/opencode-deepseek`
**Kart:** `automation/KART_CLAUDE_TTS_3468MS.md`
**Araç:** `scripts/olc_tts_anatomisi.py` + `EdgeTTSAdapter.speak()` olay damgaları
**Testler:** `tests/test_tts_anatomisi_olcumu.py` (12 test)
**Ham veri:** `automation/TTS_ANATOMISI_20260909-2240.json`
**Sınanan belge:** `automation/SES_HATTI_COZUMLEME_2026-09-09.md`

> Bu belge **hüküm vermez**. Akışlı TTS bir mimari değişikliktir ve CLAUDE.md §9
> gereği Ahmet'in imzasını ister.

---

## 0. Kısa cevap

**3.468 ms "ilk sese kadar ödenen bedel" değil.** Doğrudan ölçüldüğünde ilk
sese kadar geçen süre **577–1.052 ms**. Bu bir çıkarım değil, dört uzunluk ×
5 tur boyunca gözlenen değerlerin ortancası.

Ve o sürenin neredeyse tamamı ağ:

| İlk sese kadar | p50 |
|---|---|
| Sentez (Microsoft'a gidiş-dönüş) | 573–1.048 ms |
| Oynatıcı kurulumu (pygame, ısınmış) | 4–6 ms |
| Oynatıcı kurulumu (ilk çağrı, mixer init) | 188 ms — bir kez |

Yani kartın sorduğu **"kaçı ağ, kaçı yerel"** sorusunun cevabı: ısınmış
durumda **%99 ağ, %1 yerel**.

Bu, akışlı TTS'in işe yarayabileceği anlamına gelir — ama tavanı **3.468 ms
değil, ~680 ms**.

---

## 1. Regresyon sınandı: aritmetik doğru, model yanlış

Kart "kendi çıkarımımı doğrulatmak için değil, sınamak için koyuyorum" diyor.
Sınandı.

**Aritmetik doğru.** Aynı beş noktadan aynı sayılar çıkıyor; bu betiğin
`dogrusal_uyum`'u testle kilitli ve Ahmet'in değerlerini yeniden üretiyor:

```
egim = 72,2251 ms/karakter   kesisim = 3.467,7 ms   R2 = 0,9858
```

**Model yanlış.** Doğrudan ölçüm (20 nokta, 4 uzunluk × 5 tur):

| Dilim | Eğim | Kesişim | R² |
|---|---|---|---|
| `oynatma_ms` (saf konuşma) | **58,52** ms/kar | 1.478,6 ms | **0,999** |
| `sentez_ms` (ağ) | 2,25 ms/kar | 657,6 ms | 0,215 |
| `oynatici_kurulum_ms` | −0,11 ms/kar | 26,1 ms | 0,057 |
| `toplam_ms` (sentez+oynatma) | **60,66** ms/kar | 2.162,2 ms | 0,994 |
| **Ahmet'in uyumu** | **72,22** ms/kar | **3.467,7** ms | 0,986 |

**Eğim uyuşmuyor: 58,52'ye karşı 72,22 ms/karakter — Ahmet'inki %23 dik.**

Ve uyuşmazlık tesadüf değil, aritmetik olarak kilitli:

```
egim farki x Ahmet'in ortalama x'i  =  11,57 x 113,2  =  1.309,2 ms
kesisim farki                       =  3.467,7 - 2.162,2  =  1.305,5 ms
```

Dört milisaniye içinde aynı sayı. **Kesişimdeki fark, eğimdeki farkın ortalama
x etrafında dönmesinden başka bir şey değil.** Doğrusal uyumda eğim hatası
doğrudan kesişime yazılır; bu yüzden 3.468 ms "ölçülmüş bir bedel" gibi
görünüyor ama aslında dik eğimin muhasebe artığı.

### Neden eğim dik çıktı — kısmen ölçüldü, kısmen bilinmiyor

Benim modelim Ahmet'in **beş noktasının hepsini birden az tahmin ediyor**:

| karakter | gözlenen | benim modelim | fark |
|---|---|---|---|
| 194 | 17.634 | 13.930 | +3.704 |
| 133 | 12.523 | 10.230 | +2.293 |
| 91 | 10.688 | 7.682 | +3.006 |
| 86 | 9.675 | 7.379 | +2.296 |
| 62 | 7.698 | 5.923 | +1.775 |

Ortalama **+2.615 ms**. Hepsi aynı yönde, yani gürültü değil: o akşamki
turlar gerçekten yavaştı.

**[EMİN DEĞİLİM]** Nedenini ölçmedim. Adını koyabileceğim üç aday:

1. **Metin farkı.** Ahmet'in verisi gerçek JARVIS cevaplarıydı; benimki düz
   sentetik nesir. Noktalama ve sayı, karakter başına ses süresini değiştirir.
2. **Makine yükü.** Aynı 5 turluk koşu `model_ms` = 4.367 ms'lik bir sıçrama
   da gösterdi (diğerleri 475–1.068 ms) — kendi raporunun §4'ünde yazılı. O
   akşam makinenin çekişme altında olduğuna dair bağımsız bir işaret.
3. **Ölçüm sınırı.** Onun `sentez_ve_oynatma_ms`'i `VoiceIO.say()`'i sarıyordu,
   benimki `EdgeTTSAdapter.speak()`'i. Aradaki fark `speech_text()` +
   `_hassas_mi()`; ikisi de regex/sınıflandırma, milisaniye altı. **Bu adayı
   inceledim ve 2,6 saniyeyi açıklamıyor.**

---

## 2. Oynatma bir muamma değil: dosya ne kadarsa o kadar

`oynatma_ms` ile mp3 boyutu arasındaki ilişki **R² = 1,000**:

```
oynatma_ms  =  0,1667 x bayt  +  14,3 ms        R2 = 1,000
bayt        =  351,16 x karakter  +  8.784,7    R2 = 0,9988
```

Yani oynatıcı sadece dosyayı çalıyor; hiçbir gizli maliyet yok. Ve dikkat:
ses dosyasının kendisinin **sabit bir parçası var** — ~8.785 bayt, yaklaşık
1.464 ms. Bu, `oynatma_ms`'in 1.478,6 ms'lik kesişimiyle örtüşüyor.

**Bu sabit parça sessizlik/dolgu, bekleme değil.** Yani Ahmet'in 3.468 ms'sinin
içinde, ilk sesten SONRA çalınan ~1,5 saniyelik ses de var. Bir "gecikme" gibi
sayılmış ama kullanıcı o sırada zaten JARVIS'i duyuyor.

> **Kendi çıkarımım hakkında uyarı:** 8.785 baytlık ve 1.478 ms'lik kesişimler
> benim de **ekstrapolasyonum** — en kısa örneğim 21 karakter. Sıfır karakterde
> ne olduğunu gözlemedim. Bu yüzden §0'daki cevabı kesişime hiç dayandırmadım:
> orada yazan 577–1.052 ms **doğrudan gözlenen** değerlerdir.

---

## 3. Ölçüm nasıl yapıldı

`EdgeTTSAdapter.speak()` artık beş an kaydediyor. Davranış değişmedi; yalnız
zaman kaydediliyor.

| Damga | An |
|---|---|
| `t0` | `speak()` girildi |
| `t_istek` | kapı kontrolleri geçildi, sentez isteği gönderiliyor |
| `t_ses_hazir` | ses baytları elde |
| `t_oynatma_basladi` | oynatıcı çalmaya başladığını bildirdi |
| `t_bitti` | `speak()` döndü |

Türeyen alanlar `TTSResult`'a eklendi: `sentez_ms`, `oynatici_kurulum_ms`,
`oynatma_ms`, `toplam_ms`. **Ölçülemeyen alan `None` döner, `0` değil.**

`first_audio_hint_ms` **silinmedi.** Kendi uyarısında "synthesis time only …
playback start is not measured" diyordu ve bu doğruydu; `sentez_ms` aynı anı
adıyla söylüyor, eskisi yerinde duruyor. Bir test ikisinin ayrışmamasını
koruyor. Eski alanı silmek, onu zaten alıntılamış raporları geçmişe dönük
yeniden yazmak olurdu.

`t_oynatma_basladi` **oynatıcının bildirdiği** andır: `pygame.mixer.music.play()`
döndükten hemen sonra. Bunu haber veremeyen bir oynatıcı (eski `player(path)`
imzası) damgayı `None` bırakır — uydurulmaz. Mixer ile hoparlör arasında ne
olduğu bu katmanın altındadır ve **ölçülmüyor**; yani "ilk ses" burada
"oynatıcı başladı" demektir, "kulak duydu" demek değil.

### Sentetik metin, kişisel veri değil

Dört Türkçe cümle: 21, 56, 119, 244 karakter. Ahmet'in gerçek cevapları
kullanılmadı. Uzunluklar bir testle kilitli — dosya kodlaması bozulursa
(BOM, cp1254) karakter sayısı kayar ve ms/karakter ölçümü sessizce yanlış olur.

Bayrak (`JARVIS_J0_EDGE_TTS_ENABLED=1`) **yalnız ölçüm sürecinde**,
`os.environ` üzerinden tanımlandı. Hiçbir dosyaya yazılmadı, `.env` okunmadı.

Koşu: 4 uzunluk × 5 tur oynatmalı, ayrıca 4 uzunluk × 5 tur **oynatmasız**.
Toplam 40 sentez isteği. Ölçüm `.venv` yorumlayıcısıyla koştu — sistem
Python 3.11'inde `edge_tts` kurulu değil, kapı orada koşuyor.

### Oynatmalı ve oynatmasız koşunun farkı

| karakter | sentez p50 (oynatmalı) | sentez p50 (oynatmasız) |
|---|---|---|
| 21 | 573,3 ms | 578,2 ms |
| 56 | 627,0 ms | 543,7 ms |
| 119 | 1.047,6 ms | 651,2 ms |
| 244 | 973,2 ms | 778,4 ms |

Sentez süresi iki koşuda da aynı mertebede ve uzunluktan büyük ölçüde
bağımsız (R² 0,22 ve 0,30 — yani ilişki zayıf). Oynatıcının varlığı sentezi
yavaşlatmıyor. Oynatıcının kendi payı doğrudan ölçüldü ve **4–6 ms**.

---

## 4. PUSULA bütçesi — güncel tablo

Önceki çözümleme "model payı %17, sentez payı %83" diyordu. Doğrudan ölçüm
bunu değiştiriyor:

```
model p50 (nerede kaldik, llama3.1)      1.160 ms   ÖLÇÜLDÜ (GECIKME_ANATOMISI)
+ sentez p50 (~90 karakterlik cevap)       ~650 ms   ÖLÇÜLDÜ (bu belge)
+ oynatici kurulumu (isinmis)                 ~5 ms  ÖLÇÜLDÜ (bu belge)
------------------------------------------------------
ilk sese kadar ~                         ~1.815 ms   (hedef 1.500 ms)
```

Hedefin **~1,2 katı**, önceki çıkarımın söylediği ~2,8 katı değil.

**[EMİN DEĞİLİM]** Bu toplam iki ayrı koşudan birleştirildi ve aynı turda
gözlenmedi. Ayrıca STT ve VAD hâlâ dışarıda. Tek turda uçtan uca ölçüm ayrı
bir iştir.

---

## 5. Seçenekler — hangi ölçüme dayanıyor, ne feda ediliyor

Kartın kuralı: desteklenmeyen seçenek yazılmaz. **Hiçbiri önerilmiyor.**

### A. Akışlı TTS — ilk cümle bitince konuşmaya başlamak

- **Dayanak:** ilk sese kadar geçen sürenin **%99'u sentez**, yani ağ
  (573–1.048 ms'ye karşı 4–6 ms oynatıcı). Kartın koyduğu şart — "bedel ağ ise
  akışlı TTS kazanır" — **ölçümle karşılandı.**
- **Ama tavanı küçüldü.** Kazanılabilecek en fazla şey 3.468 ms değil,
  **~650 ms**. Bütçenin geri kalanı modelin üretimi (1.160 ms) ve zaten
  duyulan ses.
- **Feda edilen:** `EdgeTTSAdapter` şu an mp3'ü **dosyaya** yazıp öyle çalıyor
  (`_default_edge_synth` → `mkstemp` → pygame). Akışlı çalışmak sentez ve
  oynatma sözleşmelerinin ikisini de değiştirir. Mimari değişiklik → §9, imza.
- **Ölçülmedi:** Edge TTS akış API'sinin ilk parça gecikmesi. "650 ms'nin ne
  kadarı kurtulur" sorusu bu ölçüm yapılmadan bilinemez.

### B. Sentez önbelleği (sık cümleler)

- **Dayanak:** aynı cümlenin sentezi 494–1.149 ms sürüyor ve **metinden
  bağımsız olarak** her seferinde yeniden ödeniyor. Bir önbellek isabeti bunu
  dosya okumaya indirir.
- **Kaç turda işe yarar:** yalnızca tekrar eden cümlelerde. Ölçülen tekrar
  oranı **yok** — JARVIS'in cevapları serbest metin. Sabit ifadeler
  ("Efendim?", "Anlamadım efendim") sayılabilir ama kaç tur ettiği
  **ölçülmedi**. Bu ölçüm yapılmadan seçenek desteklenmiyor sayılmalı.
- **Feda edilen:** disk alanı, ve önbelleğin bayatlaması (ses/persona
  değişirse).

### C. Oynatıcıyı önceden ısıtmak

- **Dayanak:** pygame `mixer.init()` **ilk çağrıda 188,2 ms**, sonraki 19
  turda 4,0–5,7 ms. Ölçüldü.
- **Kazanç:** oturumun **yalnız ilk cevabında** ~184 ms. Sonrasında sıfır.
- **Feda edilen:** neredeyse yok — açılışta bir `mixer.init()`. Ama kazanç da
  neredeyse yok; bütçenin %12'si, bir kez.

### D. Yerel TTS (Piper)

- **Dayanak:** ağ payı ölçüldü ve **büyük** (ilk sese kadar olan sürenin
  %99'u). Kartın koyduğu şart sağlanıyor.
- **PARK EDİLMİŞ CEPHE — CLAUDE.md §9.** LOOP-0E Phase B hiç yürütülmedi.
  Bu seçenek burada yalnız **ölçüm şartı sağlandığı için** yazıldı; açılması
  ayrı bir imza ister ve karar Ahmet'indir. Ben dokunmadım.
- **Ölçülmedi:** Piper'ın bu makinedeki sentez süresi ve Türkçe ses kalitesi.
  Ağ payının büyük olması Piper'ın daha hızlı olacağını **kanıtlamaz**.

---

## 6. Görülen, dokunulmayan şeyler

CLAUDE.md §3 gereği: görüldü, söylendi, düzeltilmedi.

1. **Geçici mp3 dosyaları temizlenmiyor.** `_default_edge_synth`
   `tempfile.mkstemp(suffix=".mp3")` ile dosya açıyor ve kimse silmiyor —
   her sesli cevap `%TEMP%`'te bir mp3 bırakıyor. Ölçüm betiği **kendi**
   ürettiği 40 dosyayı siliyor (ölçüm dışında, süreye girmeden), ama
   adaptörün kendi davranışına dokunulmadı.
2. **`scripts/j0_tts_adapters.py` `import warnings` kullanmıyor.** Bu benim
   değişikliğimden önce de öyleydi (`git show HEAD` ile doğrulandı) ve 283'lük
   ruff tabanının içinde. Önceden var olan ölü koda dokunulmadı.
3. **`first_audio_hint_ms` ile `sentez_ms` aynı sayıyı taşıyor.** Bilerek:
   biri tarihsel ad, diğeri ölçtüğü şeyin adı. Bir gün eskisi kaldırılacaksa
   bu bir sözleşme değişikliğidir, ayrı karar.

---

## 7. Bitti sayılma ölçütü — durum

| Ölçüt | Durum |
|---|---|
| `speak()` beş damgayı üretiyor, testleri var, kırmızı görüldü | ✅ 12 test, `AttributeError`/`ModuleNotFoundError` ile kırmızı görüldü |
| Dört uzunluk × 5 tur + oynatmasız tur | ✅ §3, ham veri JSON'da |
| "3.468 ms'nin kaçı ağ" sayıyla cevaplı | ✅ §0 — ısınmışken %99 ağ, %1 yerel |
| Regresyon eğimi doğrudan ölçümle karşılaştırıldı, uyuşmazlık yazıldı | ✅ §1 — 58,52 vs 72,22; uyuşmuyor |
| Kapı iki sırada yeşil, ruff ≤ 283 | ✅ §8 |

---

## 8. Kapı

```
pytest tests -q  alfabetik : 1940 geçti / 0 başarısız (2 xfail)
pytest tests -q  ters sıra : 1940 geçti / 0 başarısız (2 xfail)
ruff check .               : 283  (taban 283, yeni iki dosya sıfır bulgu)
```

Yeni 12 test önceki 1928'in üstüne eklendi. `scripts/j0_tts_adapters.py`
değiştiği hâlde `tests/test_j0_voice_adapters.py`'nin 98 testi bozulmadı —
damgalar eklendi, davranış değişmedi.

## 9. Ölçüm nasıl tekrarlanır

```bash
export PYTHONPATH="$(pwd)"
.venv/Scripts/python.exe scripts/olc_tts_anatomisi.py --tur 5
.venv/Scripts/python.exe scripts/olc_tts_anatomisi.py --tur 5 --yalniz-sentez
```

`--yalniz-sentez` ses cihazı gerektirmez ve sessizdir. Bayrak her iki durumda
da yalnız o süreçte tanımlanır.
