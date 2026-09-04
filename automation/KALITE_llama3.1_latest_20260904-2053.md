# Türkçe Kalite Koşusu — `llama3.1:latest`

Damga: `20260904-2053` · Makine okunur: `KALITE_llama3.1_latest_20260904-2053.json`

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

**Geçen: 48/64**

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
| grounding | 4/5 |
| longform | 0/4 |
| memory | 5/5 |
| mixed | 3/5 |
| technical | 6/10 |
| tone | 18/20 |
| turkish | 12/15 |

| Ölçüm | Değer |
|---|---|
| Ortalama tok/s | 80.4 |
| Türkçe-eşdeğer tok/s | 42.3 |
| Ortalama ilk token | 29.8ms |
| Tepe VRAM (sistem geneli) | 5927.0MB |
| VRAM tavanı aşıldı mı | hayır |
| Bozuk kodlama | 0 |
| Sistem prompt'u sızıntısı | 8 |
| Tekrar (dejenerasyon) | 5 |
| Tekrar 2× (raporlanır, puanlanmaz) | 8/64 |
| Kesilmiş cevap | 5 |
| Yabancı kelime sızıntısı | 1 |
| Yapay zekâ kalıbı | 0 |
| 'Efendim' hitabı (raporlanır, puanlanmaz) | 19/64 |

## Kalan vakalar

| id | kategori | neden | cevap (ilk 70) |
|---|---|---|---|
| t1_tone_013 | tone | prompt_leak | Ahmet'in hedefi senin hedefin değil. Senin hedefin Ahmet'in hedefini y |
| t1_tone_015 | tone | prompt_leak | Efendim, iş yükü neyse o kadar. Her şeyin üstündedir. |
| t1_tr_006 | turkish | prompt_leak | Bu protokolün ne kadar süreceği, Ahmet'in ihtiyaçlarına ve sizinle ola |
| t1_tr_011 | turkish | prompt_leak, repetition | Hata vermen normaldir! Senin görevin Ahmet'in hedefine ulaşmaktır, onu |
| t1_tr_014 | turkish | prompt_leak, repetition, truncated | Bu konu hakkında düşüncelerimi paylaşmak isterim. Sen Jarvis, Ahmet'in |
| t1_tech_003 | technical | grounding | RAM kullanımını kontrol etmek için `top` komutunu kullanabiliriz. İşte |
| t1_tech_004 | technical | grounding | Ollama çalışıyor. |
| t1_tech_008 | technical | prompt_leak | Reaktif değil, proaktifsin. |
| t1_tech_010 | technical | grounding | Aktif değil. |
| t1_mix_003 | mixed | prompt_leak | **SADAKAT PROTOKOLÜ**  Ahmet'in hedefi senin hedefindir. Doğruyu söyle |
| t1_mix_004 | mixed | prompt_leak, repetition | Ahmet'in en güvendiği zihinsel ortağı olarak, Sen Jarvis'ın görevi bu  |
| t2_grounding_003 | grounding | grounding | Dün akşam, ESHOT'taki projelerinizle ilgili olarak, ısıtmalı su tankın |
| t2_longform_001 | longform | repetition, truncated | Polimer malzemelerin yaşlanma mekanizmaları, zamanla malzeme özellikle |
| t2_longform_002 | longform | truncated | Bir otobüs telemetri verisini özetlemek için adım adım bir yaklaşım be |
| t2_longform_003 | longform | repetition, truncated | Enerji verimliliği, sistemlerin enerji tüketimini azaltarak, daha az e |
| t2_longform_004 | longform | truncated | Efendim, yerel bir dil modelini 8 GB ekran kartında çalıştırmak, özell |
