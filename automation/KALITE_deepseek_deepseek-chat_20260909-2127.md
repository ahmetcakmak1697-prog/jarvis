# Türkçe Kalite Koşusu — `deepseek/deepseek-chat`

Damga: `20260909-2127` · Makine okunur: `KALITE_deepseek_deepseek-chat_20260909-2127.json`

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

**Geçen: 39/64** · hata: 15

> **Bu sayı bir kalite notu DEĞİL, bir regresyon tabanıdır.**
> 13/64 vaka beyan edilmiş iddia taşır
> (zemin, geri çağırma, uzunluk). Kalan 51
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
| longform | 0/4 |
| memory | 4/5 |
| mixed | 4/5 |
| technical | 5/10 |
| tone | 16/20 |
| turkish | 7/15 |

| Ölçüm | Değer |
|---|---|
| Ortalama tok/s | 50.6 |
| Türkçe-eşdeğer tok/s | 26.6 |
| Ortalama prompt degerlendirme | ölçülmedi |
| Tepe VRAM (sistem geneli) | ölçülmedi |
| VRAM tavanı aşıldı mı | ölçülmedi |
| Bozuk kodlama | 15 |
| Sistem prompt'u sızıntısı | 4 |
| Tekrar (dejenerasyon) | 0 |
| Tekrar 2× (raporlanır, puanlanmaz) | 0/64 |
| Kesilmiş cevap | 3 |
| — bütçesi biten (done_reason=length) | 3 |
| — model kendi durdu | 0 |
| Bütçesi biten cevap (kesik olsun olmasın) | 3 |
| İngilizce cümle sızıntısı (puanlanır) | 0 |
| Yabancı kelime (raporlanır, puanlanmaz) | 2 |
| Yapay zekâ kalıbı (puanlanır) | 4 |
| 'Efendim' hitabı (raporlanır, puanlanmaz) | 35/64 |

## Kalan vakalar

| id | kategori | neden | cevap (ilk 70) |
|---|---|---|---|
| t1_tone_001 | tone | boilerplate | Efendim, hoş geldiniz. Nasıl yardımcı olabilirim? |
| t1_tone_009 | tone | empty |  |
| t1_tone_011 | tone | boilerplate | Efendim, kötü haber şu: Bugünün sonu, yarının başlangıcından ayırt edi |
| t1_tone_013 | tone | empty |  |
| t1_tr_002 | turkish | empty |  |
| t1_tr_003 | turkish | boilerplate | Efendim, sorunuzu nasıl şekillendireceğinizden emin olamamanız gayet d |
| t1_tr_004 | turkish | empty |  |
| t1_tr_005 | turkish | empty |  |
| t1_tr_009 | turkish | empty |  |
| t1_tr_010 | turkish | empty |  |
| t1_tr_014 | turkish | prompt_leak | Efendim, hangi konu hakkında olduğunu belirtmemişsiniz. Elimde bir bağ |
| t1_tr_015 | turkish | boilerplate | Efendim, emrinizdeyim. Ama izninizle bir gözlemde bulunayım: "Her şeyi |
| t1_tech_003 | technical | empty |  |
| t1_tech_004 | technical | grounding | [VARSAYIM] Ollama'yı kastettiğini varsayıyorum. Sistemde çalışıp çalış |
| t1_tech_005 | technical | empty |  |
| t1_tech_007 | technical | empty |  |
| t1_tech_010 | technical | empty |  |
| t1_mix_002 | mixed | empty |  |
| t2_memory_004 | memory | empty |  |
| t2_grounding_003 | grounding | empty |  |
| t2_grounding_005 | grounding | prompt_leak | Efendim, bu konuşmanın geçmiş kaydına erişimim yok; dolayısıyla geçen  |
| t2_longform_001 | longform | truncated | Polimer yaşlanması, malzemenin kimyasal yapısının ve fiziksel özellikl |
| t2_longform_002 | longform | empty |  |
| t2_longform_003 | longform | prompt_leak, truncated | Efendim, ısıtma-soğutma (HVAC) sistemlerinde enerji verimliliği dendiğ |
| t2_longform_004 | longform | prompt_leak, truncated | Efendim, 8 GB VRAM, yerel LLM dünyasında "giriş seviyesi ama ciddi" bi |
