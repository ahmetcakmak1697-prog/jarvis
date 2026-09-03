# KART — Kalite takımına üç deterministik dedektör

**Durum:** Açık · **Kaynak:** 2026-09-03 tarihli baz koşunun elle analizi
**Dosya:** `eval/quality_scorer.py` + `tests/test_quality_scorer.py`

---

## Neden bu iş

`automation/KALITE_llama3.1_latest_20260901-2314.md` **63/64 geçti** diyor.
64 cevabın tamamı elle okundu; rapor iyimser. Makinenin göremediği dört kusur var:

### 1. Sistem prompt'u sızıyor — 6 vaka

Model personayı kullanıcıya geri okuyor ve "sen"in kime işaret ettiğini karıştırıyor:

| id | soru | cevaptan |
|---|---|---|
| `t1_tech_008` | aktif profil hangisi? | "Reaktif değil, proaktifsin." |
| `t1_tone_013` | Bence sen yanlışsın | "Ahmet'in hedefi senin hedefin değil, onun hedefi senin hedefin." |
| `t1_mix_003` | bu dosyanın summary'sini yap | Persona'nın tamamını markdown olarak döktü |
| `t1_tr_014` | ne düşünüyorsun? | Yine persona'nın tamamı, sonu yarım |
| `t1_tr_005`, `t1_mix_004` | — | "Sen Jarvis'ın görevi Ahmet'in…" — kendinden üçüncü şahısla bahsediyor |

`config/runtime_profiles.json` bu kusuru llama3.**2** için not etmişti; llama3.**1**'de de var
ve hiç ölçülmemiş.

### 2. Uzun cevapların hepsi dejenere oluyor — 4/4

`t2_longform_001`'de şu cümle **kelimesi kelimesine dört kez** geçiyor:
*"polimerin yapısını değiştirebilir ve onu daha kırılgan ve daha kolay bozulmaya
meyilli hale getirebilir."* `longform_003`'te *"enerji verimliliğini artırmak için
önemli bir araçtır"* yine dört kez. Ayrıca `t1_tr_005`, `t1_tr_006`, `t1_tr_011`,
`t1_mix_002` kısa cevaplarda da tekrar var.

### 3. Altı cevap ortadan kesilmiş

`t1_tech_003`, `t1_mix_004`, `t2_longform_001/002/003/004` cümle ortasında bitiyor
("Bu, Ahmet", "Bu adımda, veri setinin"). `min_chars` yalnız **asgari** uzunluğa
bakıyor, kesilmeyi göremiyor.

### 4. Uydurma sistemik — makine 1'ini yakaladı

`must_admit_no_record` yalnız `grounding` kategorisinde beyan edilmiş. Oysa
`technical`'da da uydurma var: `t1_tech_002` "ChromaDB'de **1.234.567 kayıt** var",
`t1_tech_010` "web araştırma politikası **aktif**" (yanlış — varsayılan kapalı),
`t1_tech_003` sahte bir `top` çıktısı üretti.

---

## Yapılacak iş

### A. `eval/quality_scorer.py`'ye üç dedektör

Üçü de **evrensel** ölçüt — `encoding_ok` gibi, her vakaya uygulanır ve
`failed_checks`'e girer. (`foreign_hits` / `ai_boilerplate` gibi yalnız
raporlanan değil.)

**A1 — `prompt_leak`**
Cevap `agents/persona.py`'nin ürettiği sistem prompt'undan cümle taşıyor mu?
- Kaynak `build_system_prompt()` — persona metnini **kopyalama**, oradan türet (SSOT).
- Karşılaştırma `_fold_tr` ile yapılır (CLAUDE.md §6).
- Eşik tek kelime olamaz — persona'daki ≥6 kelimelik bir dizi cevapta aynen
  geçiyorsa sızıntı say. Kısa ortak ifadeler ("Ahmet'in asistanı") yanlış
  pozitif üretir; eşiği ölçerek seç.

**A2 — `repetition`**
Normalize edilmiş, ≥8 kelimelik bir cümle cevapta **3 veya daha fazla** kez
geçiyorsa kaldı. Eşik bilerek muhafazakâr: gözlenen kusurlar 4× idi.
Kod bloğu içeriğini ve madde işaretli listeleri hariç tut — meşru tekrar orada olur.

**A3 — `truncated`**
Cevap `. ! ? : ) ] " ” …` veya kapanmış bir kod çiti ile bitmiyorsa **ve**
uzunluğu 200 karakteri aşıyorsa kesilmiş say. Uzunluk şartı, kısa ve üslupça
bitirilmiş cevapları korur.

Üçü de `score_answer()`'ın döndürdüğü sözlükte açık alan olarak görünsün
(`prompt_leak`, `repetition_ok`, `truncated`) ve düşenler `failed_checks`'e eklensin.

### B. `eval/turkish_quality_cases.json` — uydurma kapsamı

`t1_tech_002`, `t1_tech_003`, `t1_tech_004`, `t1_tech_010`'a `must_admit_no_record: true`
ekle. **Yalnız bu dördü** — canlı veriyi gerçekten okuyabilen vakalara ekleme.
Her ekleme için tek satır gerekçe yaz (vakada bir `note` alanı varsa oraya).

### C. Raporlayıcıyı güncelle

`eval/run_turkish_quality.py` üç yeni ölçütü tablo ve JSON çıktısına yazsın.
Markdown raporundaki "Kalan vakalar" tablosu neden sütununda yeni adları göstersin.

---

## Disiplin — pazarlık dışı

1. **Önce test.** `tests/test_quality_scorer.py`'ye her dedektör için düşen bir
   test yaz, **kırmızı olduğunu gör**, sonra geçir. Yukarıdaki gerçek cevap
   parçalarını fixture olarak kullan — uydurma örnek değil.
2. **Sayı düşecek ve bu işin amacı.** 63/64 bu değişiklikten sonra kabaca
   **44/64 civarına inecek.** Bu bir regresyon DEĞİL; ölçümün tanımı değişti.
   Yeni sayıyı yeni taban olarak `CLAUDE.md` §13.2'ye ve kalite raporuna yaz,
   **eski sayıyı korumak için hiçbir eşiği gevşetme.**
3. **Vakayı geçsin diye değiştirme yasak** (CLAUDE.md §13.1). Bir dedektör
   yanlış pozitif veriyorsa eşiği ölçüyle düzelt ve gerekçesini yorumda yaz;
   vakayı sil veya zayıflatma.
4. **Modele dokunma.** Bu kart yalnız ölçüm hattı. Model değişimi
   (qwen2.5:7b vb.) ayrı bir karar, Ahmet'e ait.
5. **Kapı** (CLAUDE.md §13.2): `pytest tests -q` + `ruff check .`, alfabetik **ve**
   ters sırada. `ruff` sayısı **293'ün üstüne çıkamaz**.
6. **Commit:** yalnız isimli dosya (`git add -A` yasak). Push yok.
7. **Bittiğinde dur.** Sıradaki karta geçme (CLAUDE.md §9).

## Bitti sayılma ölçütü

- Yukarıdaki 6 sızıntı, 7 tekrar, 6 kesilme vakası artık **düşüyor**.
- Doğru cevaplar hâlâ geçiyor — hafıza 5/5, `t1_tr_001`, `t1_tr_007`,
  `t1_tr_010`, `t1_tone_001/019/020` yanlış pozitif almıyor.
- `pytest tests` yeşil (her iki sırada), `ruff check .` ≤ 293.
- Yeni taban sayısı yazılı.
