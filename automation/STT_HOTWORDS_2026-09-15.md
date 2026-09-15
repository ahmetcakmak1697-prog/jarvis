# STT ipuçları — `hotwords` / `initial_prompt` ölçümü (KART_STT_HOTWORDS)

**Ölçen:** Claude Code · **Tarih:** 2026-09-15 · **Dal:** `auto/opencode-deepseek`
**Kart:** `automation/KART_STT_HOTWORDS.md` · **Başlangıç HEAD:** `6cbb5b6`
**Kayıt:** `%TEMP%\jarvis_stt_kayit\20260914-185533` — 15 cümle, Ahmet'in
sesi, 76 kelime, referans = ekrandaki metin. Ses repoya girmedi.

---

## 0. ÖNGÖRÜ — ölçümden ÖNCE yazıldı

> **Bu bölüm 2026-09-15 07:56:54'te, hiçbir ipucu ölçümü koşulmadan yazıldı.**
> Ölçüm dosyasının (`olcum_ipucu.json`) damgası bu saatten sonradır. Aşağıda
> değiştirilmeden durur; ölçüm ne derse §3 onu yazar.

### Kartın §2 tahmini (aynen)

| sınıf | cümle | small/1 duydu | ipucu yardım eder mi |
|---|---|---|---|
| sözlük boşluğu gibi | Hey **Jarvis** | Heyecan mısın | **evet, beklenir** |
| sözlük boşluğu gibi | **DeepSeek**'in | Deep-sik'in | **evet, beklenir** |
| sözlük boşluğu gibi | Son **commit**'te | Son komitte | **evet, beklenir** |
| sözlük boşluğu değil | **Klimayı** biraz daha serin yap | Kulüme | **hayır, beklenmez** |
| sözlük boşluğu değil | **Testler** iki sırada | Sestler / Sesler | **hayır, beklenmez** |

### Benim öngörülerim (sayı görülmeden)

1. **"Hey Jarvis":** `hotwords` ile small/1'de "Jarvis" kelimesinin
   duyulmasını bekliyorum. "Hey"in de doğru çıkıp çıkmayacağından emin
   değilim [EMİN DEĞİLİM].
2. **"klima" ipucu listesinde olduğu hâlde** "Kulüme" → "Klimayı"
   düzelmesini **beklemiyorum** (kartın tahmini). Düzelirse tahmin yanlıştır.
3. **"Testler"** ipucu listesinde yok; değişmemesini bekliyorum.
4. **Bozulma:** ipucu kelimesinin alakasız bir cümleye sızması riski var —
   en az bir cümlenin **bozulmasını** bekliyorum.
5. **Süre:** ipucu prompt'a ~5–10 token ekler; p50'de %5'ten az artış
   bekliyorum.
6. **`hotwords` ile `initial_prompt` benzer çıkacak.** Kurulu kütüphanede
   (faster-whisper 1.2.1, `get_prompt`) ikisi de `<|startofprev|>`'den sonra
   prompt'a girer; `hotwords` her pencerede, `initial_prompt` yalnız ilkinde.
   Kayıtlar 30 s'nin altında, yani tek pencere. Aynı beş kelime verildiği için
   fark yalnız noktalama olacak [EMİN DEĞİLİM].

---

## 1. ADIM 1 — sonda (`scripts/olc_stt_turkce.py`)

- `_yaziya(model, ses, beam, hotwords=None, initial_prompt=None)`: ipucu
  **yalnız verildiğinde** anahtar olarak geçer. Verilmezse çağrı
  `{language="tr", beam_size, vad_filter=True}` — üretimle
  ([voice/stt.py:406](voice/stt.py:406)) birebir aynı; `None` bile
  geçilmez. `vad_filter` hiçbir yolda kapanmaz. Üçü de testle kilitli
  (`tests/test_olc_stt_turkce.py` §6).
- `karsilastir(once, sonra)`: saf fonksiyon; **düzelen**, **bozulan** ve
  **metni değişen ama hata sayısı aynı** cümleleri ayrı listeler. Toplam WER
  bu raporda hiçbir yerde tek başına kullanılmadı.
