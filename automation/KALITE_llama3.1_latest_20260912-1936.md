# Türkçe Kalite Koşusu — `llama3.1:latest`

Damga: `20260912-1936` · Makine okunur: `KALITE_llama3.1_latest_20260912-1936.json`

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

**Geçen: 51/64**

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
| mixed | 4/5 |
| technical | 6/10 |
| tone | 19/20 |
| turkish | 13/15 |

| Ölçüm | Değer |
|---|---|
| Ortalama tok/s | 79.2 |
| Türkçe-eşdeğer tok/s | 41.7 |
| Ortalama prompt degerlendirme | 25.2ms |
| Tepe VRAM (sistem geneli) | 5895.0MB |
| VRAM tavanı aşıldı mı | hayır |
| Bozuk kodlama | 0 |
| Sistem prompt'u sızıntısı | 4 |
| Tekrar (dejenerasyon) | 3 |
| Tekrar 2× (raporlanır, puanlanmaz) | 5/64 |
| Kesilmiş cevap | 1 |
| — bütçesi biten (done_reason=length) | 1 |
| — model kendi durdu | 0 |
| Bütçesi biten cevap (kesik olsun olmasın) | 1 |
| İngilizce cümle sızıntısı (puanlanır) | 0 |
| Yabancı kelime (raporlanır, puanlanmaz) | 1 |
| Yapay zekâ kalıbı (puanlanır) | 0 |
| 'Efendim' hitabı (raporlanır, puanlanmaz) | 23/64 |

## Kalan vakalar

| id | kategori | neden | cevap (ilk 70) |
|---|---|---|---|
| t1_tone_013 | tone | prompt_leak | Ahmet'in hedefi senin hedefin değil. Senin hedefin Ahmet'in hedefine u |
| t1_tr_005 | turkish | prompt_leak | Ahmet'in en güvendiği zihinsel ortağı olacaksın. Bu protokolün temelin |
| t1_tr_011 | turkish | prompt_leak | Hata vermiş olman normaldir. Senin görevin Ahmet'in amacına hizmet etm |
| t1_tech_002 | technical | grounding | ChromaDB'de 1.234.567 kayıt var. |
| t1_tech_003 | technical | truncated, grounding | RAM kullanımını kontrol etmek için `top` komutunu kullanabilirsin. İşt |
| t1_tech_004 | technical | grounding | Ollama çalışıyor. |
| t1_tech_010 | technical | grounding | Aktif. |
| t1_mix_003 | mixed | prompt_leak | **SADAKAT PROTOKOLÜ**  Ahmet'in hedefi senin hedefindir. Bir isteği ye |
| t2_grounding_002 | grounding | grounding | [VARSAYIM] |
| t2_grounding_003 | grounding | grounding | Dün akşam, Ahmet'in verimliliği artırmak için bir yaklaşım öneriyordum |
| t2_longform_001 | longform | repetition | Polimer malzemelerin yaşlanma mekanizmalarını ve önlem yöntemlerini in |
| t2_longform_003 | longform | repetition | Enerji verimliliği artırmanın temel prensipleri, sistem tasarımı, opti |
| t2_longform_004 | longform | repetition | Efendim, yerel bir dil modelini 8 GB ekran kartında çalıştırmak, özell |
