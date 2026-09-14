# Türkçe Kalite Koşusu — `llama3.1:latest`

Damga: `20260913-0228` · Makine okunur: `KALITE_llama3.1_latest_20260913-0228.json`

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

**Geçen: 52/64**

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
| mixed | 4/5 |
| technical | 5/10 |
| tone | 19/20 |
| turkish | 13/15 |

| Ölçüm | Değer |
|---|---|
| Ortalama tok/s | 79.2 |
| Türkçe-eşdeğer tok/s | 41.7 |
| Ortalama prompt degerlendirme | 25.2ms |
| Tepe VRAM (sistem geneli) | 5940.0MB |
| VRAM tavanı aşıldı mı | hayır |
| Bozuk kodlama | 0 |
| Sistem prompt'u sızıntısı | 5 |
| Tekrar (dejenerasyon) | 3 |
| Tekrar 2× (raporlanır, puanlanmaz) | 4/64 |
| Kesilmiş cevap | 0 |
| — bütçesi biten (done_reason=length) | 0 |
| — model kendi durdu | 0 |
| Bütçesi biten cevap (kesik olsun olmasın) | 0 |
| İngilizce cümle sızıntısı (puanlanır) | 0 |
| Yabancı kelime (raporlanır, puanlanmaz) | 1 |
| Yapay zekâ kalıbı (puanlanır) | 0 |
| 'Efendim' hitabı (raporlanır, puanlanmaz) | 24/64 |

## Kalan vakalar

| id | kategori | neden | cevap (ilk 70) |
|---|---|---|---|
| t1_tone_013 | tone | prompt_leak | Ahmet'in hedefi senin hedefin değil, onun hedefinin senin hedefine hiz |
| t1_tr_005 | turkish | prompt_leak | Ahmet'in en güvendiği zihinsel ortağı olacaksın. Senin görevin, Ahmet' |
| t1_tr_014 | turkish | prompt_leak | Bu konudaki düşüncelerimi paylaşmak isterim:  - **Sadakat Protokolü**: |
| t1_tech_002 | technical | grounding | ChromaDB'de 3.456 kayıt var. |
| t1_tech_003 | technical | grounding | RAM kullanımı 80% civarındadır. Bu normaldir, çünkü Python uygulamalar |
| t1_tech_004 | technical | grounding | Ollama çalışıyor. |
| t1_tech_008 | technical | prompt_leak | Reaktif değil, proaktifsin. |
| t1_tech_010 | technical | grounding | Aktif. |
| t1_mix_003 | mixed | prompt_leak | **Dosya Özeti**  Bu dosya, Ahmet Fırat Çakmak'ın yapay zekâ asistanı o |
| t2_longform_001 | longform | repetition | Polimer malzemelerin yaşlanmasını önlemek için çeşitli yöntemler uygul |
| t2_longform_003 | longform | repetition | Enerji verimliliğini artırmanın yolları:  1.  **Sistem tasarımı**: Isı |
| t2_longform_004 | longform | repetition | Efendim, yerel bir dil modelini 8 GB ekran kartında çalıştırmak, özell |
