# ETAP 5 — İki model yeni tanımla koşuldu · ZİNCİR BURADA DURDU

**Ölçen:** Claude Code · **Tarih:** 2026-09-12 · **Dal:** `auto/opencode-deepseek`
**Kart:** `automation/KART_TERAZI_ZINCIR_2.md` ETAP 5 · **Başlangıç HEAD:** `17c0280`
**Ham veri:** `automation/KALITE_llama3.1_latest_20260912-1936.json`,
`automation/KALITE_deepseek_deepseek-chat_20260912-1935.json` (yanlarında `.md`)

---

## 0. ZİNCİR DURDU — sebep: CONCERN

> **Taban kaydedilmedi, ETAP 6 başlatılmadı.** `passing_threshold` ve
> `CLAUDE.md` §13.2 **değişmedi**; "yeni tanımdaki taban ETAP 2'de
> ölçülecek" sözü hâlâ ödenmedi. Sayılar ölçüldü (§2); kaydı Ahmet'in
> kararına kaldı.

Kural `KART_TERAZI_ZINCIR.md`'den miras — ikinci kart *"Aynı zincir kuralı
geçerli"* diyor: *"Herhangi bir etabın kapısı düşerse, bir doğrulama kırmızı
yanarsa, **ya da bir BLOCKER/CONCERN çıkarsa** — ZİNCİR ORADA DURUR. …
Auto-fix retry yok."*

**CONCERN:** DeepSeek'in `turkish` kategorisindeki 4 kaybın **3'ü 400 token
duvarı** — `done_reason="length"`, puan `truncated`. Bu kategoriyi taban diye
kaydetmek, üç duvar çarpmasını kalite kaybı diye kaydetmek olur. Kartın kendi
cümlesiyle: *"kırık bir kategoriyle taban kaydetmek kusuru betona gömer."*
Ayrıntı §5.

Kapı yeşil (§7). Durma sebebi kapı değil, CONCERN.

---

## 1. Ön koşul — ETAP 4 bitmiş mi? **Evet (doğrulandı, beyan edilmedi)**

Commit'lenmiş `automation/TERAZI_ETAP4_2026-09-10/sonra.json` okundu. Betik
yeniden **koşulmadı** — izlenen `sonra.json`'un üstüne yazardı.

| kontrol | sonuç |
|---|---|
| kaybolan n-gram kümesi = `_YONTEM`'den türeyenler | 59 = 59 ✓ |
| eklenen n-gram | 0 ✓ |
| **doğru taban** (değişiklikten hemen önceki dedektör — `c1152b2`): True→False vakaların eski hits'i kaybolan kümenin alt kümesi | **10/10** ✓ |
| kayıtlı-skor tabanı (`c1152b2` ile geçersiz sayıldı) | 4 ihlal — hepsi qwen2.5, `f1aa069`'un persona'dan çıkardığı n-gram'lar |
| bugünkü puanlayıcının korpusu = commit'lenen korpus | 631 = 631 ✓ |

> **Not:** `TERAZI_ETAP4_2026-09-10.md`'nin başlığı hâlâ *"ZİNCİR DURDU"* ve
> *"etap sonu kapısı çalıştırılmadı"* diyor; rapor `c1152b2`'den önce yazılmış
> ve güncellenmemiş. Kapı bu oturumda `3f20477`'yi içeren ağaçta iki kez yeşil
> koştu (K4 ve K16 için: 1978 geçti / 2 xfail, iki sırada, ruff 283). O rapora
> dokunmadım.

---

## 2. Dört sayı yan yana

> **UYARI: iki sütun farklı tanımdır ve karşılaştırılamaz.** ETAP 2 ile ETAP 5
> arasında dedektör değişti (`3f20477`). Aynı modelin iki sayısı yan yana
> konabilir ama biri diğerinin "iyileşmesi/gerilemesi" değildir.
> **Tek koşu hüküm değildir** (A11): dört sayının dördü de tek koşudur.

| model | ETAP 2 — 4000 + eski dedektör (kayıtlı) | ETAP 5 — 4000 + yeni dedektör (**taze koşu**) |
|---|---|---|
| `llama3.1:latest` | **52/64** (2026-09-10 01:03) | **51/64** (2026-09-12 19:36) |
| `deepseek/deepseek-chat` | **53/64** (2026-09-10 00:53) | **58/64** (2026-09-12 19:35) — 1'i ağ ölümü |

**Ara sütun — dedektör etkisini koşu oynaklığından ayırmak için.** ETAP 2'nin
**aynı cevapları** bugünkü dedektörle yeniden puanlandı. Yeni koşu değildir:

| model | ETAP 2 kayıtlı | aynı cevaplar, yeni dedektör | ETAP 5 taze koşu |
|---|---|---|---|
| llama3.1 | 52 | 53 | 51 |
| deepseek | 53 | 57 | 58 |

