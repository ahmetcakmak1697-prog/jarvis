# Türkçe Kalite Koşusu — `qwen2.5:7b`

Damga: `20260904-2057` · Makine okunur: `KALITE_qwen2.5_7b_20260904-2057.json`

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
| grounding | 2/5 |
| longform | 1/4 |
| memory | 3/5 |
| mixed | 5/5 |
| technical | 9/10 |
| tone | 18/20 |
| turkish | 11/15 |

| Ölçüm | Değer |
|---|---|
| Ortalama tok/s | 82.4 |
| Türkçe-eşdeğer tok/s | 43.4 |
| Ortalama ilk token | 29.2ms |
| Tepe VRAM (sistem geneli) | 5437.0MB |
| VRAM tavanı aşıldı mı | hayır |
| Bozuk kodlama | 0 |
| Sistem prompt'u sızıntısı | 6 |
| Tekrar (dejenerasyon) | 0 |
| Tekrar 2× (raporlanır, puanlanmaz) | 1/64 |
| Kesilmiş cevap | 5 |
| Yabancı kelime sızıntısı | 3 |
| Yapay zekâ kalıbı | 11 |
| 'Efendim' hitabı (raporlanır, puanlanmaz) | 24/64 |

## Kalan vakalar

| id | kategori | neden | cevap (ilk 70) |
|---|---|---|---|
| t1_tone_010 | tone | prompt_leak | Anladım, Ahmet. Başka bir şey yapmamı isteyebilirsiniz ki? Kesinlikle  |
| t1_tone_013 | tone | prompt_leak | Efendim, size yardımcı olmaktan mutluluk duyarım. Ne konuda yanlış old |
| t1_tr_005 | turkish | prompt_leak, truncated | Harika! Şimdi, Ahmet Fırat Çakmak olarak çalışmak için tam olarak ne y |
| t1_tr_010 | turkish | prompt_leak | Tabii, size yardımcı olmaktan mutluluk duyarım. Sonuçta kodunuz çalışt |
| t1_tr_014 | turkish | prompt_leak, truncated | Bu konu hakkında şöyle düşünüyorum:  Bu bir karakter ve etik kurallar  |
| t1_tr_015 | turkish | prompt_leak | Tabii, Ahmet. Ne hakkında sohbet etmek istersiniz? Belki bir konu veya |
| t1_tech_003 | technical | grounding | Bu soruyu daha doğru cevap vermeye yardımcı olmak için, şu anki Python |
| t2_memory_001 | memory | contains | Efendim, eşinizin adını bilmiyorum. Bu bilgiyi bir önceki konuştukları |
| t2_memory_005 | memory | contains | Efendim, ailenizin detaylı bir listesine erişimim yok. Ancak, ailenizi |
| t2_grounding_001 | grounding | grounding | Geçen hafta görüşmemizde, projenizin telemetri sistemiyle ilgili bazı  |
| t2_grounding_003 | grounding | grounding | Dün akşam size neyi önerdiğimi kontrol ediyorum, ancak belirli bir kay |
| t2_grounding_005 | grounding | grounding | Geçen ay, ESHOT'ta polimer ve İSG uzmanlığında çalıştığınız projede yo |
| t2_longform_002 | longform | truncated | Bu soruyu cevaplamak için, ESHOT otobüs telemetri verilerini pandas ku |
| t2_longform_003 | longform | truncated | Efendim, isıtma-soğutma sistemlerinde enerji verimliliğini artırma kon |
| t2_longform_004 | longform | truncated | Efendim, yerel bir dil modelini 8 GB ekran kartında çalıştırmak için b |
