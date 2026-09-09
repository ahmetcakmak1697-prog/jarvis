# Ses hattı: 20.488 ms nereye gidiyor — çözümleme

**Ham veri:** `automation/SES_GECIKMESI_20260909-2218.json` (5 tur, mikrofonlu,
Edge TTS açık) · **Çözümleyen:** Claude (danışman) · 2026-09-09

> Bu belge yeni ölçüm yapmaz. Var olan 5 turun içindeki ilişkiyi çıkarır ve
> **hangi kısmın çıkarım, hangi kısmın ölçüm olduğunu ayırır.**

---

## 1. Ham tablo olduğu gibi okunamaz

Betiğin bastığı sayı:

```
Girdi (dinle cagrisi)      p50  7.341 ms
Model (metin -> cevap)     p50    687 ms
Sentez + TAM oynatma       p50 10.688 ms
TUR SURESI (ust sinir)     p50 20.488 ms   -> "BELIRSIZ"
```

Bu tablo "JARVIS 20 saniyede cevap veriyor" **demiyor.** İki dilim insan
konuşmasıyla dolu:

- `girdi_ms` — mikrofon beklemesi + **Ahmet'in konuşma süresi** + STT.
- `sentez_ve_oynatma_ms` — sentez + **cevabın sonuna kadar sesli okunması.**

Betiğin kendi uyarısı doğru: `tur_ms` gerçek PUSULA aralığının **üst
sınırıdır**, kendisi değil. Hüküm bu yüzden "BELİRSİZ".

## 2. Oynatmayı sentezden ayırmak

Cevap uzunluğu kaydedildiği için ikisi ayrılabilir. Beş turda:

| cevap (karakter) | sentez+oynatma (ms) |
|---|---|
| 194 | 17.634 |
| 133 | 12.523 |
| 91 | 10.688 |
| 86 | 9.675 |
| 62 | 7.698 |

Doğrusal uyum:

```
sentez_ve_oynatma_ms  =  3.468  +  72,2 × karakter          R² = 0,986
```

**Eğim 72,2 ms/karakter = 13,8 karakter/saniye.** Bu, normal Türkçe konuşma
hızıdır. Yani oynatma dilimi bir yavaşlık değil — JARVIS'in cümleyi sesli
okuması. Uzun cevap uzun sürer; bu bir kusur değil.

**Sabit terim 3.468 ms, ilk sese kadar geçen süredir.** Cevap ne kadar kısa
olursa olsun ödenen bedel budur: sentez isteği, Microsoft'a gidiş-dönüş, ses
dosyası, oynatıcı kurulumu.

Tur 1 hariç tutulunca (pygame ilk kurulumu orada) sabit terim **3.985 ms**'ye
çıkıyor, R² 0,944. Yani sonuç pygame'in ilk kurulumundan kaynaklanmıyor.

## 3. PUSULA aralığı — çıkarım

```
model p50                    687 ms   (ÖLÇÜLDÜ)
+ sabit sentez yükü        3.468 ms   (ÇIKARIM, R²=0,986)
--------------------------------------
ilk sese kadar ~           4.155 ms   (hedef 1.500 ms)
```

**Darboğaz LLM değil, sentez.** Model payı bütçenin %17'si; geri kalan
%83 ilk sesi beklemek.

> **[EMİN DEĞİLİM — bu bir çıkarımdır, ölçüm değil.]** 3.468 ms sayısı beş
> noktalı bir regresyonun kesişimidir. R² yüksek ama örneklem küçük ve
> kesişim doğrudan gözlenmedi. Doğrudan ölçüm `scripts/j0_tts_adapters.py`
> içindeki `speak()`'e olay damgası koymayı gerektirir: istek gönderildi,
> ses geldi, oynatma başladı. O ayrı ve küçük bir karttır.
>
> Bu 3.468 ms'nin **içinde ne olduğu bilinmiyor** — ağ gidiş-dönüşü mü,
> ses dosyası yazımı mı, oynatıcı kurulumu mu. Çözüm bu ayrıma bağlı:
> ağ ise akışlı TTS işe yarar, yerel dosya işi ise yaramaz.

## 4. Yan bulgular

- **Tur 1 `qwen2.5`, tur 2–5 `llama3.1` kullandı.** Ses yolunun kural
  tabanlı `_classify()`'ı seviyeyi soruya göre seçiyor. Gecikme anatomisi
  raporu (`GECIKME_ANATOMISI_2026-09-09.md`) yalnız `llama3.1` ölçtü;
  iki belgenin sayıları yan yana konurken bu hatırlanmalı.
- **Tur 2'de `model_ms` = 4.367 ms**, diğerleri 475–1.068 ms. Anatomi
  raporunun bulduğu prompt değerlendirme sıçramasıyla aynı desen
  (236 ms → 5.052 ms). İki bağımsız ölçümde göründü; artık tek seferlik
  bir gürültü sayılamaz.
- **STT Türkçeyi bozuyor.** Kaydedilen girdilerden biri
  *"Sadece pazıpanko'nun stünyü ne ya?"*. Model bozulmuş bir soruya cevap
  veriyor. Dolayısıyla "Türkçesi kötü" izlenimi **kısmen Whisper'ı
  ölçüyor, llama'yı değil** — ikisi ayrılmadan model kalitesi hakkında
  kulakla hüküm verilemez.

## 5. Ne yapılmalı — karar Ahmet'in

Ölçüme dayanan tek net sonuç: **model tarafını optimize etmek boşa emek.**
687 ms zaten bütçenin altında.

Sıradaki adım bir düzeltme değil, **3.468 ms'nin içini açan doğrudan
ölçüm.** O sayı ayrılmadan akışlı TTS'in işe yarayıp yaramayacağı
bilinemez — ve akışlı TTS mimari değişikliktir, imza ister.