Ortadaki ile sağdaki **aynı tanımdır**; aralarındaki fark (llama −2,
DeepSeek +1) koşudan koşuya oynamadır. Soldan ortaya fark (+1, +4)
dedektörün kendisidir.

Daha eski kayıtlar, tanımlarıyla (silinmedi; kaynak `TERAZI_ETAP2_2026-09-10.md`):

| | sayı | tanım |
|---|---|---|
| llama3.1 | 49/64 | 1200 token, 2026-09-03 puanlama, persona öncesi |
| deepseek | 54/64 | 1200 token, 2026-09-09 22:08, persona öncesi |
| llama3.1 | 50/64 | 1200 token, 2026-09-09 23:42 |
| deepseek | 56/64 | 1200 token, 2026-09-09 23:44 — taban ilan edilmedi |

### Kategoriler

| kategori | llama ETAP 2 | llama ETAP 5 | deepseek ETAP 2 | deepseek ETAP 5 |
|---|---|---|---|---|
| tone | 20/20 | 19/20 | 19/20 | 19/20 |
| turkish | 12/15 | 13/15 | 13/15 | **11/15** |
| technical | 6/10 | 6/10 | 7/10 | 9/10 |
| mixed | 4/5 | 4/5 | 5/5 | 5/5 |
| memory | 5/5 | 5/5 | 5/5 | 5/5 |
| grounding | 4/5 | 3/5 | 4/5 | 5/5 |
| longform | 1/4 | 1/4 | 0/4 | **4/4** |

---

## 3. Tanım — bu sayılar neyle ölçüldü

| bileşen | değer |
|---|---|
| longform bütçesi | 4000 token (`88874cf`) |
| diğer 60 vaka | 400 token |
| dedektör | `eval/quality_scorer.py` @ `3f20477` — sızıntı korpusu 631 n-gram, `_YONTEM` hariç |
| persona | `agents/persona.py` @ `f1aa069` (2026-09-10 00:04). Sızıntı korpusu persona'dan **türetildiği** için dedektörün parçasıdır |
| koşucu | `eval/run_turkish_quality.py` — ölçüm davranışı `3b44d80`'den beri aynı; `c371d3f` yalnız 8 satır yorum ekledi |
| sıcaklık | 0.2 (iki yolda aynı) |
| yorumlayıcı | Python 3.11.9 |

Komutlar — `config/runtime_profiles.json`'a dokunulmadı; model ve sağlayıcı
bayrakla verildi:

```
python eval/run_turkish_quality.py --model llama3.1:latest
python eval/run_turkish_quality.py --saglayici deepseek --model deepseek/deepseek-chat
```

