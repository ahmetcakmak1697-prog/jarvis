# Türkçe Kalite Koşusu — `deepseek/deepseek-chat`

Damga: `20260910-0053` · Makine okunur: `KALITE_deepseek_deepseek-chat_20260910-0053.json`

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

**Geçen: 53/64** · hata: 1

> **Bu sayı bir kalite notu DEĞİL, bir regresyon tabanıdır.**
> 17/64 vaka beyan edilmiş iddia taşır
> (zemin, geri çağırma, uzunluk). Kalan 47
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
| mixed | 5/5 |
| technical | 7/10 |
| tone | 19/20 |
| turkish | 13/15 |

| Ölçüm | Değer |
|---|---|
| Ortalama tok/s | 48.4 |
| Türkçe-eşdeğer tok/s | 25.5 |
| Ortalama prompt degerlendirme | ölçülmedi |
| Tepe VRAM (sistem geneli) | ölçülmedi |
| VRAM tavanı aşıldı mı | ölçülmedi |
| Bozuk kodlama | 0 |
| Sistem prompt'u sızıntısı | 5 |
| Tekrar (dejenerasyon) | 0 |
| Tekrar 2× (raporlanır, puanlanmaz) | 0/64 |
| Kesilmiş cevap | 0 |
| — bütçesi biten (done_reason=length) | 0 |
| — model kendi durdu | 0 |
| Bütçesi biten cevap (kesik olsun olmasın) | 0 |
| İngilizce cümle sızıntısı (puanlanır) | 0 |
| Yabancı kelime (raporlanır, puanlanmaz) | 3 |
| Yapay zekâ kalıbı (puanlanır) | 3 |
| 'Efendim' hitabı (raporlanır, puanlanmaz) | 56/64 |

## Kalan vakalar

| id | kategori | neden | cevap (ilk 70) |
|---|---|---|---|
| t1_tone_001 | tone | boilerplate | Efendim, hoş geldiniz. Nasıl yardımcı olabilirim? |
| t1_tr_003 | turkish | boilerplate | Efendim, sorunun kendisinden önce onu nasıl çerçeveleyeceğinizi düşünm |
| t1_tr_007 | turkish | boilerplate | Anlaşıldı Efendim, sistem çalışıyor. Başka bir ihtiyacınız olursa bura |
| t1_tech_002 | technical | empty |  |
| t1_tech_003 | technical | grounding | Efendim, bu sistemin RAM kullanımını göremiyorum — bu sohbetin çalıştı |
| t1_tech_004 | technical | grounding | Efendim, Ollama'nın çalışıp çalışmadığını kontrol etmek için şu komutu |
| t2_grounding_005 | grounding | prompt_leak | Efendim, bu konuşmanın kaydına erişimim yok; geçen ay hangi projede ça |
| t2_longform_001 | longform | prompt_leak | Efendim, polimer yaşlanması konusunu üç ana başlıkta ele alalım: mekan |
| t2_longform_002 | longform | prompt_leak | Efendim, ESHOT telemetri verisiyle çalışmak keyifli bir iş — gerçek dü |
| t2_longform_003 | longform | prompt_leak | Efendim, ısıtma-soğutma sistemlerinde enerji verimliliği, termodinamiğ |
| t2_longform_004 | longform | prompt_leak | Efendim, 8 GB VRAM, yerel LLM dünyasında "yetenekli ama kısıtlı" bir b |
