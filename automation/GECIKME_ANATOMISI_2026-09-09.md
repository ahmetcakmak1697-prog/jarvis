# Gecikmenin anatomisi — 10.954 ms nereye gidiyor?

**Ölçen:** Claude Code · **Tarih:** 2026-09-09 · **Dal:** `auto/opencode-deepseek`
**Kart:** `automation/KART_CLAUDE_GECIKME_ANATOMISI.md`
**Araç:** `scripts/olc_llm_anatomisi.py` · **Testler:** `tests/test_llm_anatomisi_olcumu.py` (15 test)
**Ham veri:** `automation/GECIKME_ANATOMISI_20260909-2146.json` (llama3.1),
`automation/GECIKME_ANATOMISI_20260909-2148.json` (llama3.2)

> Bu belge **hüküm vermez**. Ölçülen sayıları ve ölçülemeyeni yazar.
> Optimizasyon kararı Ahmet'indir.

---

## 0. Önce en önemli sonuç: taban sayı yeniden üretilemedi

Kart "10.954 ms'nin içini aç" diyor. İç açıldı, ama **o sayının kendisi bugün
çıkmadı.** Aynı soru, aynı model, aynı kod yolu:

| | 2026-09-06 tabanı | 2026-09-09 ölçümü |
|---|---|---|
| Soru | `nerede kaldik` | `nerede kaldik` |
| Model | `llama3.1:latest` | `llama3.1:latest` |
| Tur sayısı | 4 | 5 |
| **p50** | **10.954 ms** | **1.160 ms** |
| Turlar | 18.739 / 9.444 / 12.464 / 5.428 | 1.061 / 2.053 / 1.160 / 827 / 5.913 |
| Cevap uzunluğu | 70–96 karakter | 94–339 karakter |

Bugünkü ölçüm, **daha uzun cevaplar üretirken 9 kat hızlı.** Bu, tek başına
bir teşhis değildir; bir olgudur ve raporun geri kalanı onu bu şekilde ele
alır.

**Aritmetik köprü.** Bugün ölçülen üretim hızı 54,2–70,0 token/saniye. Eğer
10.954 ms'nin tamamı üretim olsaydı, model **594–767 token** üretmiş olurdu —
kabaca 2.100–2.700 karakter. Tabanın kaydettiği cevaplar **70–96 karakter**.
Yani taban sayı, bugünkü hızda o cevapların üretimiyle **açıklanamaz.**

Bugün gözlenen ve saniyeler mertebesinde duraklama üretebilen iki olgu var.
Hangisinin 2026-09-06'da rol oynadığı **ölçülmedi** — o koşu bu alanları
kaydetmiyordu:

1. **Soğuk model yükleme.** Bugün `llama3.2` (2,0 GB) ilk çağrıda
   `load_duration` = **4.170,8 ms** verdi; ısındıktan sonra 1,5–2,8 ms.
   `llama3.1` 4,9 GB'tır ve bu oturumda soğuk ölçülmedi. Tabanın ilk turu
   18.739 ms idi ve diğerlerinin ~2 katıydı.
2. **Prompt değerlendirme sıçraması.** Bugün `proje_durumu` sınıfının 5.
   turunda `prompt_eval_duration` = **5.051,6 ms** ölçüldü; bir önceki tur
   neredeyse aynı boyutta bir prompt'ta (2.396 → 2.445 token) **236,0 ms**
   idi. Yaklaşık **20 kat**. Mekanizma ölçülmedi.

---

## 1. Ölçüm nasıl yapıldı

`LocalJarvisAgent.chat()` tek bir duvar saati dilimidir; taban ölçümdeki
`model_ms` alanı o dilimin tamamıydı. Yeni araç aynı sırayı korur ama beş
parçaya ayırır:

| Dilim | Ne ölçülüyor |
|---|---|
| `arac_tespiti_ms` | `_detect_tool` |
| `arac_calistirma_ms` | `_run_tool` (egress kapısı **içinde**) |
| `prompt_insa_ms` | persona + proje bağlamı + hafıza + geçmiş birleştirme |
| `model_duvar_ms` | Ollama çağrısı, istemci tarafından görüldüğü kadarıyla |
| `sonrasi_ms` | temizlik + geçmiş + hafızaya yazma |

