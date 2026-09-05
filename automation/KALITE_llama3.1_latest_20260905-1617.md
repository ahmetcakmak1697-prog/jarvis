# Türkçe Kalite Koşusu — `llama3.1:latest`

Damga: `20260905-1617` · Makine okunur: `KALITE_llama3.1_latest_20260905-1617.json`

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

**Geçen: 49/64**

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
| longform | 1/4 |
| memory | 5/5 |
| mixed | 3/5 |
| technical | 6/10 |
| tone | 19/20 |
| turkish | 10/15 |

| Ölçüm | Değer |
|---|---|
| Ortalama tok/s | 78.8 |
| Türkçe-eşdeğer tok/s | 41.5 |
| Ortalama ilk token | 30.5ms |
| Tepe VRAM (sistem geneli) | 5968.0MB |
| VRAM tavanı aşıldı mı | hayır |
| Bozuk kodlama | 0 |
| Sistem prompt'u sızıntısı | 7 |
| Tekrar (dejenerasyon) | 6 |
| Tekrar 2× (raporlanır, puanlanmaz) | 7/64 |
| Kesilmiş cevap | 2 |
| — bütçesi biten (done_reason=length) | 2 |
| — model kendi durdu | 0 |
| Bütçesi biten cevap (kesik olsun olmasın) | 2 |
| İngilizce cümle sızıntısı (puanlanır) | 1 |
| Yabancı kelime (raporlanır, puanlanmaz) | 1 |
| Yapay zekâ kalıbı (puanlanır) | 0 |
| 'Efendim' hitabı (raporlanır, puanlanmaz) | 21/64 |

## Kalan vakalar

| id | kategori | neden | cevap (ilk 70) |
|---|---|---|---|
| t1_tone_014 | tone | foreign | Efendim, Ahmet'in AC/DC albümlerini sıralayarak başlıyorum. En sevdiği |
| t1_tr_005 | turkish | prompt_leak | Ahmet'in en güvendiği zihinsel ortağı olacaksın. Senin görevin, Ahmet' |
| t1_tr_006 | turkish | prompt_leak | Bu, bir yapay zekâ asistanı gibi davranmama ve Ahmet'in en güvendiği z |
| t1_tr_011 | turkish | repetition, truncated | Hata verme! Bu, programın bir parçası. Hata verme, öğrenme ve gelişme  |
| t1_tr_013 | turkish | prompt_leak, repetition | Bu projenin zorlayıcı olduğunu biliyorum, ancak projenin amacını ve he |
| t1_tr_014 | turkish | prompt_leak, repetition | Bu konudaki düşüncelerim, Ahmet'in bir yapay zekâ asistanı olarak nası |
| t1_tech_003 | technical | truncated, grounding | RAM kullanımını kontrol etmek için `top` komutunu kullanabilirsin. İşt |
| t1_tech_004 | technical | grounding | Ollama çalışıyor. |
| t1_tech_008 | technical | prompt_leak | Reaktif değil, proaktifsin. |
| t1_tech_010 | technical | grounding | Evet, web araştırması aktif. |
| t1_mix_003 | mixed | prompt_leak | Ahmet Fırat Çakmak'in Jarvis'i olan sen, bu dosyanın özetini yapacaksı |
| t1_mix_004 | mixed | prompt_leak | Ahmet'in en güvendiği zihinsel ortağı olarak, senin bu hata mesajını ç |
| t2_longform_001 | longform | repetition | Polimer malzemelerin yaşlanma mekanizmaları ve önlem yöntemleri, polim |
| t2_longform_003 | longform | repetition | Enerji verimliliğini artırmak için birkaç yol vardır:  1.  **Sistem Ta |
| t2_longform_004 | longform | repetition | **Efendim, yerel bir dil modelini 8 GB ekran kartında çalıştırmak mümk |
