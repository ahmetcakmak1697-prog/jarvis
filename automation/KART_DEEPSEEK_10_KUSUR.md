# KART — DeepSeek'in kalan 10 kusuru: 7'si bizim, 3'ü onun

**Kime:** Claude Code (VS Code) · **Veren:** Ahmet, 2026-09-09
**Dal:** `auto/opencode-deepseek` · **Taban:** `8593dcf`

---

## Ölçülen durum

`automation/KALITE_deepseek_deepseek-chat_20260909-2208.json` — DeepSeek
54/64, llama3.1 49/64. Kalan 10 kusurun dağılımı **ölçüldü**:

| id | kategori | bütçe | uzunluk | bitiş | neden |
|---|---|---|---|---|---|
| `t2_longform_001` | longform | 1200 | 2864 | `length` | truncated |
| `t2_longform_002` | longform | 1200 | 3042 | `length` | truncated |
| `t2_longform_003` | longform | 1200 | 2796 | `length` | truncated |
| `t2_longform_004` | longform | 1200 | 2599 | `length` | truncated |
| `t1_tone_015` | tone | 400 | 60 | stop | boilerplate |
| `t1_tech_003` | technical | 400 | 371 | stop | boilerplate |
| `t1_tech_008` | technical | 400 | 334 | stop | boilerplate |
| `t1_tech_004` | technical | 400 | 258 | stop | grounding |
| `t2_memory_004` | memory | 400 | 183 | stop | contains |
| `t1_tr_002` | turkish | 400 | 0 | — | empty (ağ) |

**Longform'un dördü de bütçeye çarpıyor**, modelin kendi durması değil.
2864 karakter / 1200 token ≈ **2,39 karakter/token** — Türkçe token
açısından pahalı ve 1200 tam duvara denk geliyor.

Kart iki parçaya bölündü çünkü **ikisi farklı sınıfta.**

---

## PARÇA A — Persona kalıbı (İMZASIZ, önce bunu yap)

Üç vaka `boilerplate` ile düşüyor: model "size nasıl yardımcı olabilirim"
sınıfı bir kalıp kuruyor. Dedektör değişmiyor, eşik değişmiyor, **taban
oynamıyor** — bu yüzden imza gerekmiyor.

`agents/persona.py` → `build_system_prompt()` tek kaynaktır (§10).
Önce ölç, sonra dokun:

1. Üç vakanın cevabını oku, **hangi kalıbın** tetiklendiğini yaz
   (`eval/quality_scorer.py` içindeki `_BOILERPLATE` listesi).
2. Persona'nın bu kalıbı hangi cümlesinin davet ettiğini bul. Prompt'a
   yasak eklemek ilk çözüm değil — **var olan bir cümle** kalıbı
   çağırıyor olabilir.
3. Değişikliği yap, **aynı 64 vakayı DeepSeek ile yeniden koştur.**

**Kabul ölçütü:** üç vakadan en az ikisi geçiyor VE `llama3.1` tabanı
**49/64 olarak kalıyor** (persona ortak; llama'yı bozmadığın kanıtlanmalı).
Taban düşerse değişiklik geri alınır — persona iki modele birden hizmet
ediyor.

**Uyarı:** persona'yı "DeepSeek'e göre" ayarlamak yerel modeli bozabilir.
Ölçmeden hiçbir cümleyi silme.

---

## PARÇA B — Longform bütçesi (İMZA VERİLDİ, dikkatli uygula)

**Ahmet 2026-09-09'da onayladı.** Bu bir ölçüm-tanımı değişikliğidir ve
normalde imza gerektirir (kartın kendi kuralı); imza verildi, ama
koşullu:

> **Bütçe değişirse `llama3.1` de AYNI tanımla yeniden koşturulmalıdır.**
> Yoksa 54 ile 49 farklı tanımlarda ölçülmüş olur ve karşılaştırma
> geçersizleşir. Raporun kendi başlığı bu hatayı zaten anlatıyor:
> *"Taban 2026-09-03'te değişti... ölçümün tanımı değişti, model
> değişmedi."* Aynı tuzağa ikinci kez düşmeyeceğiz.

Adımlar:

1. `eval/turkish_quality_cases.json` içinde longform vakalarının
   `num_predict` alanını yükselt. **Kaç olacağını ölçerek seç:** dört
   cevap 2599–3042 karakter ve hepsi kesildi; modelin kendi durduğu
   uzunluk bilinmiyor. Önce **tek bir vakayı** yüksek bütçeyle koş
   (`--limit` / `--category longform`), `done_reason == "stop"` olduğu
   noktayı gör, **sonra** sayıyı ona göre belirle. Tahminle yazma.
2. `passing_threshold` bloğundaki longform taban kaydını güncelle
   (A14: hedef yazılmaz, **ölçülmüş taban** yazılır).
3. **Üç koşu:** DeepSeek yeni bütçeyle, llama3.1 yeni bütçeyle, ve
   ikisinin eski sayısı rapora eski tanım olarak not düşülür.
4. `automation/KALITE_TABAN_*.md` ailesine yeni tabanı yaz; eski sayıyı
   silme, "hangi tanımla ölçüldüğü" ile birlikte bırak.

**Kabul ölçütü:** dört longform vakası artık `done_reason == "stop"`
ile bitiyor (kesilme yok); DeepSeek ve llama'nın **yeni tanımdaki**
sayıları yan yana yazılı; eski sayılarla karşılaştırmanın neden
yapılamayacağı bir cümleyle belgelenmiş.

**Bu parça tabanı oynatacak.** `CLAUDE.md` §13.2'deki "taban 49/64"
cümlesi de güncellenmeli — ölçüm tanımı değiştiği için.

---

## Kapsam dışı

- `t1_tech_004` (grounding) ve `t2_memory_004` (contains) — bunlar gerçek
  model kusurları olabilir. **Dokunma**, yalnız her biri için tek satır
  gözlem yaz. Prompt'la kovalamak kalite takımını modele göre eğmek olur.
- `t1_tr_002` — ağ kopması, K14/yeniden deneme kartında zaten kapandı;
  bir vakada hâlâ tuttu. Sayıya girer, düzeltilmez.
- Sağlayıcı eklemek, model değiştirmek, `config/` dosyaları: **hayır.**

## Sınırlar

- Kapı: `pytest tests -q` **iki sırada**, `ruff check .` **≤ 283**.
- PARÇA A bitince **DUR** ve sonucu bildir; B'ye kendiliğinden geçme (§9).
- Push yok.