Ollama'nın kendi bildirdiği süreler `model_duvar_ms` **içindedir** ve
nanosaniyeden çevrilir (`prompt_eval_duration`, `eval_duration`,
`load_duration`, `total_duration`; sayaçlar `prompt_eval_count`,
`eval_count`). Çevrim testle kilitli.

**Ölçülemeyen alan `None` döner, `0` değil.** `0` "ölçtüm, sıfırdı" demektir;
`None` "ölçemedim" demektir ve ortalamaya girmez.

**Alan adı ölçtüğü şeyi söyler.** B11'de `first_token_ms` diye bir alan vardı
ve `prompt_eval_duration` taşıyordu — TTFT değil. Bu araçta öyle bir alan yok
ve bir test bunu koruyor.

### Ölçülmeyenler

- **STT ve TTS yok.** Bu araç metin girer, metin çıkar. Ses hattının uçtan uca
  süresi ayrı bir karttır (`scripts/olc_ses_gecikmesi.py`) ve VAD konuşma-sonu
  ile ilk-ses anları mevcut arayüzlerle hâlâ ölçülemiyor.
- **TTFT (ilk token) yok.** `stream=False` kullanılıyor; "ilk token" diye bir
  an yok. Akışlı TTS seçeneği bu yüzden ölçüme değil çıkarıma dayanır ve
  aşağıda öyle işaretlendi.
- **Egress kapısının kendi payı yok.** `_egress_kapisi` `_run_tool` içinde
  çağrılıyor; ayırmak ajanı yeniden yazmayı gerektirirdi. Üç soru sınıfının
  hiçbiri araç tetiklemedi, dolayısıyla bu tur bu dilimlerin ikisi de boş.
- **Ollama sunucusunun kuyruk beklemesi** `model_duvar_ms` ile
  `model_bildirilen_toplam_ms` farkının içindedir, ayrılmadı (medyan turlarda
  11–95 ms).

Koşu koşulları: `voice_mode = True` (taban ölçüm de ses yolundandı), model
ısınmış, sınıf başına 5 tur, sınıflar arasında RAM geçmişi sıfırlanır ama
**tur arasında sıfırlanmaz** — gerçek bir oturumda geçmiş birikir ve taban
ölçüm de böyle alınmıştı.

Ölçüm Ahmet'in **canlı hafızasına yazmaz**: `chat()` her turda
`add_conversation` + `auto_extract_info` çağırıyor ve bu iş `sonrasi_ms`'in
ölçtüğü şeyin ta kendisi, atlanamaz. Bu yüzden veritabanı ve profil geçici bir
dizine kopyalanır, ajan kopyaya bağlanır. Okuma gerçek kalır (prompt boyutu
gerçekçi olmalı), yazma geçicidir.

---

## 2. llama3.1:latest — üç soru sınıfı × 5 tur

Sayılar milisaniye, `p50` / `p95`.

| | kısa olgusal | proje durumu | uzun anlatım |
|---|---|---|---|
| Araç tespiti | 0,1 / 0,2 | 0,1 / 0,1 | 0,1 / 0,1 |
| Araç çalıştırma | *tetiklenmedi* | *tetiklenmedi* | *tetiklenmedi* |
| Prompt inşası | 1,8 / 21,8 | 1,6 / 1,7 | 1,4 / 2,2 |
| **Model (duvar)** | **460,1 / 722,0** | **1.155,2 / 5.136,4** | **15.883,1 / 16.582,6** |
| · model yükleme | 2,1 / 2,4 | 1,9 / 2,1 | 2,1 / 2,6 |
| · prompt değerlendirme | 158,4 / 187,2 | 198,2 / 4.088,5 | 1.097,2 / 1.132,4 |
| · **üretim** | **287,3 / 532,4** | **908,6 / 1.684,4** | **14.644,9 / 16.215,9** |
| Sonrası (hafıza/kayıt) | 2,9 / 5,9 | 3,0 / 3,2 | 3,9 / 5,4 |
| **TOPLAM** | **464,5 / 726,9** | **1.159,8 / 5.141,2** | **15.890,3 / 16.588,8** |
| Üretilen token (p50) | 19 | 55 | 1.024 |
| Prompt token (p50) | 2.215 | 2.329 | 3.299 |
| Token/saniye (p50) | 66,0 | 58,3 | 69,9 |