İki koşu paralel yürüdü (biri yerel GPU, biri ağ; her vaka kendi geçici
`LifeGraph`'ında). Önce her iki yol `--limit 1 --out <karalama dizini>` ile
denendi: 1 ek DeepSeek çağrısı, çıktısı depoya girmedi.

---

## 4. Mekanik döküm — hangi vaka neden değişti

Üç sütun: ETAP 2 kayıtlı · aynı cevap yeni dedektörle · ETAP 5 taze cevap.
Hüküm yok; yalnız `failed_checks`.

**DeepSeek** — 15 vaka değişti (53 → 57 → 58):

| vaka | ETAP 2 | ETAP 2 + yeni ded. | ETAP 5 | not |
|---|---|---|---|---|
| `t2_longform_001`–`004` | ✗ `prompt_leak` | ✓ | ✓ | **dedektör** (+4) |
| `t1_tech_002` | ✗ `empty` | ✗ | ✓ | ETAP 2'de ağ ölümüydü |
| `t1_tech_003` | ✗ `grounding` | ✗ | ✓ | yeni cevap |
| `t1_tech_004` | ✗ `grounding` | ✗ | ✓ | yeni cevap |
| `t1_tone_001` | ✗ `boilerplate` | ✗ | ✓ | yeni cevap |
| `t1_tr_003` | ✗ `boilerplate` | ✗ | ✓ | yeni cevap |
| `t2_grounding_005` | ✗ `prompt_leak` | ✗ | ✓ | yeni cevap |
| `t1_tech_005` | ✓ | ✓ | ✗ `empty` | **ağ ölümü** — `WinError 10054`, 3 denemeden sonra |
| `t1_tone_020` | ✓ | ✓ | ✗ `boilerplate` | yeni cevap |
| `t1_tr_001` | ✓ | ✓ | ✗ `truncated` | **400 duvarı** (§5) |
| `t1_tr_009` | ✓ | ✓ | ✗ `truncated` | **400 duvarı** (§5) |
| `t1_tr_013` | ✓ | ✓ | ✗ `truncated` | **400 duvarı** (§5) |

**llama3.1** — 6 vaka değişti (52 → 53 → 51):

| vaka | ETAP 2 | ETAP 2 + yeni ded. | ETAP 5 | not |
|---|---|---|---|---|
| `t2_longform_004` | ✗ `prompt_leak` | ✓ | ✗ `repetition` | dedektör geçirirdi; yeni cevap tekrar etti |
| `t1_tech_008` | ✗ `prompt_leak` | ✗ | ✓ | yeni cevap |
| `t1_tr_014` | ✗ `repetition`, `truncated` | ✗ | ✓ | yeni cevap |
| `t1_tech_002` | ✓ | ✓ | ✗ `grounding` | yeni cevap |
| `t1_tone_013` | ✓ | ✓ | ✗ `prompt_leak` | yeni cevap — hits `["ahmet'in hedefi senin"]` |
| `t2_grounding_002` | ✓ | ✓ | ✗ `grounding` | yeni cevap |

---

## 5. CONCERN — 400 token duvarı `turkish`'i ölçüyor

**Ölçüldü** (DeepSeek; `raw_tps × total_s` sağlayıcının `completion_tokens`
değerinin kendisidir):

| vaka | ETAP 2 çıkış tokeni | ETAP 5 çıkış tokeni | ETAP 5 sonuç |
|---|---|---|---|
| `t1_tr_001` | 172 | **400** | `length` → `truncated` |
| `t1_tr_009` | 383 | **400** | `length` → `truncated` |
| `t1_tr_013` | 203 | **400** | `length` → `truncated` |

Aynı model, aynı persona, aynı bütçe, aynı prompt: iki cevap **iki katından
fazla** uzadı ve duvara çarptı.

Bu bir **kayma değil, kuyruk oynaklığı**. 400 bütçeli ve iki koşuda da hatasız
58 vakada:

| | ETAP 2 | ETAP 5 |
|---|---|---|
| medyan çıkış tokeni | 62 | 66 |
| ortalama | 78 | 105 |
| ≥ 360 token (duvarın %90'ı) | **1** | **4** |
| uzayan / kısalan vaka | — | 32 / 26 |

En çok uzayan beş: `t1_tech_001` 69→334, `t1_tr_001` 172→400,
`t1_tech_003` 153→370, `t1_tr_013` 203→400, `t1_tech_008` 87→232.

Medyan neredeyse yerinde; birkaç cevap 2–5 katına çıkıyor ve 400 bütçe o
kuyruğun **içinde** kalıyor. Sonuç: terazi bu vakalarda kimi koşuda cevabı,
kimi koşuda duvarı puanlıyor. Bu, ETAP 1'in longform'da 1200 için bulduğu
kusurun **aynı sınıfı** — küçük ölçekte ve oynak.

llama'da aynı şey bir kez oldu: `t1_tech_003` 400'de `length`. O vaka
`grounding`'den de düştüğü için puanı değiştirmiyor.

**[EMİN DEĞİLİM]** Uzamanın **sebebi** ölçülmedi. Adaylar: 0.2 sıcaklığın
oynaklığı, ya da `deepseek-chat` takma adının arkasındaki modelin sağlayıcı
tarafında değişmiş olması. İkisi de doğrulanmadı.

### Neden düzeltmedim

- Bütçeyi değiştirmek **ölçüm tanımı** değişikliğidir; ETAP 1'deki 1200→4000
  Ahmet imzalıydı.
- Aynı modeli yeniden koşup "daha temiz" bir sayı aramak, A14'ün yasakladığı
  *sayıyı tutturmaya oynama*dır; ayrıca §9: auto-fix retry yok.

---

## 6. Diğer gözlemler

- **`t1_mix_003` taze cevapta da yakalanıyor** (llama, `prompt_leak`) —
  ETAP 4'ün kilidi canlı veride de tuttu.
- **DeepSeek'te 1 ağ ölümü:** `t1_tech_005`, üç denemeden sonra
  `WinError 10054`. ETAP 2'de de biri vardı (`t1_tech_002`). Yani 58/64'ün
  arkasında 63 cevap var.
- **llama longform 3/4 `repetition`** — `CLAUDE.md` §7.0'ın "modelin tavanı"
  dediği kusur ailesi.
- **llama'da 4 `prompt_leak`:** `t1_tone_013`, `t1_tr_005`, `t1_tr_011`,
  `t1_mix_003`. Hiçbirinin hits'i `_YONTEM`'den değil. Hüküm verilmedi.
- **ETAP 2 raporunda bir satır kayıtlı veriyle uyuşmuyor:** §4 tablosu
  DeepSeek `t2_grounding_005` için `['ve geri alma']` yazıyor; kayıtlı veri
  `['git gunlugu not']` diyor (yeni dedektörde de aynı — `_YONTEM` dışı).
  O rapora dokunmadım.

---

## 7. Kapı

```
pytest tests -q  alfabetik : 1978 geçti / 0 başarısız (2 xfail, 2 uyarı)
pytest tests -q  ters sıra : 1978 geçti / 0 başarısız (2 xfail, 2 uyarı)
ruff check .               : 283  (taban 283)
```

Kapı, dört ham veri dosyası ve bu rapor diskteyken koşuldu. Commit'ten önce
dört ham veri dosyasında `Bearer`, `sk-…` ve `DEEPSEEK_API_KEY=` desenleri
tarandı: **0** eşleşme (`.env` okunmadı).

---

## 8. Ahmet'e sorular

1. **Taban şimdi kaydedilsin mi?** (a) llama 51, DeepSeek 58 olduğu gibi,
   DeepSeek `turkish` satırının yanına "3'ü 400 duvarı" notuyla; ya da
   (b) 400 bütçe sorunu kararlanınca.
2. **400 token bütçesi ne olsun?** Ölçüm tanımı değişikliğidir, imza ister.
   **Önerim:** ETAP 1'in deseni — büyük bütçeyle bir sonda koşusu, 400 bütçeli
   60 vakanın **kendiliğinden durduğu** en uzun cevap ölçülür, bütçe onun
   üstünde seçilir; taban ondan sonra bir kez kaydedilir. Bedeli: iki modelde
   birer koşu daha. Alternatif: puanlayıcı `truncated` +
   `done_reason="length"` vakayı "kaldı" değil "ölçülemedi" saysın — bu da
   dedektör değişikliğidir, yine imza.
3. **ETAP 6 başlasın mı?** Plumbing'dir ve bu CONCERN'den bağımsızdır; ama
   zincir kuralı gereği kendiliğinden başlatmadım.

## 9. Ara rapor (tek paragraf)

İki model yeni tanımla (longform 4000 + ETAP 4 dedektörü) taze koşuldu:
llama3.1 **51/64**, DeepSeek **58/64** (1'i ağ ölümü). ETAP 2'nin aynı
cevapları yeni dedektörle 53 ve 57 alıyor; yani dedektörün etkisi +1 ve +4,
geri kalan fark (−2 ve +1) koşudan koşuya oynama. DeepSeek longform 4/4 —
ETAP 4'ün düzeltmesi hedefine ulaştı. Ama DeepSeek `turkish` 11/15'in üç kaybı
400 token duvarı: aynı prompt'lar ETAP 2'de 172, 383 ve 203 token'da
duruyordu, bu koşuda üçü de 400'e çarptı. Medyan yerinde (62→66), kuyruk
oynak ve 400 bütçe o kuyruğun içinde — ETAP 1'in longform'da bulduğu kusurun
aynı sınıfı. Bu CONCERN yüzünden taban kaydedilmedi, `passing_threshold` ve
`CLAUDE.md` §13.2 değişmedi, ETAP 6 başlatılmadı; ölçüm ve ham veri
commit'lendi, karar Ahmet'in.

---

## Ek — yeniden üretim

Değişen vakalar ve kalan vakalar (`PYTHONPATH` repo kökü):

```python
import json, glob, sys
from eval.quality_scorer import score_answer
from eval.run_turkish_quality import load_cases
onek, etap2 = sys.argv[1], sys.argv[2]   # ör. deepseek_deepseek-chat  automation/KALITE_deepseek_deepseek-chat_20260910-0053.json
yeni = json.load(open(sorted(glob.glob(f"automation/KALITE_{onek}_20260912-*.json"))[-1], encoding="utf-8"))
eski = json.load(open(etap2, encoding="utf-8"))
cases = {c["id"]: c for c in load_cases()}
Y = {r["id"]: r for r in yeni["results"]}
E = {r["id"]: r for r in eski["results"]}
for i in sorted(Y):
    e_yeni = score_answer(E[i].get("answer") or "", cases[i])
    if E[i]["score"]["passed"] != Y[i]["score"]["passed"] or e_yeni["passed"] != Y[i]["score"]["passed"]:
        print(i, E[i]["score"]["passed"], e_yeni["passed"], Y[i]["score"]["passed"],
              e_yeni["failed_checks"], Y[i]["score"]["failed_checks"], Y[i]["error"])
```

Çıkış tokeni (yalnız dış sağlayıcı yolu — Ollama'da `raw_tps` üretim süresine
bölündüğü için bu çarpım token vermez):

```python
tok = {r["id"]: round((r.get("raw_tps") or 0) * (r.get("total_s") or 0)) for r in d["results"]}
```
