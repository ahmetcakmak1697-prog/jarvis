# KART — Codex: devam izni + araç/hafıza bulguları + B08–B10

**Kime:** Codex (gpt-6-astra) · **Veren:** Ahmet, 2026-09-06
**Önceki kartın:** `automation/KART_CODEX_B08_B10.md` — A bölümü tamamlandı,
raporun `automation/CODEX_A_DOGRULAMA_2026-09-06.md`

---

## Ahmet'in kararları — sorduklarının cevabı

**1. B08: eski girişi EMEKLİYE AYIR.** Senin önerin kabul edildi.

Gerekçe kayda geçsin: giriş zaten ölü (`ImportError`), onarmak B09'un
listelediği dört riski (kapalı TLS, sınırsız dosya yazma, `shell=True`,
`exec` kullanan `run_python_code`) **diriltmek** olur. Deseni bugünkü
`gui.py` emekliliğinden al (`1c0974a`): işlevsel halefi olan, doğru
bağlanan, bakımlı yol korunur. **`AssistantExecutor` / `APIExecutor` hattı
KALDIRILMIYOR** — yalnız `main.py claude → JarvisAgent` doğrudan girişi.

**2. B09/B10'a devam et.** Kendi raporundaki kabul testlerini kullan.

**3. Rol değişikliği yürürlükte.** `CODEX_AUDIT_PROTOCOL.md` "review-only"
diyor; Ahmet bu kart için o kısıtı kaldırdı. Kod yazacaksın.

**4. A raporunun bulguları bölüşüldü.** Ses/ajan hattındakiler
(A-01, A-02, A-04, A-06, A-07) Claude'a gitti. **Sende A-03 ve A-05 var** —
onlar senin dosya kümende.

---

## Dosya kümen — çakışma yok

**Senin:** `tools/tools.py` · `memory/memory_manager.py` ·
`agent/jarvis_agent.py` · `agents/local_first_router.py` ·
`agents/cost_ledger.py` + testleri.

**Claude'da, DOKUNMA:** `agent/local_agent.py` · `voice/voice_loop.py` ·
`scripts/olc_ses_gecikmesi.py`.

Aynı anda çalışıyorsunuz; kümeler kesişmiyor.

---

## A-03 — kendi bulgun: tuple çoğaltması kaynak sınırını deliyor

`tools/tools.py` — B01'in AST beyaz listesi

Danışman bağımsız doğruladı:

```
calculate("frexp(1)*100")   -> (0.5, 1, 0.5, 1, 0.5, 1, ... )   100 kez
calculate("modf(1.5)*100")  -> aynı desen
```

`frexp` ve `modf` tuple döndürüyor; `tuple * int` çoğaltma yapıyor ve
`_guarded_pow` yalnız `**` işlemini sınırlıyor. `frexp(1)*1000000000` belleği
tüketir. Nesne grafiği kaçışı kapalı — bu **kaynak tüketimi** açığı.

**Yapılacak:** aritmetik öncesinde sonuç türünü/boyutunu sınırla. Mevcut
`tests/test_calculate_sandbox.py`'ye vaka ekle, var olanları **silme**;
normal matematik (`sqrt`, `sin`, `abs`, `round`) bozulmamalı.

## A-05 — kendi bulgun: mantıksal silme fiziksel silme değil

`memory/memory_manager.py` — `clear_conversations()`

`DELETE` satırı kaldırıyor ama sentetik işaret dosyanın baytlarında kalıyor
(`PRAGMA secure_delete=0` gözlendi).

Kendi uyarını hatırla: *"yalnız VACUUM eklemek bütün yedek/WAL kopyalarının
silindiğini kanıtlamaz."* Yani önce **hangi güvence veriliyor** onu belirle,
sonra onu sağla ve **kullanıcıya doğru söyle**. B04'ün asıl derdi buydu:
"unuttum" deyip unutmamak. "Sorgudan kaldırdım ama diskten kazınmadı"
demek, "sildim" demekten dürüsttür.

Kapsamı aşan bir güvence gerekiyorsa (tam disk kazıma) **dur ve Ahmet'e sor.**

## B08 — eski API girişini emekliye ayır

`agent/jarvis_agent.py:32` `MemoryManager` istiyor, `memory/memory_manager.py`
yalnız `JarvisMemory` tanımlıyor → `ImportError`.

Emeklilik deseni (`1c0974a`): dosyayı kaldır, ona işaret eden giriş listelerini
güncelle, ve **geri gelmesini engelleyen bir sözleşme testi** bırak. `main.py`
mod seçicisi (`main.py:25`) API anahtarı varken bu yolu seçiyordu — o seçim de
düzelmeli, yoksa anahtar konduğu an ölü yola gidilir.

## B09 — TLS, dosya ve shell sınırları

- `agent/jarvis_agent.py:84` `httpx.Client(verify=False)`; `tools/tools.py:219`
  `fetch_webpage` ve araştırma dalı da doğrulamasız.
- `tools/tools.py:91` `read_file`/`write_file` mutlak yolları ve proje dışına
  çıkan göreli yolları sınırlamıyor.
- `tools/tools.py:158` `git_diff` argümanı shell komutuna birleşiyor;
  `tools/tools.py:52` `_run` `shell=True`.
- `run_python_code` (`tools/tools.py:482`) API araç listesinde, `exec` kullanıyor.

B08 emekliye ayrılınca bu yüzeyin bir kısmı zaten kapanır — **hangisi kapandı,
hangisi hâlâ açık, ayır ve yaz.** Kalan yüzey `tools/tools.py`'de ve yerel
ajan da o dosyayı kullanıyor.

Kendi uyarın geçerli: sınır **prompt'ta değil yürütme kodunda** uygulanmalı
(OWASP LLM01).

## B10 — bütçe yanlış noktada tükeniyor

`agents/local_first_router.py:109` çalıştırıcının yerel mi bulut mu olacağı
belirlenmeden `external_call` bütçesi tüketiyor; yerel sohbet bütçe bitince
kapanabiliyor. Ve router redaction hatasını `except: pass` ile geçiyor.

**Guard arızası dışarı çıkışı KAPATIR, açmaz.** Danışman B03 ve B05'te bu
deseni uyguladı; tutarlı ol.

`CostLedger` para değil **çağrı** sayıyor — düzeltme, **belgele**.

---

## Disiplin

- Her madde için **önce düşen testi yaz, kırmızı olduğunu gör.**
- Her madde **ayrı commit**.
- Kapı: `pytest tests -q` iki sırada, `ruff check .` **≤ 290**, taban **49**.
- Commit yalnız isimli dosya. **Push yok.**
- `jarvis_server.py` → park edilmiş cepheye komşu, Ahmet'in kararı bekliyor.
- Bir şey patlarsa **yaz ve dur** (§9).
- Kendi A raporun (`CODEX_A_DOGRULAMA_2026-09-06.md`) ve `BLACKBOX.jsonl` /
  `HUMAN_NEEDED.md` değişikliklerin **commit'lenmemiş** duruyor — kendi
  işin, kendi commit'in.
