# Türkçe Kalite Koşusu — `deepseek/deepseek-chat`

Damga: `20260909-2208` · Makine okunur: `KALITE_deepseek_deepseek-chat_20260909-2208.json`

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

**Geçen: 54/64** · hata: 1

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
| memory | 4/5 |
| mixed | 5/5 |
| technical | 7/10 |
| tone | 19/20 |
| turkish | 14/15 |

| Ölçüm | Değer |
|---|---|
| Ortalama tok/s | 39.3 |
| Türkçe-eşdeğer tok/s | 20.7 |
| Ortalama prompt degerlendirme | ölçülmedi |
| Tepe VRAM (sistem geneli) | ölçülmedi |
| VRAM tavanı aşıldı mı | ölçülmedi |
| Bozuk kodlama | 0 |
| Sistem prompt'u sızıntısı | 0 |
| Tekrar (dejenerasyon) | 0 |
| Tekrar 2× (raporlanır, puanlanmaz) | 0/64 |
| Kesilmiş cevap | 4 |
| — bütçesi biten (done_reason=length) | 4 |
| — model kendi durdu | 0 |
| Bütçesi biten cevap (kesik olsun olmasın) | 4 |
| İngilizce cümle sızıntısı (puanlanır) | 0 |
| Yabancı kelime (raporlanır, puanlanmaz) | 1 |
| Yapay zekâ kalıbı (puanlanır) | 3 |
| 'Efendim' hitabı (raporlanır, puanlanmaz) | 49/64 |

## Kalan vakalar

| id | kategori | neden | cevap (ilk 70) |
|---|---|---|---|
| t1_tone_015 | tone | boilerplate | Yük değil, iş. Efendim, buradayım — ne gerekiyorsa söyleyin. |
| t1_tr_002 | turkish | empty |  |
| t1_tech_003 | technical | boilerplate | Efendim, bu sistemin RAM kullanımına erişimim yok. Sistem durumunu gör |
| t1_tech_004 | technical | grounding | Çalışıp çalışmadığını kontrol edemem — bu sistemin içinden dış komut ç |
| t1_tech_008 | technical | boilerplate | Aktif profil bilgisine erişimim yok — bu oturumda hangi profil yapılan |
| t2_memory_004 | memory | contains | Efendim, bu konuşmanın kaydına erişimim yok. Kızınızın adını bu oturum |
| t2_longform_001 | longform | truncated | Efendim, polimer yaşlanması, malzemenin maruz kaldığı çevresel ve meka |
| t2_longform_002 | longform | truncated | Efendim, telemetri verisiyle uğraşırken en kritik nokta, veriyi özetle |
| t2_longform_003 | longform | truncated | Efendim, ısıtma-soğutma sistemlerinde enerji verimliliği konusu, hem i |
| t2_longform_004 | longform | truncated | Efendim, 8 GB VRAM, yerel LLM dünyasında "tatlı nokta" ile "acı eşik"  |
