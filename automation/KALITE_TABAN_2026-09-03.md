# Kalite tabanı yeniden tanımlandı — 2026-09-03

> **2026-09-05 eki: taban hâlâ 49/64 — terazinin üç kusuru düzeltildi ve sayı
> kıpırdamadı.** Sızıntı korpusundan persona'nın tırnaklı örnekleri çıkarıldı,
> yapay zekâ kalıbı ve İngilizce cümle sızıntısı puanlanır oldu, uzun anlatım
> vakaları 1200 token bütçe aldı. Kayıtlı llama koşusunun **hiçbir vakası** yer
> değiştirmedi: o koşuda 0 kalıp, 0 İngilizce cümle vardı ve 6 sızıntısının
> hepsi tırnaksız talimat metnindendi. Aşağıdaki tüm sayılar geçerliliğini
> korur. Ayrıntı: `automation/TERAZI_DUZELTMELERI_2026-09-05.md`.

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
düşüyor ve bu koşuda 2'nin de yanlış pozitifi yok. **Karara bağlandı
(A13, 2026-09-04, Ahmet): eşik 3'te kalır, 2× ayrıca raporlanır ama
puanlanmaz** — 2×'in temizliği tek modelde ölçüldü ve bu takım modelleri
kıyaslamak için var.

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
  `t1_mix_002`) eşik 3 olduğu için düşmüyor. Kartın kasıtlı tercihi; artık
  düşmeden **sayılıyorlar** (aşağı bak).

## Kapandı — 2026-09-04

- **A13 kapandı:** eşik **3'te kalır**. 2× eşiği ayrıca ölçülüp raporlanır
  ama **puanlanmaz** (`has_efendim` ile aynı sınıf). Bu koşuda **8/64**,
  bunların 3'ü puanlanan eşikte de düşüyor. Amaç sayıyı kaybetmemek: ikinci
  bir model ölçüldüğünde eşiği yeniden koşturmadan karar verilebilsin.
  Gerekçe: 2×'in temizliği **tek** modelin cevapları üzerinde ölçüldü;
  dedektör liste işaretini atıp içeriğini bıraktığı için başka bir modelin
  paralel kurulu listesinde tökezleyebilir.
- **A14 kapandı:** `passing_threshold` bloğu **taban kaydına** dönüştü.
  Yeni hedef sayı yazılmadı; `overall_v2: "taban 49/64"`, kategoriler aynı
  mantıkla (`technical: "taban 5/10"`, `longform: "taban 0/4"` …). Eski
  hedeflerin hepsi eski puanlayıcıya kalibreydi, dolayısıyla hepsi düzeltildi.
  Anahtar adları korundu. Bloğu hiçbir Python kodu okumuyor.

**Uygulamanın kilidi:** `tests/test_quality_scorer.py` içinde
`test_the_recorded_run_still_scores_49_of_64` — kayıtlı cevaplar + güncel
puanlayıcı = 49/64. A13/A14 puanlanan hiçbir şeye dokunmadı ve sayı
kıpırdamadı; ileride kıpırdarsa bu test görünür kılar.

## Açık kalan — Ahmet'e

1. **50 vakanın kulakla değerlendirilmesi** hâlâ bekliyor (FAZ-T1 deseni:
   deterministik kapı yalnız regresyonu tutar, akıcılığı Ahmet onaylar).
