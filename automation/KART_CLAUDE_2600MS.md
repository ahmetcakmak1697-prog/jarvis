# KART — Açıklanamayan 2.615 ms: gerçek darboğaz burada

**Kime:** Claude Code (VS Code) · **Veren:** Ahmet, 2026-09-09
**Dal:** `auto/opencode-deepseek` · **Taban:** `f4fae54`

---

## Durum

İki ölçüm birbirini tutmuyor ve fark **tek yönlü**:

| | ilk sese kadar |
|---|---|
| Sentetik ölçüm (`TTS_ANATOMISI`, 20 nokta) | 577–1.052 ms |
| Canlı turlardan çıkarım (5 tur, mikrofonlu) | ~3.500 ms |

`TTS_ANATOMISI_2026-09-09.md` §1: model canlı beş noktanın **hepsini birden**
az tahmin ediyor, ortalama **+2.615 ms**. Hepsi aynı yönde — gürültü değil.

Üç aday yazılmış, biri elenmiş:

1. **Metin farkı** — canlı veri gerçek JARVIS cevaplarıydı, sentetik ölçüm düz
   nesir. Noktalama ve sayı, karakter başına ses süresini değiştirir. **AÇIK.**
2. **Makine yükü** — aynı koşuda `model_ms` 4.367 ms'lik bir sıçrama gösterdi
   (diğerleri 475–1.068 ms). O akşam üç ajan + pytest aynı anda dönüyordu.
   **AÇIK.**
3. **Ölçüm sınırı** (`VoiceIO.say()` vs `EdgeTTSAdapter.speak()`) — incelendi,
   2,6 saniyeyi açıklamıyor. **ELENDİ.**

**Bu 2.615 ms projenin şu anki tek gerçek gecikme sorunudur.** Sentetik ölçüm
"1.340 ms, hedeftesin" diyor; Ahmet'in kulağı 20 saniye duyuyor. İkisi
arasındaki fark burada.

---

## ADIM 0 — Önce kaybı kapat (küçük ama şart)

`scripts/olc_ses_gecikmesi.py` ham veriye **cevap metnini kaydetmiyor**, yalnız
`cevap_uzunluk`. Bu yüzden o akşamki turlar **tekrar oynatılamıyor** ve aday 1
doğrudan sınanamıyor.

Cevap metnini JSON'a ekle. Gerekçe: bu bir ölçüm aracıdır ve ölçtüğü girdiyi
saklamayan bir araç, kendi sonucunu bir daha üretemez. Metin JARVIS'in kendi
çıktısıdır, kişisel veri değildir; yine de rapora (`.md`) değil yalnız ham
veriye (`.json`) yazılır.

## ADIM 1 — Canlı hattı yeni damgalarla koştur (mikrofonsuz)

`--kuru` modu STT'yi atlar ama **model + TTS'i gerçekten çalıştırır.** Yani
Ahmet gerekmez.

`EdgeTTSAdapter.speak()` artık beş olay damgası üretiyor. Bunları
`olc_ses_gecikmesi.py`'nin tur kaydına **geçir** — `sentez_ve_oynatma_ms`
tek bir sayı olarak kalmasın, `sentez_ms` / `oynatici_kurulum_ms` /
`oynatma_ms` ayrı ayrı kaydedilsin.

Sonra `--kuru --tur 10` koş, **gerçek JARVIS cevaplarıyla.**

**Bu koşu tek başına kararı verir:**

- `sentez_ms` sentetik ölçümdeki 573–1.048 ms bandında çıkarsa → fark
  **metinden değil**, aday 1 elenir.
- `sentez_ms` 3 saniyeye çıkarsa → gerçek cevaplar Microsoft'a farklı bir
  bedel ödetiyor demektir (uzunluk? noktalama? Türkçe karakter?) ve o zaman
  **ne olduğu** ölçülür.

## ADIM 2 — Makine yükünü ayır

Aynı koşuyu **sessiz makinede** tekrarla: başka ajan yok, pytest yok, tarayıcı
yok. `model_ms` sıçraması kayboluyor mu?

Kayboluyorsa aday 2 doğrulanmış olur ve sonuç şudur: **JARVIS yavaş değil,
o akşam makine doluydu.** Bu bir düzeltme değil, bir ölçüm koşulu kuralıdır ve
`FAILURES.md`'ye yazılır — çünkü aynı hataya üç kez düştük (mutasyon kapısı,
kalite koşusu, şimdi bu).

Kaybolmuyorsa gerçek bir gecikme var ve aranmaya devam edilir.

## ADIM 3 — Hüküm verme, sayıyı yaz

`automation/GECIKME_ACIKLAMASI_2026-09-09.md`:

- 2.615 ms'nin kaçı metin, kaçı yük, kaçı hâlâ açıklanamıyor
- Açıklanamayan kısım kalırsa **[EMİN DEĞİLİM]** ile ve bir sonraki adayla
  birlikte yazılır
- `SES_HATTI_COZUMLEME_2026-09-09.md` (benim yanlış çıkarımım) bu bulguyla
  **düzeltilir** — silinme, üstüne "bu bölüm çürütüldü, sebebi şu" yazılır

---

## Sınırlar

- Edge TTS bayrağı yalnız ölçüm sürecinde tanımlanır; `.env` okunmaz (§9).
- `main.py` davranışı değişmez. Bu kart ölçer.
- Akışlı TTS **uygulanmaz** — o mimari değişiklik ve imza bekliyor. Ayrıca
  bu ölçüm bitmeden tavanının ne olduğu bilinmiyor.
- Kapı: `pytest tests -q` **iki sırada**, `ruff check .` **≤ 283**.
- Auto-fix retry yok. Push yok. Bitince **DUR**.

## Bitti sayılma ölçütü

- Ham veri artık cevap metnini taşıyor.
- Tur kaydı `sentez_ms` / `oynatici_kurulum_ms` / `oynatma_ms` ayrı ayrı içeriyor.
- 10 turluk kuru koşu ve sessiz-makine koşusu yapıldı.
- "2.615 ms'nin kaçı ne" sorusu **sayıyla** cevaplı; kalan varsa işaretli.
- Kapı iki sırada yeşil, ruff ≤ 283.
