# KART — A13 ve A14 kapatma

**Durum:** Açık · **Karar sahibi:** Ahmet, 2026-09-04, ikisi de onaylandı
**Önceki kart:** `automation/KART_kalite_dedektorleri.md` (kapandı — `b82dd72`, `1473ab6`)

Küçük iş. İki açık karar `automation/AHMET_ONAYI_BEKLEYENLER.md`'de bekliyordu;
Ahmet ikisini de karara bağladı. Bu kart yalnız o kararları uygular.

---

## A13 — tekrar eşiği 3'te kalır, 2× raporlanır

**Karar:** `REPETITION_MIN_HITS = 3` **değişmez**. 2× eşiğinin sonucu ayrıca
ölçülüp **raporlanır ama puanlanmaz**.

**Gerekçe (kayda geçsin):** 2×'in "bu koşuda yanlış pozitif yok" ölçümü tek
modelin 64 cevabı üzerinde yapıldı. Bu takımın varlık sebebi modelleri
kıyaslamak; llama3.1'de temiz olan eşik başka modelde paralel kurulu bir
listede tökezleyebilir — dedektör liste **işaretini** atıp **içeriğini**
bıraktığı için (ki bu doğru karardır). Asimetri `_NO_RECORD_ROOTS`'un başındaki
notun aynısı: iyi bir cevabı haksız yere düşürmek ölçümün kendisini çürütür.

2× sayısını kaybetmemek için raporlanır: ikinci model ölçüldüğünde eşiği
yeniden koşturmadan karar verilebilsin.

### Yapılacak

`eval/quality_scorer.py`:
- Yeni sabit, gerekçesiyle: `REPETITION_REPORT_MIN_HITS = 2`.
- `score_answer()` çıktısına raporlanan alan(lar) ekle — 2× eşiğini aşan dizi
  var mı ve varsa hangisi. Adlandırmada mevcut `repeated_phrase` desenini izle.
- **`failed_checks`'e GİRMEZ.** `has_efendim` / `ai_boilerplate` ile aynı
  sınıftadır: ölçülür, yazılır, puanlanmaz.
- Boş cevap dalındaki sözlüğe de karşılık gelen varsayılanı ekle (o dal
  tüm alanları açıkça listeliyor).

`eval/run_turkish_quality.py`:
- Ölçüm tablosuna satır ekle, mevcut biçimi izle:
  `| Tekrar 2× (raporlanır, puanlanmaz) | N/64 |`
- JSON çıktısına da yaz.

---

## A14 — `passing_threshold.overall_v2` hedef olmaktan çıkar, kayıt olur

**Olgu:** Bu alanı **hiçbir Python kodu okumuyor**. Yalnız
`eval/turkish_quality_cases.json` içinde metin, artı iki belgede anılıyor.
Yani makine kapısı değil, insan için bir yorum — ve şu an yanlış yönlendiriyor.

**Karar:** Yeni bir hedef sayı **yazılmaz** (">=47" vb. yasak — az önce
kurtulduğumuz "sayıyı tutturmaya oynama" baskısını geri getirir). Alan bir
**taban kaydına** dönüşür.

### Yapılacak

`eval/turkish_quality_cases.json` → `passing_threshold.overall_v2`:
- Değeri, hedef değil kayıt olacak biçimde yaz. Anlamı şu olmalı:
  **49/64 — llama3.1:latest, puanlayıcı v2, 2026-09-03.** Regresyonun tanımı
  "aynı model, aynı puanlayıcı, bu sayının altı".
- Blokta anahtar adı `overall_v2` kalabilir; isim değiştirmek gereksiz kırılma.
  Önemli olan içeriğin hedef değil taban okunması.
- Bloktaki diğer alanlar aynı hatayı taşıyorsa (eski puanlayıcıya göre
  kalibre edilmiş hedefler) onları da aynı mantıkla düzelt; taşımıyorsa dokunma.

`automation/AHMET_ONAYI_BEKLEYENLER.md`:
- A13 ve A14'ü **Resolved**'a taşı. Her biri için: kararın kendisi, tarih
  (2026-09-04), karar sahibi (Ahmet) ve yukarıdaki gerekçenin özeti.

`automation/KALITE_TABAN_2026-09-03.md`:
- §100 civarındaki A14 maddesi artık açık değil; kapandığını ve nasıl
  kapandığını yaz.

---

## Kabul ölçütü — en önemli madde

**Skor 49/64 DEĞİŞMEYECEK.** Bu kart puanlanan hiçbir şeye dokunmuyor:
bir raporlanan sinyal ekliyor ve bir belge dizesini düzeltiyor. Koşuyu
yeniden puanladığında 49 çıkmıyorsa bir yeri yanlış bağlamışsındır —
düzeltmeden devam etme.

Kalanlar:
- `pytest tests -q` yeşil, alfabetik **ve** ters sıra.
- `ruff check .` **≤ 293** (artmayacak).
- Yeni alanlar için test yaz; önce düşen testi gör, sonra geçir.
- Commit: yalnız isimli dosya (`git add -A` yasak). Push yok.
- Bittiğinde **dur**, sıradaki karta geçme (CLAUDE.md §9).
