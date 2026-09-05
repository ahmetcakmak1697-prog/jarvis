# KART — Terazinin üç kusuru

**Durum:** Açık · **Karar:** Ahmet, 2026-09-05 — `local_main` **llama3.1'de kalır**, önce ölçüm düzelir
**Önceki kartlar:** `KART_kalite_dedektorleri.md`, `KART_A13_A14.md`, `KART_model_kiyasi.md` (üçü de kapandı)

Kıyas koşusu (`automation/MODEL_KIYASI_2026-09-04.md`) modelleri ölçerken
**teraziyi de** ölçtü. Ajanın kendi raporunda dürüstçe listelediği üç kusur var.
Bu kart onları kapatır. Model değişmez.

---

## Kusur 1 — Sızıntı dedektörü iki farklı şeyi karıştırıyor

qwen'in 6 "sızıntısının" 4'ü aynı ifade: *"size yardımcı olmaktan mutluluk
duyarım"*. Bu cümle persona'da **yasak örneği olarak** geçiyor. Yani model
talimatı geri okumuyor — persona'nın yasakladığı kalıbı kullanıyor. İkisi
ayrı kusur ve şu an aynı sayaca giriyor; üstelik `ai_boilerplate` sütununda
ikinci kez sayılıyor.

**Yapılacak:** Persona'nın **yasak örnekleri** bölümünü sızıntı korpusundan
çıkar. O ifadeler `ai_boilerplate`'in işi. `_instruction_ngrams()` zaten
"## " başlıklı blokları alıp kimlik önsözünü dışarıda bırakıyor — aynı
mantıkla yasak-örnek bloğu da dışarıda kalmalı.

**Dikkat:** Hangi bloğun "yasak örnekleri" olduğunu `agents/persona.py`'den
**ölçerek** bul, tahminle değil. Bloğu çıkardıktan sonra `KART_kalite_dedektorleri.md`'nin
işaret ettiği 6 llama sızıntısının hâlâ yakalandığını doğrula — o vakalar
gerçek sızıntı, kaybolmamalı.

## Kusur 2 — Kesilmelerin hepsi bütçe, model kararı değil

Kıyas koşusundaki 10 kesilmenin **hepsi** `num_predict=400` sınırına
çarpmış. Kayıtlı koşuda da öyleydi: kesilen cevaplar 1300–1500 karakterde
kümelenmiş (400 token × Türkçe ~3,3 kar/token ≈ 1320). `longform 0/4`'ü
"model uzun anlatamıyor" diye okumak yanlış — vaka "uzun anlat" diyor,
koşucu 400 token veriyor.

**Yapılacak, iki parça:**

**2a.** `eval/run_turkish_quality.py`, Ollama'nın döndürdüğü **`done_reason`**
alanını sonuç JSON'una yazsın. `"length"` = bütçe bitti, `"stop"` = model
kendi durdu. Kesilmenin sebebi böylece tahmin değil ölçüm olur. Rapor da
ikisini ayrı göstersin.

**2b.** `num_predict` vaka başına ayarlanabilsin: varsayılan **400 kalır**,
yalnız 4 `longform` vakası ~**1200** alır. Cerrahi değişiklik (§3) — 60
vakanın koşulu hiç değişmez.

## Kusur 3 — İki gerçek kusur ölçülüyor ama puanlanmıyor

`ai_boilerplate` ve `foreign_hits` hesaplanıyor, raporlanıyor, **puanlanmıyor.**
Kıyasta bunun bedeli görüldü:

- Yapay zekâ kalıbı: **qwen 11/64**, llama 0/64. Persona bunu açıkça yasaklıyor.
- Yabancı dil sızıntısı: qwen 3, llama 1. Örnek `t2_memory_002` —
  *"Eşinizin doğum günü 3 Mart'ta**Celebratory cake and balloons are a nice
  way to celebrate!**"* Cümle ortasında, boşluksuz İngilizce. **Bu vaka GEÇTİ.**

**Yapılacak:** İkisini de puanla — `failed_checks`'e gir. Persona'nın açık
yasağını çiğnemek, kodlama bozukluğu kadar nesnel bir kusurdur.

**Dikkat — yanlış pozitif riski `_FOREIGN` listesinde:** liste `" the "`,
`" and "`, `" you "` gibi parçalar içeriyor. Türkçe bir cevapta meşru olarak
geçebilecek İngilizce terimler var (kod, kütüphane adı, `git status`).
Puanlamaya bağlamadan önce **her iki modelin 128 cevabında** ölç: yanlış
pozitif çıkarsa listeyi daralt, kuralı gevşetme.

---

## Taban nasıl yeniden kurulur — bu kartın en kritik kısmı

`test_the_recorded_run_still_scores_49_of_64` **kayıtlı** 2026-09-01
cevaplarını puanlar. Üç kusurun taban üzerindeki etkisi farklı:

| Kusur | Kayıtlı cevapları etkiler mi? | Neden |
|---|---|---|
| 1 (sızıntı korpusu) | **Evet** | Puanlama mantığı değişiyor |
| 3 (kalıp + yabancı puanlanır) | **Evet** | Yeni ölçüt ekleniyor |
| 2 (num_predict, done_reason) | **Hayır** | Yalnız *gelecek* koşuları etkiler; kayıtlı cevaplar değişmez |

Yani 49 sayısı 1 ve 3 yüzünden değişecek. Değiştiğinde:

- Test **bilerek, kanıtla** güncellenir — sessizce değil (CLAUDE.md §13.1).
- Yeni sayı `automation/KALITE_TABAN_*.md`'ye ve `CLAUDE.md` §13.2'ye yazılır.
- `eval/turkish_quality_cases.json`'daki `passing_threshold` taban kayıtları
  da güncellenir (A14'te taban kaydına çevrilmişti).
- **Yeni bir hedef sayı yazılmaz** (A14 kararı yürürlükte).

Kusur 2 taban sayısını değiştirmez ama gelecek koşuları değiştirir; bunu
belgede açıkça ayır ki ileride biri iki etkiyi karıştırmasın.

## Yasaklar

1. **`config/runtime_profiles.json`'a dokunma.** `local_main` = llama3.1,
   Ahmet'in 2026-09-05 kararı. Bu kart yalnız ölçüm hattı.
2. Vaka metinlerini değiştirme. Yalnız kusur 2b'nin gerektirdiği
   `num_predict` alanı eklenir.
3. Bir dedektör yanlış pozitif veriyorsa **ölçerek** düzelt, gevşeterek değil.
4. Auto-fix retry yok: bir şey patlarsa yaz ve dur (§9).

## Bitti sayılma ölçütü

- Üç kusur da kapandı, her biri için düşen test önce yazıldı.
- `KART_kalite_dedektorleri.md`'deki 6 llama sızıntısı hâlâ yakalanıyor.
- Yeni taban sayısı ölçüldü, kilit testi güncellendi, üç belgeye yazıldı.
- `pytest tests -q` yeşil (alfabetik **ve** ters sıra), `ruff check .` ≤ 293.
- Commit: yalnız isimli dosya. Push yok. **Bittiğinde dur.**