- `ipucu` alt komutu: `small` bir kez yüklenir; her satır kendi ısınmasıyla
  koşar. Önceki ham ölçüme (`olcum.json`) **dokunulmadı** (damga
  2026-09-14 19:11:24, değişmedi); sonuç `olcum_ipucu.json` (2026-09-15
  08:04:58 — §0'ın damgasından sonra).
- İpucu, kayıtlardaki gerçek beş kelime; uydurma yok. İki mekanizma **aynı
  beş kelimeyi** taşır ve tek satırda karışmaz:
  - `hotwords` = `Jarvis DeepSeek Ollama commit klima`
  - `initial_prompt` = `Jarvis, DeepSeek, Ollama, commit, klima.`

## 2. ADIM 2 — beş satır

**Koşu:** 2026-09-15 08:03:36–08:04:58, `.venv` (faster-whisper 1.2.1),
CPU/int8, `HF_HUB_OFFLINE=1`, yükleme 1,04 s. **Hijyen:** koşudan hemen önce
CPU yükü %1; süreç listesinde sondaya ait süreç yoktu — yalnız
`pythonw panel.py` (Airfel paneli, boşta) ve `ollama serve` (boşta). Koşu
sırasında başka komut çalıştırılmadı, süreç listesi de okunmadı. `.venv`
başlatıcısı koşu boyunca iki PID üretir; bu tek iştir (`FAILURES.md`,
2026-09-14).

| # | ayar | ipucu | WER | hata / 76 | p50 ms | p90 ms | max ms |
|---|---|---|---|---|---|---|---|
| 1 | `small`/1 | yok (**taban**) | **0,171** | 13 | 956 | 995 | 1009 |
| 2 | `small`/1 | `hotwords` | 0,132 | 10 | 960 | 993 | 1017 |
| 3 | `small`/5 | yok (**taban**) | **0,132** | 10 | 994 | 1020 | 1034 |
| 4 | `small`/5 | `hotwords` | **0,053** | **4** | 1001 | 1037 | 1043 |
| 5 | `small`/1 | `initial_prompt` | 0,132 | 10 | 961 | 986 | 987 |

**Taban tuttu:** satır 1 = 0,171, satır 3 = 0,132 — kartın istediği. Daha
sıkı denetim de geçti: iki taban satırında **15 cümlenin 15'inin metni**
önceki ölçümle (`olcum.json`, 2026-09-14) karakter karakter aynı. Düzenek
değişmedi; ipucu satırları yorumlanabilir.

**Süre uyarısı — mutlak ms bugün ~%24 düşük.** Dün `small`/1 p50 1252 ms
(bağımsız tekrarda 1243), bugün 956; `small`/5 1305 (1308) → 994. İki
beam'de de aynı oran (−%24): tek bir ölçek çarpanı gibi, çözümleme farkı
gibi değil — metinler zaten birebir aynı. **Sebebi ölçülmedi** [EMİN
DEĞİLİM]; CPU güç/ısıl durumu ya da dünkü arka plan yükü aday, hiçbiri
sınanmadı. Sonuç: bu raporda süre karşılaştırmaları **yalnız bu koşunun
satırları arasında** yapılır. Oturumlar arası mutlak ms karar girdisi
değildir — oturumlar arası fark (~300 ms), oturum içi yayılımın (p50 → max
~50 ms) altı katı.

## 3. ADIM 3 — cümle cümle

Her ipucu satırı **kendi tabanıyla** (aynı beam, ipucusuz) karşılaştırıldı.
Parantez içi: kelime hatası.

### Satır 2 — `small`/1 + `hotwords` (taban: satır 1)

Toplam 13 → 10 hata · p50 956 → 960 ms · p90 995 → 993 ms

**Düzelen — 3:**

| # | önce | sonra |
|---|---|---|
| 8 | Deep-sik'in cevabı neden bu kadar uzun sürdü? (2) | DeepSeek'in cevabı neden bu kadar uzun sürdü? (0) |
| 13 | Kulüme biraz daha serin yap. (1) | Klimayı biraz daha serin yap (0) |
| 15 | Bile bile sonra görüşürüz. (2) | Bile güle sonra görüşürüz (1) — **kısmi** |

**Bozulan — 1:**

| # | önce | sonra |
|---|---|---|
| 9 | Sestler iki yarıda da yeşil geçti mi? (2) | Sesleri 2 yarıda da yeşil geçti mi? (3) |

Artan hata `iki` → `2`: bir yazım biçimi, duyma hatası değil. **Yine de
bozulan sayıldı — ölçüt değiştirilmedi.** Referans setinde rakam bilerek yok
(test kilitli); ipucu, rakamsız okunan bir cümlede rakam üretti.

**Metni değişen, hata aynı — 5:** #2 *"Heyecan mısın? Nerede kaldık?"* →
*"Heyecan vesim, nerede kaldık?"* (2 → 2); #7, #10, #12, #14 yalnız
noktalama (cümle sonu işareti düştü).

**Hüküm:** net −3 hata ama **bedelli** — 3 düzelen (biri kısmi), 1 bozulan.

### Satır 4 — `small`/5 + `hotwords` (taban: satır 3)

Toplam 10 → 4 hata · p50 994 → 1001 ms · p90 1020 → 1037 ms

**Düzelen — 3:**

| # | önce | sonra |
|---|---|---|
| 2 | Heyecan mısın? Nerede kaldık? (2) | **Hey Jarvis, nerede kaldık? (0)** |
| 8 | Deepsik'in cevabı neden bu kadar uzun sürdü? (1) | DeepSeek'in cevabı neden bu kadar uzun sürdü? (0) |
| 13 | Kulüme biraz daha serinyab (3) | Klimayı biraz daha serin yap (0) |

**Bozulan — sıfır.**

**Metni değişen, hata aynı — 5:** #7, #10, #12, #14, #15 — yalnız noktalama.

**Kalan 4 hata:** #6 *"Son komitte"* (1), #9 *"Sesler iki yarıda"* (2), #11
*"çıkartır"* (1).

**Mevcut üretim ayarına (satır 1) göre:** 13 → 4 hata; düzelen 5 cümle (#2,
#8, #10, #13, #15), bozulan **sıfır**. Önceki raporun *"beam 5 bir cümleyi
kötüleştirdi (#13, 1 → 3)"* notu bu satırda kapanıyor: beam 5'in tek başına
bozduğu #13'ü `hotwords` hatasıza çekti.

### Satır 5 — `small`/1 + `initial_prompt` (taban: satır 1)

Toplam 13 → 10 hata · p50 956 → 961 ms · p90 995 → 986 ms

**Düzelen — 3:** #8 (*"DeepSeek'in …"*, 2 → 0), #13 (*"Klimayı biraz daha
serin yap."*, 1 → 0), #15 (*"Bile güle sonra görüşürüz."*, 2 → 1, **kısmi**).

**Bozulan — 1:** #9 *"Sesleri 2 yarıda da yeşil geçti mi?"* (2 → 3) —
satır 2'dekiyle aynı.

**Metni değişen, hata aynı — 2:** #2 *"Heyecan Vesim, nerede kaldık?"* (2 →
2); #7 noktalama.

**`hotwords` ile karşılaştırma (aynı beam):** düzelen küme aynı, bozulan küme
aynı, hata sayısı aynı (10). Fark yalnız büyük harf (*vesim / Vesim*) ve
cümle sonu noktalaması: `initial_prompt` satırında 0/15 cümle noktalamasız,
`hotwords` satırlarında 5/15. *[Açıklama bir çıkarım: Whisper çıktı üslubunu
önceki metinden alır; noktalı bir prompt noktalı, noktalamasız bir liste
noktalamasız çıktı getiriyor gibi. Ölçülen yalnız 0/15 ile 5/15.]*
WER noktalamayı normalize ettiği için bu yan etkiyi görmez; ayrıca sayıldı.

### Sızıntı

Üç ipucu satırının hiçbirinde, bir ipucu kelimesi **referansında o kelime
olmayan** bir cümlede görünmedi (10 ipucusuz cümle × 3 satır). Rakam yalnız
#9'da ve yalnız `small`/1 ipuçlu satırlarda çıktı; `small`/5 + `hotwords`'te
çıkmadı.

## 4. Tahmin tuttu mu

### Kartın §2 tahmini

| cümle | tahmin | `small`/1 + hw | `small`/5 + hw | `small`/1 + ip | hüküm |
|---|---|---|---|---|---|
| Hey **Jarvis** | yardım eder | hayır | **evet** | hayır | **kısmen** — yalnız beam 5 ile |
| **DeepSeek**'in | yardım eder | evet | evet | evet | **tuttu** |
| Son **commit**'te | yardım eder | hayır | hayır | hayır | **tutmadı** |
| **Klimayı** | yardım etmez | düzeldi | düzeldi | düzeldi | **tutmadı — tahmin yanlıştı** |
| **Testler** | yardım etmez | düzelmedi (2 → 3) | düzelmedi (2) | düzelmedi (2 → 3) | **tuttu** |

Beş maddeden ikisi tuttu, biri kısmen, ikisi tutmadı.

- **"Klimayı" — kart yanıldı, bunu yazıyorum.** Kart bu hatayı "akustik/dil
  modeli hatası, sözlük boşluğu değil" diye sınıfladı; üç ipucu satırının
  üçünde de düzeldi. Yani bu kayıtta hata, ipucunun kaydırabildiği bir
  **dil önceli** — ipucunun erişemeyeceği bir akustik tavan değil.
  Kartın kutusundaki ev kontrolü sorusu **kapanmadı**: tek okuma, tek cihaz
  adı; bütün cihaz adlarını taşıyan bir ipucu listesi ölçülmedi. Ama artık
  elinde olumlu bir veri noktası var, olumsuz değil.
- **"commit" — kart yanıldı.** İpucu listesinde olduğu hâlde üç satırda da
  *"komitte"*. *[Çıkarım, ölçülmedi: "komite" Türkçe'de gerçek bir kelime;
  model burada bir boşluğu değil, var olan bir Türkçe kelimeyi tercih
  ediyor — sözlük boşluğu varsayımı bu cümle için yanlıştı.]* `medium` bu
  cümleyi *"committe"* diye doğru duymuştu.

### Benim öngörülerim (§0)

1. *"Hey Jarvis" `small`/1 + `hotwords`'te duyulur* → **tutmadı.** `small`/1'de
   ne `hotwords` ne `initial_prompt` "Jarvis"i getirdi.
2. *"Klimayı" düzelmez* → **tutmadı.** Üç satırda da düzeldi.
3. *"Testler" değişmez* → **yarısı tuttu.** Düzelmedi; ama `small`/1 ipuçlu
   satırlarda metin değişti ve hata 2 → 3 oldu.
4. *En az bir cümle bozulur* → `small`/1 satırlarında **tuttu** (#9),
   `small`/5 + `hotwords`'te **tutmadı** (sıfır). Öngördüğüm mekanizma —
   ipucu kelimesinin alakasız bir cümleye sızması — **gerçekleşmedi**;
   bozulma rakam biçiminden geldi.
5. *p50 artışı < %5* → **tuttu** (§6).
6. *`hotwords` ≈ `initial_prompt`* → `small`/1'de **tuttu**: aynı düzelen, aynı
   bozulan, aynı 10 hata. `initial_prompt` beam 5 ile ölçülmedi (kartın
   matrisinde yok), o yüzden beam 5'te de eşit olduklarını söyleyemem.

## 5. "Hey Jarvis" — açıkça

| satır | duyulan | hata |
|---|---|---|
| `small`/1 (**mevcut üretim**) | Heyecan mısın? Nerede kaldık? | 2 |
| `small`/1 + `hotwords` | Heyecan vesim, nerede kaldık? | 2 |
| `small`/5 | Heyecan mısın? Nerede kaldık? | 2 |
| `small`/5 + `hotwords` | **Hey Jarvis, nerede kaldık?** | **0** |
| `small`/1 + `initial_prompt` | Heyecan Vesim, nerede kaldık? | 2 |

**Düzeldi — ama yalnız beam 5 ve `hotwords` BİRLİKTEYKEN.** Beam 5 tek başına
düzeltmiyor (dün de bugün de *"Heyecan mısın"*), `hotwords` tek başına
düzeltmiyor, `initial_prompt` tek başına düzeltmiyor. **Mevcut üretim
ayarında PUSULA cümlesi hâlâ duyulmuyor.**

Kanıtın boyu: n = 1 — bir konuşmacı, bir okuma, bir kayıt. `medium`/1 aynı
cümleyi dün 3671 ms'de doğru duymuştu; `small`/5 + `hotwords` bugün 960 ms'de
doğru duydu.

*[Açıklama, ölçülmedi — EMİN DEĞİLİM: açgözlü çözümde (beam 1) ilk jeton
"Heyecan"a erken bağlanıyor; ipucu sonrasını kaydırsa da (*mısın → vesim*)
başı geri alamıyor. Beam 5 "Hey" dalını canlı tutuyor, ipucu "Jarvis"i o
dala itiyor. Çıktıyla uyumlu bir açıklama; mekanizma sınanmadı.]*

## 6. ADIM 4 — öneri: `small` + `beam_size=5` + `hotwords` (UYGULANMADI)

ETAP 1 şablonu:

1. **Ölçüldü mü?** Evet — aynı 15 kayıt, aynı çağrı, aynı koşu. Mevcut ayara
   göre 13 → 4 hata; düzelen 5 cümle, **bozulan sıfır**. PUSULA cümlesi
   yalnız bu kombinasyonda duyuldu.
2. **Bütçeye sığıyor mu?** Maliyet **ölçüldü**, varsayılmadı. Aynı cümlenin
   ipuçlu ve ipucusuz süresi eşleştirildi:

   | fark (aynı cümle) | medyan | en düşük … en yüksek |
   |---|---|---|
   | `hotwords` − ipucusuz, beam 1 | +4,7 ms | −31,0 … +25,0 |
   | `hotwords` − ipucusuz, beam 5 | +7,5 ms | −33,5 … +36,2 |
   | `initial_prompt` − ipucusuz, beam 1 | +14,1 ms | −24,4 … +31,5 |
   | beam 5 − beam 1 (ipucusuz) | +34,2 ms | **+11,0** … +75,6 |
   | önerilen bütün − mevcut | **+44,9 ms** | +5,1 … +69,1 |

   İpucunun maliyeti bu ölçümün çözünürlüğünün **altında**: cümle başına
   fark iki yöne ±30 ms salınıyor, medyanı +5–14 ms. Beam 5'in maliyeti ise
   gerçek — 15 cümlenin 15'inde pozitif. Önerilen bütünün maliyeti p50'de
   +%4,7 ve neredeyse tamamı beam'den geliyor. Bugün p90 1037 ms (bütçenin
   %69'u); dünkü koşulda ipucusuz `small`/5'in p90'ı 1388 ms'ydi (%93).
   Önceki raporun hükmü değişmedi: **bütçeyi belirleyen CPU**; bu öneri o
   sorunu ne yaratıyor ne çözüyor.
3. **Oynaklık payı var mı?** **Kısmen.** Çözücü deterministik — aynı ses iki
   oturumda aynı metni verdi — yani koşudan koşuya oynaklık yok. Oynaklık
   **okumadan okumaya** ve o ölçülmedi. Kazanç 6 hata / 76 kelime ama üç
   cümleden geliyor (#2, #8, #13), her biri tek okuma; "Hey Jarvis" n = 1.
   **Ölçülmemiş riskler:**
   - **Gürültü-yalnız klip:** Whisper'ın ipucu metnini gürültüye "kusma"
     ihtimali bu kayıtta sınanmadı. `vad_filter` açık ve saf sessizliği
     keser; VAD'den geçen gürültü için bilinmiyor [ÖLÇÜLMEDİ].
   - Doğal konuşma (bu kayıt okunan metin).
   - Beş kelimeden uzun bir liste (cihaz adları eklenince).

**Kararın niteliği:** olumlu ve önceki öneriden (*beam 5 tek başına, zayıf
olumlu*) güçlü — beam 5 tek başına PUSULA cümlesini düzeltmiyor ve #13'ü
bozuyordu. Ama kanıt dar. Üretime almadan önce ölçülmesi gereken iki şey:
**"Hey Jarvis"in birden çok okuması** ve **gürültü-yalnız klipte sızıntı.**
İkisi de ayrı karar.

**Nasıl geçirilir — BU KARTTA UYGULANMADI:**

- [voice/stt.py:350](voice/stt.py:350) `FasterWhisperTranscriber.__init__`:
  `beam_size: int = 1` ve `hotwords: Optional[str] = None` — varsayılanlar
  bugünkü davranış.
- [voice/stt.py:406](voice/stt.py:406) `transcribe(...)`:
  `beam_size=self.beam_size` (bugün `:409`'da sabit `1`); `hotwords` yalnız
  `None` değilse geçer — sondadaki `_yaziya` deseni, ipucusuz çağrının
  birebir aynı kaldığını bir testle kilitleyerek. `vad_filter=True`
  (`:415`) dokunulmaz.
- [voice/voice_loop.py:180](voice/voice_loop.py:180) `build_default_voice_io`:
  `whisper_model`'in yanına `whisper_beam_size` ve `whisper_hotwords`,
  `:212`'de `FasterWhisperTranscriber`'a iletilir.
- [main.py:68](main.py:68) bugün `build_default_voice_io`'ya hiçbir Whisper
  ayarı geçirmiyor. Değerin kaynağı o kartın kararı; ama kelime listesi
  `voice/stt.py`'ye gömülmemeli — model adları gibi yapılandırmadan gelmeli.
- **`beam_size` ve `hotwords` tek kartta, birlikte.** Ölçüm bunu kartın
  talimatından daha güçlü bir sebeple destekliyor: "Hey Jarvis" ancak ikisi
  **birlikteyken** düzeldi. Ayrı kartlarda açılsalar, hangisi önce gelirse
  gelsin, ilk kart PUSULA cümlesini düzeltmez.

## 7. Sondanın sınırları

- Satırlar sabit sırayla koştu (1 → 5); sıra karıştırılmadı. Isıl kayma
  olsaydı son satırları şişirirdi; satır 5'in (en son) p50'si 961, satır 1'in
  956 — büyük bir kayma görünmüyor.
- Tek koşu. WER tekrarlanabilir (çözücü deterministik), süreler değil (§2).
- WER ölçütü rakamı kelimeden ayırmaz: `iki` ↔ `2` hata sayılır. Ölçüt bu
  kartta değiştirilmedi. Referansta rakam yok, ama hipotezde çıkabildiğini
  ilk kez ipucu satırları gösterdi.
- `initial_prompt` yalnız beam 1'de ölçüldü; kartın matrisi bu kadar.

---

## 8. Kapı

```
pytest tests -q  alfabetik : 2011 geçti / 0 başarısız (2 xfail, 2 uyarı)
pytest tests -q  ters sıra : 2011 geçti / 0 başarısız (2 xfail, 2 uyarı)
ruff check .               : 283  (taban 283)
```

2007 → 2011: bu kartın dört testi. Çalışma ağacında yalnız üç dosya:
`scripts/olc_stt_turkce.py` (+139 / −3; silinen üç satır: eski `_yaziya`
imzası, çağrının kapanış satırı, `main`'in dağıtım satırı — `olc()` ve dünkü
ölçüm yolu değişmedi), `tests/test_olc_stt_turkce.py` (+63, dört test), bu
rapor. `voice/`, `eval/`, `agent/`, `agents/persona.py` farkı boş; repoda WAV
yok. **Hiçbir varsayılan değişmedi.**

---

## 9. Ara rapor (tek paragraf)

Sonda artık `hotwords` / `initial_prompt` alabiliyor; ipucusuz çağrı
üretimle birebir aynı (testle kilitli), `vad_filter` hiçbir yolda kapanmıyor.
Taban satırları tuttu — `small`/1 0,171, `small`/5 0,132, 15 cümlenin 15'inde
metin dünküyle karakter karakter aynı. `small`/5 + `hotwords` 10 → 4 hata,
bozulan **sıfır**; mevcut üretim ayarına göre 13 → 4, düzelen 5 cümle.
`small`/1'de `hotwords` ile `initial_prompt` aynı sonucu verdi: 3 düzelen,
1 bozulan (#9, `iki` → `2`). **"Hey Jarvis" yalnız beam 5 ve `hotwords`
birlikteyken duyuldu** — hiçbiri tek başına düzeltmiyor; mevcut üretim
ayarında cümle hâlâ *"Heyecan mısın"*. Kartın tahmini iki yerde yanıldı:
"Klimayı" üç ipucu satırının üçünde de düzeldi, "commit" hiçbirinde
düzelmedi. İpucunun maliyeti ölçümün çözünürlüğünün altında (eşleşik medyan
+5–14 ms); önerilen bütünün maliyeti +45 ms, neredeyse tamamı beam'den.
Mutlak süreler dünden ~%24 düşük, sebebi ölçülmedi. Öneri olumlu ama kanıt
dar (n = 1): üretime almadan önce "Hey Jarvis"in birden çok okuması ve
gürültü-yalnız klipte sızıntı ölçülmeli; `beam_size` ve `hotwords` tek kartta
birlikte parametreye çevrilmeli. Uygulanmadı.