### Payların dağılımı (her sınıfın **medyan turu** üzerinde)

Yüzdeler medyan turdan hesaplandı; p50'lerin toplamı turun p50'si değildir.

| Sınıf | Toplam | Üretim | Prompt değ. | Yükleme | **Bizim kodumuz** | Atfedilmemiş |
|---|---|---|---|---|---|---|
| kısa olgusal | 464,5 ms | **61,9 %** | 34,1 % | 0,5 % | **0,9 %** | 2,6 % |
| proje durumu | 1.159,8 ms | **81,4 %** | 17,1 % | 0,2 % | **0,4 %** | 1,0 % |
| uzun anlatım | 15.890,3 ms | **92,2 %** | 7,2 % | 0,0 % | **0,0 %** | 0,6 % |

"Bizim kodumuz" = araç tespiti + prompt inşası + sonrası. Üç sınıfta da
**4,4–7,2 ms**, yani turun **%1'inden azı.**

### Kartın sorusuna sayıyla cevap

> **10.954 ms'nin kaçı üretim, kaçı prompt işleme, kaçı bizim kodumuz?**

O sayı bugün yeniden üretilemedi (§0). Bugün aynı soru için ölçülen 1.159,8
ms'nin dağılımı: **%81,4 üretim, %17,1 prompt değerlendirme, %0,4 bizim
kodumuz.**

Bizim kodumuz için ölçüm, taban sayı için de bağlayıcıdır: turun Python
tarafı **8 ms'nin altında**. Proje bağlamı önbelleği ıskalasa bile yeniden
kurulumu **24,2 ms** (aşağıda ölçüldü). Yani 10.954 ms'nin **hiçbir anlamlı
kısmı bizim kodumuz olamaz** — hangi koşulda ölçülmüş olursa olsun.

Geri alınan "darboğaz prompt işleme" çıkarımı bu ölçümle **kısmen** karşılanır
ve ayrımı yapmak gerekir:

- *Bizim* prompt **inşamız** darboğaz değil: 1,4–1,8 ms.
- Modelin prompt **değerlendirmesi** p50'de %7–34 arasında, yani küçük değil
  ama baskın da değil.
- Ama p95'te aynı alan 4.088,5 ms'ye çıkıyor. **Prompt değerlendirme çift
  tepeli**: ya ~200 ms ya da saniyeler. Bu, tek bir p50 sayısının
  gizlediği en önemli davranış.

### Türev sayılar

| | değer |
|---|---|
| Token/saniye (15 tur, llama3.1) | medyan **64,3** · min 54,2 · maks 70,0 |
| Üretilen token, kısa olgusal | p50 **19** |
| Üretilen token, proje durumu | p50 **55** (aralık 31–106) |
| Üretilen token, uzun anlatım | p50 **1.024** — bu bir **tavan** |

**Uzun anlatım sınıfı her turda tam 1.024 token üretti.** Bu, doğal cevap
uzunluğu değil `num_predict = 1024` tavanıdır ve cevaplar 4.001 karakterde
**kesiliyor**. Yani o sınıfın 15.890 ms'si "modelin söyleyecekleri bitene
kadar" değil, "bütçe bitene kadar" geçen süredir.

---

## 3. Bizim kodumuzun tam maliyeti (ayrı ölçüm)

Tur içi `prompt_insa_ms` 1,4–1,8 ms çıkıyor çünkü proje bağlamı
`__init__`'te bir kez kurulup parmak iziyle önbelleğe alınıyor (B06). Turun
göremediği maliyet ayrıca ölçüldü:

