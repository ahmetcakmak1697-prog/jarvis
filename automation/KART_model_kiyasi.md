# KART — İki modeli yeni terazide yan yana koy

**Durum:** Açık · **Önceki kartlar:** `KART_kalite_dedektorleri.md`, `KART_A13_A14.md` (ikisi de kapandı)

Terazi kuruldu (üç dedektör + kilitli taban). Bu kart onu ilk kez asıl işi için
kullanıyor: **iki modeli aynı koşulda ölçmek.**

---

## Neden şimdi

`llama3.1:latest` puanlayıcı v2'de **49/64**. Üç ölçülmüş sıkıntısı var:

- **VRAM tavanını aşıyor:** tepe 6202 MB, belgelenmiş pratik tavan 6144 MB
  (`docs/HARDWARE_AND_LOCAL_LLM_RESEARCH.md` §3). Aşan model katman katman
  RAM'e taşar.
- **Sistem prompt'unu sızdırıyor:** 6 vaka.
- **Uzun anlatımda tamamen bozuk:** longform 0/4.

`qwen2.5:7b` makinede kurulu (4.7 GB) ve daha önce 5386 MB tepe VRAM ile
ölçülmüştü — tavanın 758 MB altında. Ama o ölçüm **eski puanlayıcıyla** yapıldı,
yani bugünkü 49 ile kıyaslanamaz. Aynı terazide ölçülmesi gerekiyor.

---

## Yapılacak iş

### 1. İki canlı koşu, aynı oturum, aynı koşullar

```
python -m eval.run_turkish_quality --model llama3.1:latest
python -m eval.run_turkish_quality --model qwen2.5:7b
```

Arka arkaya, aynı makine durumunda. Koşular arasında başka ağır iş çalıştırma —
VRAM ölçümü sistem geneli, kirlenir (raporun kendi uyarısı).

### 2. Kıyas belgesi

`automation/MODEL_KIYASI_2026-09-04.md` (mevcut `MODEL_KIYASI_0901.md`'nin
biçimini izle, üzerine yazma). İçinde en az:

- Kategori kategori yan yana tablo: llama3.1 canlı · qwen2.5 canlı
- **Neden dağılımı** yan yana: sızıntı / tekrar / kesilme / uydurma kaç vaka
- Hız: ham tok/s, Türkçe-eşdeğer tok/s, ilk token
- Tepe VRAM ve tavanı aşıp aşmadığı
- 2× tekrar sayısı (raporlanan sinyal — A13'te bunun için tutuldu)

### 3. A11 için oynaklık verisi — bu koşunun ikinci ürünü

`llama3.1` **canlı** sonucunu, aynı modelin **kayıtlı** 49/64'üyle karşılaştır.
Aradaki fark saf oynaklıktır: model aynı, puanlayıcı aynı, değişen yalnız koşu.
Bunu kıyas belgesinde ayrı bir başlık olarak yaz — A11 aylardır bu veriyi
bekliyor, ilk gerçek ölçüm bu olacak.

---

## Yasaklar — bu kartın en önemli kısmı

1. **49/64 tabanına DOKUNMA.** O sayı *kayıtlı* cevapların puanlanmasıdır;
   oynaklık içermez ve `test_the_recorded_run_still_scores_49_of_64` ile
   kilitlidir. Canlı koşu **başka bir şey** ölçer. Canlı sonucu taban diye
   hiçbir yere yazma, testi değiştirme.
2. **`config/runtime_profiles.json`'a DOKUNMA.** Bu kart kanıt üretir, model
   değiştirmez. `local_main`'i değiştirmek stratejik bir karardır ve Ahmet'e
   aittir (CLAUDE.md §9, DANIŞMAN MODU).
3. **Hangi modelin "kazandığını" ilan etme.** Tabloyu kur, farkı göster,
   kararı Ahmet'e bırak. Sayılar eşitse ya da takas varsa (biri hızlı diğeri
   doğru) bunu açıkça yaz — tek bir "daha iyi" cümlesine sıkıştırma.
4. Vaka dosyasına, dedektörlere, eşiklere dokunma. Ölçüm hattı dondu.

## Bitti sayılma ölçütü

- İki koşu tamamlandı, ham JSON + md raporları repoda.
- Kıyas belgesi yazıldı; içinde llama3.1 canlı-vs-kayıtlı oynaklık başlığı var.
- `pytest tests -q` yeşil (alfabetik **ve** ters sıra), `ruff check .` ≤ 293.
- Taban testi hâlâ 49 diyor.
- Commit: yalnız isimli dosya. Push yok. **Bittiğinde dur.**

## Eğer bir şey ters giderse

Koşu çökerse, model yüklenmezse ya da VRAM ölçümü alınamazsa: **otomatik
düzeltip tekrar deneme** (CLAUDE.md §9 — auto-fix retry NOT APPROVED).
Neyin patladığını yaz ve dur.
