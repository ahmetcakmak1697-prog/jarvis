# JARVIS Öğrenilen Hatalar ve Mimari Tuzaklar

> Bu dosya bir hata *günlüğü* değil, bir **kural üreteci**dir.
> Amaç: aynı tuzağa iki kez düşmemek. Bir hata buraya yazılmadıysa
> çözülmüş sayılmaz (bkz. `CLAUDE.md` §13.4).

## Nasıl kayıt eklenir

- **Yalnız kritik olanı yaz.** Yazım hatası, tek satırlık typo, geçici
  ortam sorunu buraya girmez. Buraya giren: mimari yanlış varsayım,
  sessiz mantık hatası, tekrar edebilecek sınıf-düzeyi tuzak.
- **En yeni kayıt en üste** eklenir.
- Her kayıt üç parçadan oluşur ve üçü de zorunludur:
  **Tuzak** (ne oldu) → **Kök neden** (neden oldu) → **Kural** (bir daha
  düşmemek için ne yapılacak).
- **Kural satırı test edilebilir olmalı.** "Dikkatli ol" kural değildir;
  "X yazılmadan önce Y testi yazılır" kuraldır.
- Kayıt tarihlidir ve mümkünse kanıta (commit hash, test adı, BLACKBOX
  `sequence`) bağlanır.

## Kayıt şablonu

Yeni kayıtlar aşağıdaki şablonla, `## Kayıtlar` başlığının hemen altına
eklenir:

```markdown
### [YYYY-AA-GG] Kısa başlık — bir cümlelik özet

- **Alan:** (ör. bellek katmanı / J0 ses hattı / router / otomasyon kapısı)
- **Şiddet:** BLOCKER | CONCERN | NOTE
- **Tuzak:** Ne oldu? Gözlemlenen yanlış davranış, tek paragraf.
- **Kök neden:** Neden oldu? Yanlış olan varsayım/mekanizma.
  Semptom değil, sebep yazılır.
- **Kural:** Bir daha düşmemek için ne yapılacak? Emir kipinde, tek cümle,
  doğrulanabilir.
- **Kanıt:** commit hash / test adı / BLACKBOX sequence / dosya:satır
- **Regresyon testi:** Bu hatayı yeniden üretecek testin adı.
  (Yoksa `YOK — açık borç` yazılır, uydurulmaz.)
```

## Kayıtlar

### [2026-08-31] Persona parçalanması — üç rakip kimlik, biri bozuk kodlamalı

