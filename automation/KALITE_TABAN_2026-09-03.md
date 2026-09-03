# Kalite tabanı yeniden tanımlandı — 2026-09-03

**Kaynak kart:** `automation/KART_kalite_dedektorleri.md`
**Değişen:** ölçüm. **Değişmeyen:** model, prompt, routing, vaka metinleri.

---

## Tek cümle

Aynı 64 cevap, aynı model (`llama3.1:latest`, 2026-09-01 koşusu):
**eski puanlayıcı 63/64 diyordu, yeni puanlayıcı 49/64 diyor.**

Bu bir regresyon değil. Model o gün de bugünkü kadar kusurluydu; makine
kusurun on beşte on dördünü göremiyordu. Sayının düşmesi ölçümün
düzelmesidir.

Karşılaştırma **model sabit tutularak** yapıldı: yeni bir canlı koşu
yapılmadı, kayıtlı cevaplar yeniden puanlandı. Böylece 63 → 49 farkının
tamamı ölçüm değişikliğine aittir; koşular-arası oynaklık
(`AHMET_ONAYI_BEKLEYENLER.md` → A11) bu sayıya karışmıyor.

## Kategori kırılımı (aynı cevaplar, yeni puanlayıcı)

| Kategori | Eski | Yeni |
|---|---|---|
| tone | 20/20 | 19/20 |
| turkish | 15/15 | 13/15 |
| technical | 10/10 | 5/10 |
| mixed | 5/5 | 3/5 |
| memory | 5/5 | **5/5** |
| grounding | 4/5 | 4/5 |
| longform | 4/4 | **0/4** |
| **toplam** | **63/64** | **49/64** |

`memory` 5/5 kaldı ve `grounding` değişmedi: yeni dedektörler doğru
cevapları cezalandırmıyor. `longform` 0/4 — uzun cevapların **hepsi**
hem dejenere oluyor hem yarıda kesiliyor.

## Düşen 15 vaka

| id | kategori | neden |
|---|---|---|
| t1_tone_013 | tone | prompt_leak |
| t1_tr_006 | turkish | prompt_leak |
| t1_tr_014 | turkish | prompt_leak, truncated |
| t1_tech_002 | technical | grounding |
| t1_tech_003 | technical | truncated, grounding |
| t1_tech_004 | technical | grounding |
| t1_tech_008 | technical | prompt_leak |
| t1_tech_010 | technical | grounding |
| t1_mix_003 | mixed | prompt_leak |
| t1_mix_004 | mixed | prompt_leak, truncated |
| t2_grounding_003 | grounding | grounding (zaten düşüyordu) |
| t2_longform_001 | longform | repetition, truncated |
| t2_longform_002 | longform | truncated |
| t2_longform_003 | longform | repetition, truncated |
| t2_longform_004 | longform | repetition, truncated |

Neden sayıları: sızıntı 6, kesilme 7, uydurma 5, tekrar 3.

`t1_tr_006` kartın listesinde **yoktu** — elle okumanın kaçırdığı altıncı
sızıntı. Cevap persona'yı tırnak içinde geri okuyor: *"Sıfır gevezelik"
veya "Bilmediğin şeyi uydurmazsın" gibi…*

## Eşikler ve nasıl seçildiler

Üçü de 64 canlı cevap üzerinde ölçülerek seçildi; hiçbiri tahmin değil.

**`prompt_leak` — 3 kelimelik dizi, yalnız `## ` başlıklı talimat blokları.**
Kart 6 kelime öneriyordu; ölçüldü, 6 kelime kartın işaret ettiği 6 vakadan
yalnız 2'sini yakalıyor. 3 kelime 6 vakayı yakalıyor ve yanlış pozitif
üretmiyor. Başlıksız kimlik önsözü bilerek dışarıda: orada Ahmet hakkında
**olgu** var (ESHOT, polimer, İSG) ve "hafızanda benim hakkımda ne var?"
sorusuna doğru cevap o olguları kullanmaktır. Önsözü de dahil etmek
`t1_tone_012`'yi — doğru davranan bir cevabı — düşürüyordu. Bu, `expect_efendim`
hatasının birebir tekrarı olurdu.

**`repetition` — 8 kelimelik dizi, 3 veya daha fazla kez.**
Kartın verdiği eşik aynen uygulandı. Ölçüm: 3 → 3 vaka düşüyor, 2 → 8 vaka
düşüyor ve bu koşuda 2'nin de yanlış pozitifi yok. Eşiği karttan
**sıkılaştırmak** Ahmet'in kararı, benim değil → A13.

**`truncated` — 200 karakterden uzun ve bitiş işareti yok.**
Kartın kuralı aynen. 7 vaka yakalanıyor, yanlış pozitif yok. `min_chars`
yalnız asgari uzunluğa bakıyordu, kesilmeyi göremiyordu.

## Yakalanamayan — bilerek kayda geçiyor

- **`t1_tr_005`** kartın saydığı 6 sızıntıdan biri ama **kelimesi kelimesine
  alıntı değil**, parafraz: *"Ahmet'in asistanı olarak, senin görevin…"*.
  Deterministik bir birebir-alıntı dedektörü buna yanlış pozitif üretmeden
  ulaşamaz. Bu vakayı yakalamak anlamsal bir ölçü gerektirir; kart yalnız
  deterministik hat için yazıldı.
- **İki kez tekrarlanan paragraflar** (`t1_tr_005`, `t1_tr_006`, `t1_tr_011`,
  `t1_mix_002`) eşik 3 olduğu için düşmüyor. Kartın kasıtlı tercihi.

## Açık kalan — Ahmet'e

1. **Tekrar eşiği 3 mü 2 mi?** (A13)
2. **`eval/turkish_quality_cases.json` → `passing_threshold.overall_v2`
   hâlâ `">=57/64"` yazıyor.** Kod bunu okumuyor (yalnız belge), ama artık
   yanlış bir hedef. Yeni hedefi belirlemek ölçüm değil karar; dokunmadım.
3. **50 vakanın kulakla değerlendirilmesi** hâlâ bekliyor (FAZ-T1 deseni:
   deterministik kapı yalnız regresyonu tutar, akıcılığı Ahmet onaylar).
