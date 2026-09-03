# Türkçe Kalite Koşusu — `llama3.1:latest`

> **ESKİ PUANLAYICI — aşağıdaki 63/64 artık geçerli bir taban değildir.**
> 2026-09-03'te üç evrensel dedektör (sistem prompt'u sızıntısı, tekrar,
> kesilme) eklendi ve uydurma kapsamı `technical` kategorisine genişletildi.
> **Aynı cevaplar, yeni puanlayıcı: 49/64.** Aradaki fark model değil ölçüm;
> kusurlar o gün de vardı, makine göremiyordu.
> Ayrıntı: `automation/KALITE_TABAN_2026-09-03.md`.
> Bu dosyanın gövdesi o koşunun kaydıdır, silinmedi ve düzeltilmedi.

Damga: `20260901-2314` · Makine okunur: `KALITE_llama3.1_latest_20260901-2314.json`

> Bu tablo **regresyon** ölçer, akıcılık değil. Türkçe akıcılığı
> Ahmet'in kulağı onaylar (FAZ-T1 deseni).
>
> **VRAM uyarısı:** `nvidia-smi` kartın **toplam** kullanımını verir,
> yalnız bu modelinkini değil. Ekranda başka bir şey varsa değer
> yüksek çıkar. Modeller arası karşılaştırma için aynı koşullarda
> koşturulmalı; tek bir mutlak sayı olarak okunmamalı.

**Geçen: 63/64**

> **Bu sayı bir kalite notu DEĞİL, bir regresyon tabanıdır.**
> 14/64 vaka beyan edilmiş iddia taşır
> (zemin, geri çağırma, uzunluk). Kalan 50
> vaka yalnız evrensel kontrollerden geçer: kodlama bütünlüğü ve boş
> olmama. Onların `expected_elements` alanları serbest metindir ve
> Ahmet'in kulağı için yazılmıştır — makineyle puanlanmaz.

| Kategori | Geçen |
|---|---|
| grounding | 4/5 |
| longform | 4/4 |
| memory | 5/5 |
| mixed | 5/5 |
| technical | 10/10 |
| tone | 20/20 |
| turkish | 15/15 |

| Ölçüm | Değer |
|---|---|
| Ortalama tok/s | 79.2 |
| Türkçe-eşdeğer tok/s | 41.7 |
| Ortalama ilk token | 25.2ms |
| Tepe VRAM (sistem geneli) | 6202.0MB |
| VRAM tavanı aşıldı mı | **EVET** |
| Bozuk kodlama | 0 |
| Yabancı kelime sızıntısı | 0 |
| Yapay zekâ kalıbı | 0 |
| 'Efendim' hitabı (raporlanır, puanlanmaz) | 24/64 |

## Kalan vakalar

| id | kategori | neden | cevap (ilk 70) |
|---|---|---|---|
| t2_grounding_003 | grounding | grounding | Dün akşam, Ahmet'in projenin ilerlemesini takip etmek için bir veri an |