| Ne | Süre | Ne zaman ödenir |
|---|---|---|
| `agent.local_agent` import | 63,3 ms | süreç başına bir kez |
| `LocalJarvisAgent()` kurulumu | 573,8 ms | oturum başına bir kez |
| Proje bağlamı — önbellek **isabeti** | 0,54 ms | her tur |
| Proje bağlamı — önbellek **ıskası** | 24,2 ms | kaynak dosya değişince |

Oturum başına 574 ms'lik kurulum, kullanıcının ilk sorusundan **önce**
ödenir. PUSULA aralığının içinde değildir.

### Prompt neyden oluşuyor (proje durumu sorusu, `tier = mid`)

Toplam 6.321 karakter ≈ 2.330 token:

| Parça | Karakter | Pay |
|---|---|---|
| persona (`build_system_prompt`) | 3.156 | **49,9 %** |
| `LOCAL_AGENT_ADDENDUM` | 833 | 13,2 % |
| proje bağlamı | 1.437 | 22,7 % |
| hafıza | 335 | 5,3 % |
| `VOICE_MODE_DIRECTIVE` | 547 | 8,7 % |
| kullanıcı mesajı | 13 | 0,2 % |

---

## 4. llama3.2:latest — kartın adını verdiği ölçülmemiş seçenek

Aynı betik, aynı üç sınıf, `--model llama3.2:latest`. Profil dosyasına
dokunulmadı (kart sınırı); model yalnız komut satırından geçirildi.

| | kısa olgusal | proje durumu | uzun anlatım |
|---|---|---|---|
| TOPLAM p50 | **157,6 ms** | **201,0 ms** | **8.457,0 ms** |
| Üretim p50 | 74,3 ms | 130,6 ms | 7.829,6 ms |
| Prompt değ. p50 | ~66 ms | 53,3 ms | 544,0 ms |
| Üretilen token p50 | 11 | 19 | 1.024 |
| **Token/saniye p50** | **148,1** | **145,5** | **130,8** |

**Soğuk yükleme burada ölçüldü:** llama3.2'nin ilk turu `load_duration` =
**4.170,8 ms** (2,0 GB). Sonraki 14 turda 1,5–2,8 ms. Bu yüzden o sınıfın
p95'i 3.766,7 ms, p50'si 157,6 ms.

Karşılaştırma yaparken iki şeyi ayırmak gerekiyor:

- **Token başına hız:** llama3.2, proje durumu sınıfında **2,50 kat** hızlı
  (145,5 / 58,3 token/s). Üç sınıfın medyanında **2,03 kat** (130,8 / 64,3).
- **Tur süresi:** proje durumu p50 201,0 ms'ye karşı 1.159,8 ms — **5,8 kat**.
  Ama llama3.2 o soruya **19 token**, llama3.1 **55 token** ile cevap verdi.
  Farkın büyük kısmı hızdan değil, **cevabın kısalığından** geliyor.

Cevabın kısa olması iyi mi kötü mü, bu ölçümün söyleyebileceği bir şey
değildir. **llama3.2'nin Türkçe kalitesi ölçülmedi.**

---

## 5. Seçenekler — her biri hangi ölçüme dayanıyor, ne feda ediliyor

Kartın kuralı: desteklenmeyen seçenek yazılmaz. Aşağıdakilerin hepsinin
arkasında bu rapordaki bir sayı var. **Hiçbiri önerilmiyor.**

### A. Cevap uzunluğunu sınırlamak

- **Dayanak:** üretim, turun %61,9–92,2'si. Süre token sayısıyla neredeyse
  doğrusal: 64,3 token/s medyanda her 100 token ≈ **1,56 saniye**. Proje
  durumu sınıfında turlar 31–106 token ürettti ve toplam 827–2.053 ms arasında
  gezindi.
- **Şu an ne oluyor:** tavan `num_predict = 1024` ve uzun anlatım sınıfı her
  turda tavana çarpıyor — cevaplar zaten kesiliyor.
