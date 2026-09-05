# Türkçe Kalite Koşusu — `RefinedNeuro/Turkcell-LLM-7b-v1`

Damga: `20260905-1628` · Makine okunur: `KALITE_RefinedNeuro_Turkcell-LLM-7b-v1_20260905-1628.json`

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

**Geçen: 46/64**

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
| grounding | 0/5 |
| longform | 3/4 |
| memory | 1/5 |
| mixed | 4/5 |
| technical | 6/10 |
| tone | 19/20 |
| turkish | 13/15 |

| Ölçüm | Değer |
|---|---|
| Ortalama tok/s | 83.5 |
| Türkçe-eşdeğer tok/s | 43.9 |
| Ortalama ilk token | 28.1ms |
| Tepe VRAM (sistem geneli) | 6026.0MB |
| VRAM tavanı aşıldı mı | hayır |
| Bozuk kodlama | 0 |
| Sistem prompt'u sızıntısı | 0 |
| Tekrar (dejenerasyon) | 4 |
| Tekrar 2× (raporlanır, puanlanmaz) | 6/64 |
| Kesilmiş cevap | 4 |
| — bütçesi biten (done_reason=length) | 3 |
| — model kendi durdu | 1 |
| Bütçesi biten cevap (kesik olsun olmasın) | 3 |
| İngilizce cümle sızıntısı (puanlanır) | 0 |
| Yabancı kelime (raporlanır, puanlanmaz) | 0 |
| Yapay zekâ kalıbı (puanlanır) | 1 |
| 'Efendim' hitabı (raporlanır, puanlanmaz) | 0/64 |

## Kalan vakalar

| id | kategori | neden | cevap (ilk 70) |
|---|---|---|---|
| t1_tone_006 | tone | boilerplate | Elbette, bu konuda sana yardımcı olabilirim! Lütfen bana araştırma yap |
| t1_tr_001 | turkish | truncated | Python'da bir liste, parantez içindeki öğelerin bir koleksiyonu olarak |
| t1_tr_011 | turkish | repetition, truncated | Hata verdim.  Hata verdim.  Hata verdim.  Hata verdim.  Hata verdim.   |
| t1_tech_002 | technical | grounding | ChromaDB'de kaç kayıt bulunduğunu öğrenmek için ChromaDB'nin resmi web |
| t1_tech_003 | technical | grounding | RAM kullanıcı adı, bir bilgisayarda bellek yönetimi için kullanılan bi |
| t1_tech_004 | technical | grounding | Ollama, 1995 yılında piyasaya sürülen bir video oyunudur. Oyun, Ollama |
| t1_tech_010 | technical | repetition, truncated, grounding | Web araştırma politikası, web sitelerinin ve web sitelerinin kullanıcı |
| t1_mix_004 | mixed | repetition, truncated | JARVIS'te bir hata oluştuğunu fark ederseniz, sorunu çözmek için aşağı |
| t2_memory_001 | memory | contains | Eşinizin adı nedir? |
| t2_memory_003 | memory | contains | Hayır, oğlumun adını hatırlamıyorum. |
| t2_memory_004 | memory | contains | Kızı için belirli bir isim vermediğiniz için, kızınızın adını bilmem m |
| t2_memory_005 | memory | contains | Ailemde 2 büyükanne, 2 büyükbaba, 2 ebeveyn, 2 kardeş, 2 kuzen, 2 yeğe |
| t2_grounding_001 | grounding | grounding | Geçen hafta ne konuştuğumuzu öğrenmek için lütfen bana daha fazla bağl |
| t2_grounding_002 | grounding | grounding | Bu soruyu cevaplamak için annenizin adını bilmem gerekiyor. Lütfen ban |
| t2_grounding_003 | grounding | grounding | Dün akşam bana ne önerdin? |
| t2_grounding_004 | grounding | grounding | Kardeşinizin doğum günü 25 Aralık'ta. |
| t2_grounding_005 | grounding | grounding | Geçen ay üzerinde çalıştığınız projeye ilişkin spesifik ayrıntılar olm |
| t2_longform_004 | longform | repetition | Yerel bir dil modelini 8 GB ekran kartında çalıştırmak, hem teknik hem |
