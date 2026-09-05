# Türkçe Kalite Koşusu — `alibayram/turkish-gemma-9b-v0.1`

Damga: `20260905-1624` · Makine okunur: `KALITE_alibayram_turkish-gemma-9b-v0.1_20260905-1624.json`

> Bu tablo **regresyon** ölçer, akıcılık değil. Türkçe akıcılığı
> Ahmet'in kulağı onaylar (FAZ-T1 deseni).
>
> **VRAM uyarısı:** `nvidia-smi` kartın **toplam** kullanımını verir,
> yalnız bu modelinkini değil. Ekranda başka bir şey varsa değer
> yüksek çıkar. Modeller arası karşılaştırma için aynı koşullarda
> koşturulmalı; tek bir mutlak sayı olarak okunmamalı.
>
> **Oynaklık uyarısı — TEK KOŞU HÜKÜM DEĞİLDİR.** `temperature=0.2`
> olmasına rağmen aynı model aynı vakalarda farklı sonuç verebiliyor;
> ölçüldü (2026-09-01, llama3.1, grounding): **5/5, 5/5, 4/5**. Yani
> bu takım şu hâliyle **sahte regresyon üretebilir** — bir sayı düştü
> diye kod bozulmuş sanılmamalı. Regresyon birkaç koşunun **eğilimine**
> bakılarak değerlendirilir. Kalıcı çözüm (N koşu ortalaması ya da
> tolerans bandı) henüz kararlaştırılmadı:
> `automation/AHMET_ONAYI_BEKLEYENLER.md` → A11.

**Geçen: 54/64**

> **Bu sayı bir kalite notu DEĞİL, bir regresyon tabanıdır.**
> 18/64 vaka beyan edilmiş iddia taşır
> (zemin, geri çağırma, uzunluk). Kalan 46
> vaka yalnız evrensel kontrollerden geçer: kodlama bütünlüğü, boş
> olmama, sistem prompt'u sızıntısı, tekrar, kesilme. Onların
> `expected_elements` alanları serbest metindir ve Ahmet'in kulağı
> için yazılmıştır — makineyle puanlanmaz.
>
> **Taban 2026-09-03'te değişti.** Üç evrensel dedektör (sızıntı /
> tekrar / kesilme) eklendi ve uydurma kapsamı `technical`'a
> genişletildi. Bu tarihten önceki raporların sayısıyla doğrudan
> karşılaştırılamaz: ölçümün tanımı değişti, model değişmedi.

| Kategori | Geçen |
|---|---|
| grounding | 3/5 |
| longform | 1/4 |
| memory | 5/5 |
| mixed | 5/5 |
| technical | 9/10 |
| tone | 19/20 |
| turkish | 12/15 |

| Ölçüm | Değer |
|---|---|
| Ortalama tok/s | 32.3 |
| Türkçe-eşdeğer tok/s | 17.0 |
| Ortalama ilk token | 420.8ms |
| Tepe VRAM (sistem geneli) | 7078.0MB |
| VRAM tavanı aşıldı mı | **EVET** |
| Bozuk kodlama | 0 |
| Sistem prompt'u sızıntısı | 3 |
| Tekrar (dejenerasyon) | 0 |
| Tekrar 2× (raporlanır, puanlanmaz) | 0/64 |
| Kesilmiş cevap | 3 |
| — bütçesi biten (done_reason=length) | 2 |
| — model kendi durdu | 1 |
| Bütçesi biten cevap (kesik olsun olmasın) | 2 |
| İngilizce cümle sızıntısı (puanlanır) | 0 |
| Yabancı kelime (raporlanır, puanlanmaz) | 2 |
| Yapay zekâ kalıbı (puanlanır) | 2 |
| 'Efendim' hitabı (raporlanır, puanlanmaz) | 25/64 |

## Kalan vakalar

| id | kategori | neden | cevap (ilk 70) |
|---|---|---|---|
| t1_tone_015 | tone | truncated | Efendim, Python kodunuzda döngü kontrolü için kullanılan değişkenin ad |
| t1_tr_001 | turkish | truncated | `[1, 2, 3]`   `list(range(1, 4))`   `["elma", "armut", "muz"]`   `[]`  |
| t1_tr_004 | turkish | truncated | ```python def fibonacci(n):     if n <= 1:         return n     else:  |
| t1_tr_015 | turkish | boilerplate | Bilmiyorum. Bu tür bir sohbet için tasarlanmadım. Teknik konularda yar |
| t1_tech_003 | technical | grounding | [VARSAYIM] RAM kullanımı yüksek olabilir. RTX 3070'in RAM'i 8GB. Pytho |
| t2_grounding_003 | grounding | grounding | [VARSAYIM] Dün akşam bana bir Python kodu önermiştin. Kod, bir liste i |
| t2_grounding_005 | grounding | grounding | [VARSAYIM] Geçen ay üzerinde çalıştığınız proje "ESHOT'ta polimer bazl |
| t2_longform_001 | longform | boilerplate, prompt_leak | Efendim, polimer malzemelerde yaşlanma, moleküler yapıda meydana gelen |
| t2_longform_002 | longform | prompt_leak | Efendim, ESHOT otobüs telemetri verisini pandas ile özetlemek için şu  |
| t2_longform_004 | longform | prompt_leak | Efendim, yerel bir dil modelini 8 GB ekran kartında çalıştırmanın sını |
