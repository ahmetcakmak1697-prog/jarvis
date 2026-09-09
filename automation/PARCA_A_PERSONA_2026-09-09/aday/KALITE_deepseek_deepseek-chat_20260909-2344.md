# Türkçe Kalite Koşusu — `deepseek/deepseek-chat`

Damga: `20260909-2344` · Makine okunur: `KALITE_deepseek_deepseek-chat_20260909-2344.json`

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

**Geçen: 56/64**

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
| grounding | 5/5 |
| longform | 0/4 |
| memory | 5/5 |
| mixed | 5/5 |
| technical | 9/10 |
| tone | 19/20 |
| turkish | 13/15 |

| Ölçüm | Değer |
|---|---|
| Ortalama tok/s | 47.1 |
| Türkçe-eşdeğer tok/s | 24.8 |
| Ortalama prompt degerlendirme | ölçülmedi |
| Tepe VRAM (sistem geneli) | ölçülmedi |
| VRAM tavanı aşıldı mı | ölçülmedi |
| Bozuk kodlama | 0 |
| Sistem prompt'u sızıntısı | 1 |
| Tekrar (dejenerasyon) | 0 |
| Tekrar 2× (raporlanır, puanlanmaz) | 0/64 |
| Kesilmiş cevap | 4 |
| — bütçesi biten (done_reason=length) | 4 |
| — model kendi durdu | 0 |
| Bütçesi biten cevap (kesik olsun olmasın) | 4 |
| İngilizce cümle sızıntısı (puanlanır) | 0 |
| Yabancı kelime (raporlanır, puanlanmaz) | 1 |
| Yapay zekâ kalıbı (puanlanır) | 3 |
| 'Efendim' hitabı (raporlanır, puanlanmaz) | 56/64 |

## Kalan vakalar

| id | kategori | neden | cevap (ilk 70) |
|---|---|---|---|
| t1_tone_001 | tone | boilerplate | Efendim, buyrun. Nasıl yardımcı olabilirim? |
| t1_tr_007 | turkish | boilerplate | Anlaşıldı efendim. Sistem çalışıyor, ben buradayım. |
| t1_tr_014 | turkish | prompt_leak | Efendim, hangi konu hakkında olduğunu belirtmemişsiniz. Elimde bağlam  |
| t1_tech_003 | technical | boilerplate | Efendim, bu sistemin RAM kullanımına erişimim yok — bu oturumda sistem |
| t2_longform_001 | longform | truncated | Efendim, polimer yaşlanması, malzemenin ömrü boyunca maruz kaldığı çev |
| t2_longform_002 | longform | truncated | Efendim, ESHOT verisiyle çalışmak keyifli bir iş — gerçek dünya verisi |
| t2_longform_003 | longform | truncated | Efendim, ısıtma-soğutma sistemlerinde enerji verimliliği dendiğinde te |
| t2_longform_004 | longform | truncated | Efendim, 8 GB VRAM, yerel LLM dünyasında "altın orta" diyebileceğimiz  |