- **Alan:** karakter katmanı (`config.py`, `agents/ollama_executor.py`, `agent/local_agent.py`)
- **Şiddet:** BLOCKER (JARVIS'in kim olduğu, hangi kapıdan girildiğine bağlıydı)
- **Tuzak:** Repoda birbirinden habersiz **üç** persona tanımı vardı.
  `config.py`'deki ~70 satırlık zengin sürüm yalnız `agent/jarvis_agent.py`'ye
  ulaşıyordu; kaskad (`AssistantExecutor` → `OllamaExecutor`) ise kendi
  satır-içi, ASCII'ye indirgenmiş sözlüğünü kullanıyordu. Dahası o sözlükteki
  L1 prompt'unda Türkçe harfler soru işaretine dönüşmüştü — model kendi dil
  kuralını okunamaz bir cümleden öğreniyordu. Aynı bozulma
  `world/people.json`, `world/devices.json` ve `jarvis_server.py`'nin CSS
  yorumlarında da vardı.
- **Kök neden:** Persona bir *metin* olarak üç yere kopyalanmıştı ve hiçbir
  test onu kilitlemiyordu. Kopyalar zamanla ayrıştı; biri de bir PowerShell
  aktarımında bozuldu (CLAUDE.md §5). Kopya varsa kayma kaçınılmazdır.
- **Kural:** Persona metni **yalnız** `agents/persona.py` içinde tanımlanır;
  `config.py` ve `agents/ollama_executor.py` onu türetir. SSOT modülü **saf**
  olmalıdır — `agents/` katmanı `config.py`'yi import edemez, çünkü `config.py`
  import anında `load_dotenv()` çağırıp `HF_*_OFFLINE` yazar (§9: `.env`'e
  dokunulmaz). Yeni bir persona metni yazmadan önce `tests/test_persona_ssot.py`
  okunur.
- **Kanıt:** `tests/test_persona_ssot.py` — 28 test. Kırmızı faz 21 başarısız,
  yeşil faz 28/28. Tam süit 1351 → **1379 passed**; `ruff check .` 295'te sabit.
  Canlı doğrulama: yakalayıcı istemci ile L1/L2/L3'ün üçünün de
  `Efendim` + `SADAKAT` + gevezelik yasağı taşıdığı görüldü.
- **Regresyon testi:** `tests/test_persona_ssot.py::test_ollama_executor_has_no_inline_persona`
  (satır-içi persona geri doğarsa kırılır) ve
  `test_live_files_have_no_corrupted_turkish` (kodlama bozulması geri gelirse kırılır).

**Ölçümle çürüttüğüm iki varsayım** — ikisi de tasarım sırasında "besbelli"
görünüyordu:

1. *"Zengin personayı L1'e koymak kısa turları yavaşlatır."* **Yanlış.**
   Sıcak L1: SSOT persona (596 token) **2.15s**, minimal prompt (12 token)
   **2.14s**. Fark ölçüm gürültüsü içinde. İlk gözlenen 14s tamamen soğuk
   başlangıçtı (model VRAM'e yükleniyor). Kural: yerel modelde prompt uzunluğu
   maliyetini **varsayma, ölç** — asıl maliyet soğuk başlangıçtır.
2. *"Prompt düzelince karakter düzelir."* **Yetersiz.** Prompt doğru gidiyor
   ama `llama3.2:latest` (L1 rolü) ona uymuyor: 3 denemede `Efendim` **0 kez**
   geçti, cevaplardan biri "Merhaba! Ben Ahmet." diyerek kullanıcıyla kendini
   karıştırdı. Persona yine de ölçülebilir fayda sağlıyor — yapay zekâ kalıbı
   SSOT ile 0/3, minimal prompt ile 1/3. Kural: karakter = prompt **×** model
   kapasitesi. Türkçe persona uyumu için L1 rol modeli ayrıca değerlendirilmeli
   (aday: `qwen2.5:7b`); bu **açık madde**, karara bağlanmadı.

**Ek (aynı gün, L1 model geçişi sonrası):** Benchmark koşuldu ve `local_small`
`llama3.2:latest` → `qwen2.5:7b` oldu (5 L1 sorusu, sıcak: qwen 2.40s /
Efendim 3-5; llama 2.52s / Efendim 0-5 **ve cevaplarda sistem prompt'u
sızıntısı**). Geçiş `config/runtime_profiles.json`'daki "benchmark olmadan
varsayılan değiştirilmez" kuralına uyularak yapıldı.

Geçiş **yeni bir kusur açığa çıkardı ve kusur benim yazdığım metindeydi:**
persona'daki somut örnek cümle ("%23 daha verimli") zayıf modele halüsinasyon
malzemesi oldu — qwen "Nerede kaldık?" sorusuna o sayıyı kullanarak **olmamış
bir konuşma** anlattı. **Kural: bir prompt'a konan her somut sayı/olay, model
tarafından anı olarak geri sunulabilir; örnekler açıkça "yalnızca üslup
örneği, içeriği gerçek değil" diye etiketlenir.** Ayrıca `_ZEMIN` (gerçeklik)
bloğu eklendi ve her seviyede gönderiliyor.

Sonuç kısmi: "Nerede kaldık?" düzeldi (artık "erişimim yok" diyor), ama
"Geçen hafta ne konuşmuştuk?" hâlâ uyduruyor ve selamlamada yapay zekâ kalıbı
sürüyor. **Prompt mühendisliği 7B bir modeli tam kısıtlayamaz** — kalıcı çözüm
modele gerçek kayıt beslemektir (Eşik 3). Bu **açık madde**.

### [2026-08-31] `orchestrator` ad çakışması — kök neden kaldırıldı (izolasyon yaması artık savunma katmanı)

- **Alan:** test altyapısı / import mimarisi
- **Şiddet:** CONCERN (belirti daha önce izole edilmişti, kök neden duruyordu)
- **Tuzak:** Repoda iki `orchestrator` modülü var: `scripts/orchestrator.py`
  (park edilmiş autocoder orchestrator'ı) ve `agents/orchestrator.py`
  (`LLMOrchestrator`, model merdiveni). 2026-08-30'da belirti
  `tests/conftest.py` ile izole edilmişti ama çakışmanın kendisi duruyordu.
- **Kök neden:** `agents/` bir **paket** (`__init__.py` var) ve repo
  konvansiyonu paket-nitelikli import (`from agents.proactive_runtime import ...`).
  `tests/test_blackbox_log.py` bu konvansiyonu bozup `agents/` dizinini **düz
  dizin** olarak `sys.path[0]`'a sokuyordu. Ad çakışması modüllerden değil, bu
  tek satırdan doğuyordu: `agents/` düz dizin olunca `agents/orchestrator.py`
  bare `import orchestrator` ile erişilebilir hale geliyor ve
  `scripts/orchestrator.py`'nin önüne geçiyordu.
- **Kural:** `agents/` ve `tools/` paket olarak import edilir
  (`from agents.X import ...`); bu dizinler **hiçbir zaman** `sys.path`'e düz
  dizin olarak eklenmez. Bir modülün adı iki dizinde birden geçiyorsa çözüm
  yeniden adlandırmak değil, **paket-nitelikli import kullanmaktır** — böylece
  ne parked koda ne de çalışan mimariye dokunulur.
- **Kanıt:** `tests/test_blackbox_log.py:41-47` → `from agents.blackbox_log import`.
  `agents/orchestrator.py`'nin tek tüketicisi `jarvis_brain.py:45` ve zaten
  paket-nitelikli import kullanıyor. Doğrulama: `pytest tests/test_blackbox_log.py
  tests/test_orchestrator.py` → 133 passed, conftest koruması devre dışıyken de
  geçiyor. `ruff check .` 296 → 295 (bir E402 gitti).
- **Regresyon testi:** YOK — açık borç. `tests/conftest.py`'deki
  `pytest_collectstart` koruması artık *savunma katmanı* olarak duruyor:
  kök neden gitti ama biri yeniden `sys.path`'e düz dizin eklerse yakalar.

### [2026-08-31] FLAKY — `test_missing_sounddevice_early_return_has_t0_definition`

- **Alan:** J0 ses hattı, `tests/test_j0_spike_b_latency_probe.py:768`
- **Şiddet:** CONCERN — **açık, çözülmedi**
- **Tuzak:** Tam süit **ters sırada** çalıştırıldığında bu test 5 koşunun
  1'inde başarısız oldu; sonraki 4 ters-sıra koşusunda ve her alfabetik
  koşuda geçti. Tek başına 48/48 geçiyor.
- **Kök neden:** [EMİN DEĞİLİM] Kesin neden tespit edilemedi. Gözlem:
  test `sys.modules`'ten `sounddevice`'ı çıkarıp `_real_probe()` çağırıyor.
  `sounddevice` bu makinede **gerçekten kurulu** (0.5.5), dolayısıyla
  `_real_probe` ImportError yerine gerçek ses cihazı yoluna girebiliyor.
  Gerçek donanıma dokunan bir yol, zamanlama/cihaz meşguliyeti nedeniyle
  nondeterministik olur. Hata izi yakalanamadı çünkü sonraki koşularda
  tekrarlamadı.
- **Kural:** Gerçek donanıma dokunan yol test içinde **koşula bağlı**
  çalıştırılmaz. Bir testin gövdesi "kütüphane kuruluysa şunu yap, değilse
  atla" diye dallanıyorsa, o test iki farklı makinede iki farklı şeyi test
  ediyor demektir — donanım `tests/mocks/mock_hardware.py` ile taklit edilir.
  Bu düzeltme henüz **yapılmadı**.
- **Kanıt:** ters-sıra koşu 1/5 → `1 failed, 1350 passed`; koşu 2-5 →
  `1351 passed`. Alfabetik koşuların hepsi → `1351 passed`.
- **Regresyon testi:** YOK. Flake yeniden üretilemediği için kilitlenemedi.

### [2026-08-30] Test State Pollution & Isolation — süit sıra bağımlıydı, 49 "hata" sahteydi

- **Alan:** test altyapısı (`tests/conftest.py`), orchestrator + J0 ses hattı
- **Şiddet:** BLOCKER (yeşil hattı imkânsız kılıyordu)
- **Tuzak:** `pytest tests` 51 başarısızlık veriyordu; ama aynı dosyalar tek
  başına çalıştırıldığında geçiyordu (`test_orchestrator.py` tek başına 42/42
  geçer, tam süitte 42/42 çökerdi). Yani süit **sıra bağımlıydı** ve
  başarısızlıkların 49'u gerçek kusur değildi. Bu, en tehlikeli hata sınıfıdır:
  gerçek 2 hatayı 49 sahte hatanın içinde gizliyordu.
- **Kök neden:** İki ayrı `sys.modules` sızıntısı vardı.
  1. **Belirsiz modül adı.** Repoda ayn ada sahip iki modül var:
     `scripts/orchestrator.py` ve `agents/orchestrator.py`. `import orchestrator`
     hangisine bağlanacağını `sys.path` sırasından öğreniyor.
     `tests/test_blackbox_log.py:45` modül düzeyinde `agents/` dizinini
     `sys.path[0]`'a sokuyor; alfabetik olarak sonra **toplanan**
     `test_orchestrator.py` ve `test_contractpath_schema_alignment.py` ise
     *scripts* sürümünü bekliyor → `AttributeError: module 'orchestrator' has
     no attribute '_read_verdict'`. Kritik ayrıntı: hasar **toplama
     (collection)** anında oluşuyor, çünkü `import orchestrator` modül
     düzeyinde. Bu yüzden bir fixture çok geç kalır.
  2. **Opsiyonel ses kütüphanesi sızıntısı.**
     `scripts/j0_spike_b_latency_probe.py` çalışma anında `sounddevice` import
     ediyor ve modül `sys.modules`'te kalıyor. `test_j0_voice_adapters.py` /
     `test_j0_voice_loop.py` ise "voice adapter'ı import etmek ağır ses
     kütüphanelerini yüklememeli" diye *import güvenliği* iddia ediyor; kirli
     `sys.modules` yüzünden çöküyorlardı.
- **Kural:** Testler arası izolasyon **tek noktadan**, `tests/conftest.py`'de
  sağlanır; hiçbir test dosyası bunun için değiştirilmez.
  (a) Birden fazla enjekte edilebilir dizinde aynı ada sahip modüller
  *hesaplanarak* bulunur (sabit liste değil) ve her toplama adımında
  `sys.modules`'ten atılır; `scripts/` her zaman `agents/`'ın önünde tutulur.
  (b) Modül düzeyinde import'un bozduğu şey fixture ile değil,
  `pytest_collectstart` kancasıyla onarılır — **fixture toplama anına
  yetişmez.**
  (c) Ağır opsiyonel ses kütüphaneleri her testin hem kurulumunda hem
  sökümünde `sys.modules`'ten atılır; böylece koruma test sırasından bağımsız
  olur.
  (d) Yeşil hat iddiası **tam süit** üzerinde kanıtlanır; ek olarak süit
  **ters sırada** da çalıştırılır. "Tek başına geçiyordu" bir kanıt değildir.
- **Kanıt:** `pytest tests` → 1351 passed (öncesi: 51 failed / 1300 passed).
  Ters sıra (126 dosya) → 1351 passed. Minimal tekrar-üreticiler:
  `test_blackbox_log.py + test_orchestrator.py` → 133 passed;
  `test_j0_spike_b_latency_probe.py + test_j0_voice_adapters.py` → 127 passed.
- **Regresyon testi:** YOK — açık borç. Sızıntının kendisini yakalayan
  bir test yok; koruma kaldırılırsa bunu ancak tam süit fark eder.
  Bu boşluk bilinçli olarak kaydedilmiştir.

### [2026-08-30] Bayat sözleşme iddiası — `assert result is True` DeliveryResult'a karşı

- **Alan:** proaktif teslimat hattı (E1-S6B)
- **Şiddet:** CONCERN
- **Tuzak:** `tests/test_proactive_telegram_adapter.py` içindeki 2 test
  `run_proactive_delivery(...)` çağrısının `is True` / `is False` döndürmesini
  bekliyordu; fonksiyon `DeliveryResult` dönüyor.
- **Kök neden:** E1-S6B, dönüş tipini bilinçli olarak `bool` → `DeliveryResult`
  yükseltti (`tests/test_e1_6b_delivery_result.py` docstring'i: "returns a
  structured DeliveryResult **instead of a bare bool**"). İki iddia bu
  geçişte güncellenmeden kaldı. Testlerin geri kalanı (`calls` iddiaları)
  zaten geçiyordu — yani davranış doğruydu, **iddia bayattı**.
- **Kural:** Bir dönüş tipi genişletildiğinde, o fonksiyonu çağıran **tüm**
  testler aynı commit'te taranır. `is True` / `is False` kimlik
  karşılaştırmasıdır: zenginleştirilmiş bir dönüş tipiyle **hiçbir kaynak
  düzeltmesi** onu geçiremez — bu yüzden böyle bir başarısızlık her zaman
  "kaynak mı bayat, test mi bayat" sorusunu zorunlu kılar; sessizce kaynağı
  bool'a geri döndürmek yanlış cevaptır.
- **Kanıt:** `agents/proactive_runtime.py:18` (`-> DeliveryResult`),
  `tests/test_e1_6b_delivery_result.py:1-7`
- **Regresyon testi:** `tests/test_e1_6b_delivery_result.py::test_delivery_result_is_dataclass`
  (sözleşmeyi zaten kilitliyor)

---

## Kalıcı tuzak listesi (repo genelinde bilinen, tekrar eden sınıflar)

Bunlar tek bir olaya değil, bu repoda **tekrar tekrar** ortaya çıkan
hata sınıflarına karşılık gelir. Yeni kod yazarken önce buraya bakılır.

- **Türkçe `.lower()` tuzağı** — `"İ".lower()` combining-dot üretir,
  `"I".lower()` `'i'` verir (Türkçe'de `'ı'` olmalı). Düz `.lower()` ile
  keyword eşleştirme sessizce KAÇIRIR. Kural: eşleştirmede her iki tarafa
  da aynı ASCII-fold uygulanır (`_fold_tr`). Bkz. `CLAUDE.md` §6.
- **PowerShell paste'i Türkçe karakteri bozar** ve BOM ekler. Kural:
  patch `@' ... '@ | python` here-string ile verilir, içinde `"""`
  kullanılır, asla `'''`. Bkz. `CLAUDE.md` §5.
- **"Başarılı" demeden önce görmek** — patch sonrası `py_compile` +
  `git status`/`git diff` + import smoke çalıştırılmadan hiçbir iş
  tamamlandı sayılmaz. Bkz. `CLAUDE.md` §5.
- **Doküman ↔ durum dosyası kayması** — iki dosya aynı gerçeği farklı
  anlatabiliyor (ör. `HUMAN_NEEDED.md` "Pending" derken
  `roadmap_state.json` "DONE" diyor). Kural: bir gerçeğin tek bir
  doğruluk kaynağı olur; ikinci yer ona *referans verir*, kopyalamaz.
- **Kendi ürettiğini kendin doğrulama önyargısı** — "bunu ben yazdım,
  iyi olduğunu düşünüyorum". Kural: stratejik "sıradaki adım doğru mu"
  sorusu ayrıca sorulur; Codex diff-review'ı bunu kapatmaz.
  Bkz. `CLAUDE.md` DANIŞMAN MODU.