- **Feda edilen:** Türkçe kalite tabanı 49/64, uzun anlatım vakalarına
  **1.200 token** bütçe vererek ölçüldü
  (`automation/TERAZI_DUZELTMELERI_2026-09-05.md`). Tavanı 1.200'ün altına
  çekmek o vakaların ölçüm koşulunu değiştirir; etkisi **ölçülmedi** ve
  bilmek için 64 vakalık süitin yeniden koşması gerekir. Ayrıca terazi
  "kesilme" dedektörü taşıyor — erken kesilen cevap puan kaybedebilir.

### B. Daha küçük model (`llama3.2:latest`)

- **Dayanak:** §4. Token başına 2,03–2,50 kat hız. Proje durumu sorusunda tur
  p50'si 201,0 ms.
- **Feda edilen:** Türkçe kalitesi **ölçülmedi**. Kayıtlı taban
  `llama3.1:latest` için 49/64 ve modeller arası karşılaştırma ancak aynı
  terazide yapılabilir (A11: aynı model aynı puanlayıcıda bile koşular arası
  oynuyor). Karar öncesi `eval/run_turkish_quality.py` ile 64 vakalık koşu
  gerekir. Ayrıca `config/runtime_profiles.json` bir imza dosyasıdır; model
  değişimi Ahmet'in kararıdır.

### C. Akışlı TTS — ilk cümle bitince konuşmaya başlamak

- **Dayanak:** proje durumu sorusunda üretim turun %81,4'ü. İlk token'dan
  önce ödenen ölçülmüş maliyet, prompt değerlendirme (p50 198,2 ms) + bizim
  kodumuz (4,6 ms) ≈ **~200 ms**.
- **[EMİN DEĞİLİM]** Bu, ilk token'ın ~200 ms'de geleceğini **kanıtlamaz**.
  `stream=False` kullanıldığı için TTFT bu raporda **ölçülmedi**; yukarıdaki
  sayı bir alt sınırdır. Gerçek TTFT ancak `stream=True` ile ölçülür.
- **Feda edilen:** toplam süre **düşmez**, yalnız algılanan süre düşer.
  `_ask_ollama` sözleşmesi değişir (`stream=True`), ses hattı cümle sınırı
  bölmesi ister. Bu bir **mimari değişikliktir** ve CLAUDE.md §9 gereği
  Ahmet'in imzası olmadan uygulanmaz.

### D. Prompt küçültmek

- **Dayanak (zayıf):** prompt değerlendirme p50'de 158,4–198,2 ms, yani proje
  durumu turunun %17,1'i. Prompt'un yarısı silinse p50'de kazanç **~100 ms**
  mertebesinde kalır. Persona tek başına %49,9, proje bağlamı %22,7.
- **Dayanak (güçlü olabilir, ölçülmedi):** p95'te aynı alan 4.088,5 ms ve
  gözlenen 5.051,6 ms'lik sıçrama o sınıfın **en büyük prompt'unda** oldu
  (2.445 token). Prompt boyutu ile sıçrama arasında bir ilişki olup olmadığı
  **ölçülmedi** — tek gözlem ilişki kanıtı değildir.
- **Feda edilen:** proje bağlamı PUSULA'nın ikinci şartıdır ("repo'nun o anki
  gerçek durumu"). Onu kısmak cevabın doğruluğunu hıza satmaktır. Persona
  kimlik/sadakat SSOT'udur (`agents/persona.py`).

### Bir de şu ölçüm var, seçenek değil ama karara girer

`proje_durumu` sınıfının **p50'si 1.159,8 ms** ve PUSULA hedefi 1.500 ms.
Yani bu soru için **metin tarafı bugün hedefin altında.** Ama:

- Aynı sınıfın **p95'i 5.141,2 ms**, hedefin 3,4 katı.
- Bu sayı **STT ve TTS içermez.** PUSULA aralığı bunları içerir ve o uçlar
  hâlâ ölçülemiyor.

Yani "hedefe girdik" **denemez**; söylenebilecek olan: hedefin dışında
kaldığı düşünülen sürenin çok büyük kısmı bugün ölçüldüğünde yoktu.

---

## 6. Yol boyunca görülen, dokunulmayan şeyler

CLAUDE.md §3 gereği: görüldü, söylendi, düzeltilmedi.

1. **`LocalJarvisAgent.__init__` `self.memory`'yi iki kez atıyor.**
   Önce `self._load_memory()` (→ `LocalMemory`), hemen ardından
   `from memory.memory_manager import JarvisMemory; self.memory = JarvisMemory()`.
   Birincisi bu yolda **ölü**. `agent/local_agent_memory.py` ayrıca
   `chat()`'in çağırdığı `add_conversation` / `get_context_for_prompt` /
   `auto_extract_info` metotlarını **taşımıyor** — yani o atama canlı olsaydı
   `chat()` patlardı.
2. **Ollama `load_duration` alanını bazen hiç göndermiyor.** Aynı model, aynı
   seçenekler, arka arkaya üç çağrı: 1.913.300 ns, 1.550.400 ns, **yok**.
   Betik bunu `None` olarak raporluyor (uydurmuyor), ama model yükleme payı
   bu yüzden her turda bilinemiyor.
3. **`tests/test_quality_runner_api_provider.py::test_anahtar_yoksa_ACIK_hata_verir`
   kararsızdı — kök neden bu oturum sırasında başka bir oturumda düzeltildi.**
   Ölçüm başlarken alınan taban koşusunda test **başarısız** oldu; aynı
   komutla hemen sonraki koşuda **geçti**, tek başına da geçiyordu. Başarısız
   koşu 120 s, geçen koşu 78 s sürmüştü ve o 42 saniyelik fark bir ağ
   çağrısını düşündürüyordu. Bu şüphe **doğrulandı ama benim tarafımdan
   değil**: `3b44d80 fix(olcum): frontier kosusu agi olcup modele not
   veriyordu` tam bu dosyayı (226 satır) ve `eval/run_turkish_quality.py`'yi
   değiştirdi. Düzeltmeden sonraki üç tam süit koşusunda (iki sıra) test
   geçti. §9 gereği ben dokunmadım.

   İkincil not: o iki commit (`3b44d80`, `088f3b6`) bu ölçüm sürerken aynı
   dala düştü. Kapı sayıları **düştükten sonra** yeniden alındı; raporlanan
   1928/1928 commit `ef76243` ağacına aittir.

---

## 7. Bitti sayılma ölçütü — durum

| Ölçüt | Durum |
|---|---|
| `scripts/olc_llm_anatomisi.py` var, testleri var, kırmızı görüldü | ✅ 15 test, `ModuleNotFoundError` ile kırmızı görüldü, sonra yeşil |
| Üç soru sınıfı × 5 tur, her bileşen ayrı sayı | ✅ §2 (ayrıca llama3.2 için §4) |
| "10.954 ms'nin kaçı üretim" sayıyla cevaplı | ✅ §2 — ve sayının kendisinin üretilemediği §0'da |
| Seçenekler ölçüme bağlı, hüküm verilmemiş | ✅ §5 |
| Kapı iki sırada yeşil | ✅ alfabetik **1928 geçti / 0 başarısız**, ters sıra **1928 geçti / 0 başarısız** (2 xfail) |
| `ruff check .` ≤ 283 | ✅ **283** — yeni iki dosya sıfır bulgu ekledi |

Not: taban `ruff check .` sayısı da **283**. İlk okuduğum 287, `.ruff_cache`
bayat olduğu için çıkmıştı; `--no-cache` ile 283 doğrulandı. Yani kartın
verdiği eşik tabanın **tam üstüdür**, bir yer bile boşluk yok — yeni dosyalar
sıfır bulgu ekleyecek şekilde yazıldı.

---

## 8. Ölçüm nasıl tekrarlanır

```bash
export PYTHONPATH="$(pwd)"
python scripts/olc_llm_anatomisi.py --tur 5
python scripts/olc_llm_anatomisi.py --tur 5 --model llama3.2:latest
python scripts/olc_llm_anatomisi.py --tur 5 --sinif proje_durumu
```

Betik `automation/GECIKME_ANATOMISI_<damga>.json` yazar. Mikrofon
gerektirmez; girdi sabit metindir.
