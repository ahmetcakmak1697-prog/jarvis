# JARVIS Envanteri — ne var, ne bağlı, ne değil

**Amaç:** Ahmet'in şikayetine cevap — *"ne entegre ne değil kimse bilmiyor,
her şey darmadağın."* Şikayet doğruydu. Bu belge **haritadır**, düzenleme
değil: hiçbir dosya taşınmadı, silinmedi, yeniden adlandırılmadı.

**Nasıl üretildi:** ölçülerek. Erişilebilirlik `import` grafiğinden
hesaplanır — her dosya için "hangi giriş noktasından kaç adımda" kaydedilir.
Göz kararı hiçbir satır yok.

```
python scripts/envanter_uret.py     # bu belgenin OTOMATİK bölümünü tazeler
```

Betik işaretçinin **altını** yeniden üretir, **üstünü** (bu bölümü) elimize
bırakır. Altı ay sonra tekrar koşturulabilir; harita eskimez. *(K16: otomatik
bölüm için doğru. Bu elle yazılmış bölüm ise yazıldığı gün eskimeye başladı —
aşağıdaki not.)*

> **K16 güncellemesi (2026-09-12).** Aşağıdaki §0–§4 **2026-09-06 13:33
> ölçümüdür** (`4824760`). Aynı akşam B03–B05 ses yoluna iki modül ekledi,
> 2026-09-11'de `23943c6` ses yolunu buluta bağladı; bir kısmı bu yüzden
> otomatik bölümle çelişiyordu. **Hiçbir cümle silinmedi:** tazelenen her
> yere *(K16: …)* notu eklendi, eski cümle yanında duruyor. K16 notu
> taşımayan her iddia, sayı ve `dosya:satır` referansı 2026-09-06
> tarihlidir ve yeniden doğrulanmadı.
>
> Güncellemenin tamamı **statik import ölçümüdür** (§4.4). Yeni sayılar
> otomatik bölümden ya da üreticinin kendi fonksiyonlarıyla, otomatik
> bölümle aynı kenar kümesinden hesaplandı — elle sayılmadı. §0'ın
> sayıları şu komutla yeniden üretilir (2026-09-12'de `27 49` ve 11
> dosyalık listeyi bastı):
>
> ```
> python -c "import sys; sys.path.insert(0,'scripts'); import envanter_uret as e; d=e.izlenen_py(); k,_=e.ast_kenarlari(d,e.modul_haritasi(d)); m=set(e.bfs(k,['main.py'])); t=set(e.bfs(k,['tools/telegram_agent.py'])); print(len(m)-1, len(t)-1, sorted(m&t))"
> ```

---

## 0. Tek cümlelik bulgu — JARVIS'in iki ayrı beyni var

`main.py` (**ses hattı**) 24 dosyaya ulaşıyor. *(K16: **27**, §B.)*
`tools/telegram_agent.py` (**Telegram hattı**) 49 dosyaya ulaşıyor. *(K16: değişmedi, §B.)*
**Ortak kümeleri 8 dosya** — ve o sekizin hepsi yaprak yardımcı: *(K16: **11** — aşağıdaki not.)*

`agents/persona.py` · `agents/model_registry.py` · `agents/data_classifier.py`
`agents/hardware_sentinel.py` · `agents/provider_profiles.py`
`tools/system_intelligence.py` + iki `__init__.py`

Yani **hiçbir karar katmanı paylaşılmıyor.** Router, cascade, maliyet defteri,
dış sağlayıcı hattı, bilgi kartları, aday hafıza kuyruğu — hepsi yalnızca
Telegram tarafında. Sesle konuştuğunuzda JARVIS bunların hiçbirini görmüyor;
`agent/local_agent.py` doğrudan Ollama'ya gidiyor. *(K16: bu paragrafın iki
iddiası artık doğru değil — aşağıdaki not.)*

Ahmet'in "her şey darmadağın" hissi buradan geliyor: dağınıklık dosya
düzeninde değil, **iki hattın birbirini tanımamasında.**

> Bu bir kusur tespitidir, bir onarım önerisi değil. Ne yapılacağı Faz 2'nin
> ve Ahmet'in konusu.

**K16 — §0'ın bugünkü ölçümü.** Ortak küme **11**: yukarıdaki sekize üç
dosya eklendi. Üçünü de `agent/local_agent.py` doğrudan import ediyor ve
üçü de `main.py`'den 2 adım. Üçü de sekizin sayıldığı 2026-09-06 13:33
ölçümünden **sonra** geldi:

| Dosya | Ses yoluna hangi commit'lerle girdi (`git log -S`) |
|---|---|
| `agents/web_research_policy.py` | B03 `a39dca6` (2026-09-06 19:33) → `local_agent.py` |
| `agents/redaction_guard.py` | B05 `c401d4e` (2026-09-06 19:38) → `voice_loop.py`; B04 `939376a` (2026-09-06 19:44) → `memory_manager.py`; `23943c6` (2026-09-11) → `local_agent.py` |
| `agents/cost_ledger.py` | `23943c6` (2026-09-11) → `local_agent.py` |

- **"Hiçbir karar katmanı paylaşılmıyor" artık doğru değil.** Yukarıdaki
  paragrafın kendi saydığı katmanlardan **maliyet defteri** (`cost_ledger`)
  iki hatta da var. Router (`local_first_router`), cascade
  (`model_cascade`), dış sağlayıcı hattı (`assistant_executor` →
  `executor_registry` → `api_executor`), bilgi kartları
  (`knowledge_card_*`) ve aday hafıza kuyruğu (`memory_candidate_*`) hâlâ
  `main.py`'den erişilemiyor.
- **"`local_agent.py` doğrudan Ollama'ya gidiyor" artık doğru değil.**
  `local_agent.py` `agent/cloud_llm.py`'yi import ediyor (`23943c6`):
  bulut yolu açıksa ve kapı engellemezse `cloud_llm`, değilse Ollama.
  Hangi dalın koştuğu **çalışma zamanında ölçülmedi** (ayrıntı: §1'in K16
  notu).
- **Ses yolunun bulut çağrısı Telegram'ın dış model hattından geçmiyor.**
  `cloud_llm.py`'nin import ettiği repo modülleri yalnız
  `agents/__init__.py` ve `agents/model_registry.py`. Yani statik olarak
  **iki ayrı dış model yolu** var: ses hattında `cloud_llm`, Telegram'da
  `api_executor` hattı.
- **"Hepsi yaprak yardımcı" tam değil:** 11 dosyanın 9'u yaprak;
  `data_classifier` → `provider_profiles` ve `hardware_sentinel` →
  `system_intelligence` import ediyor — ikisi de kümenin içinde. Küme
  dışında hiçbir repo modülüne kenar yok.

> **Bu statik bir import ölçümüdür.** `cost_ledger`'ın ses yolunda import
> edilmesi bütçe kapısının bağlı olduğunu **KANITLAMAZ** —
> `agents/api_budget_gate.py` hâlâ YALNIZ-TEST (hiçbir üretim modülü
> import etmiyor; §C).

---

## 1. Ses hattının kablolaması — "Hey JARVIS" dendiğinde ne oluyor

Her ok `dosya:satır` ile doğrulanabilir. *(K16: satır numaraları 2026-09-06'nındır, bir kısmı bayat — diyagramın altındaki nota bkz.)*

```
  mikrofon
     │
     ▼  main.py:147            user_input = voice_io.prompt(...)
  VoiceIO.prompt               voice/voice_loop.py:91
     │                         (mikrofon başarısızsa klavyeye düşer, :117)
     ▼  voice_loop.py:95       self._listener.listen()
  VoiceListener.listen         voice/stt.py:448
     │
     ├─▶ MicrophoneRecorder.record   voice/stt.py:222
     │      └─ callback+kuyruk ile yakalama   voice/stt.py:293
     │         (bloklayan read() ölü akış veriyordu — FAILURES.md)
     │
     └─▶ FasterWhisperTranscriber.__call__   voice/stt.py:402
            └─ model tembel yüklenir          voice/stt.py:371
     │
     ▼  main.py:192            zemin = life_graph.recall_context()
  LifeGraph                    memory/life_graph.py
     │  main.py:193-197        [BİLİNEN GERÇEKLER] bloğu prompt'a eklenir
     │
     ▼  main.py:202            agent.voice_mode = voice_io.enabled
     ▼  main.py:204            response = agent.chat(mesaj)
  LocalJarvisAgent.chat        agent/local_agent.py:440
     │
     ├─▶ araç tespiti           agent/local_agent.py:364  _detect_tool()
     ├─▶ persona                agent/local_agent.py:471  build_system_prompt()
     └─▶ model çağrısı          agent/local_agent.py:511 → :423 _ask_ollama()
            └─ ollama.chat()    agent/local_agent.py:425
     │
     ▼  main.py:208            voice_io.say(response)
  VoiceIO.say                  voice/voice_loop.py:125
     └─ EdgeTTSAdapter         scripts/j0_tts_adapters.py
        (voice/voice_loop.py:165-167 — `sys.path` ile bağlanıyor, §E)
     │
     ▼  main.py:213            remember_exchange(user_input, life_graph)
  hafızaya yazım               memory/entity_extractor.py → memory/life_graph.py
        └─ hassas olgular kalıcı yazılmaz, inceleme kuyruğuna düşer
```

**K16 — diyagramın bayat yerleri.**

- **Model çağrısı artık iki dallı.** `agent/local_agent.py` içinde `chat()`
  (L933), bulut yolu açıksa (`_bulut_acik()`, L833; dal L1009) önce
  `_bulut_kapisi()`'ndan (L846) geçiyor, engel yoksa `_ask_cloud()` (L895)
  → `agent/cloud_llm.py`. Bulut kapalıysa, kapı engellerse ya da bulut
  çağrısı hata verirse `_ask_ollama()`'ya (L916; dal L1024-1027) düşüyor.
  Bu satırlar 2026-09-12'de okundu; **hangi dalın koştuğu çalışma
  zamanında ölçülmedi** (§4.4).
- Diyagramdaki `agent/local_agent.py:440` (`chat`), `:423` (`_ask_ollama`)
  ve `:425` (`ollama.chat`) bayat — bugün L933, L916, L918. `:364`,
  `:471` ve `:511` yeniden doğrulanmadı [DOĞRULANMADI].
- **TTS bağı:** `voice/voice_loop.py`'nin `sys.path` satırı artık **L204**
  (otomatik bölüm §E); diyagramdaki `:165-167` bayat. Import satırı
  yeniden doğrulanmadı [DOĞRULANMADI].
- **`main.py:NNN` satır numaraları** yeniden doğrulanmadı [DOĞRULANMADI].
  `main.py` 2026-09-06'dan sonra bir kez değişti (B08, `61bdbf4`) ve kendi
  `sys.path` satırı L9'dan L8'e kaydı (§E); bu numaralar da kaymış olabilir.
- `voice/stt.py` ve `voice/voice_loop.py:91/95/117/125` referansları
  yeniden doğrulanmadı [DOĞRULANMADI].

**Bu hatta olmayanlar** (ve Telegram hattında olanlar): `local_first_router`,
`assistant_executor`, `model_cascade`, `cost_ledger`, `api_executor`,
`redaction_guard`, `provider_selector`, `executor_registry`, `web_research`,
`vector_memory`, `knowledge_card_*`, `tiered_memory`, `retrieval_priority`. *(K16: `cost_ledger` ve
`redaction_guard` artık bu hatta — ikisi de `main.py`'den 2 adım. Listenin
geri kalanı hâlâ `main.py`'den erişilemiyor.)*

---

## 2. Dış model hattının gerçek durumu

Kartın işaret ettiği beş modül **yazılmış, test edilmiş ve birbirine
bağlanmış** — ama tek bir kapıdan asılı duruyorlar. *(K16: `cost_ledger` için artık doğru değil — aşağıdaki K16 tablosu.)*

| Modül | Sınıf | Gerçek durum |
|---|---|---|
| `agents/local_first_router.py` | CANLI | `tools/telegram_agent.py` → 1 adım. Ses hattında **yok**. |
| `agents/assistant_executor.py` | CANLI | Yalnız `tools/telegram_agent.py` import ediyor. |
| `agents/cost_ledger.py` | CANLI | `telegram_agent`, `local_first_router`, `api_budget_gate` besliyor. |
| `agents/api_executor.py` | CANLI | 3 adım uzakta; `executor_registry` ve `api_executor_adapter` üzerinden. |
| `agents/provider_profiles.py` | CANLI | Tek modül ki **her iki hatta da** ulaşılıyor (ses hattına `data_classifier` üzerinden, 3 adım). |
| **`agents/api_budget_gate.py`** | **YALNIZ-TEST** | **Hiçbir üretim modülü import etmiyor.** Bütçe kapısı canlı hatta bağlı değil. |

**K16 — tablonun bugünkü ölçümü** (otomatik bölüm §C ve üreticinin aynı
kenar kümesi; "import eden" = test dışı dosyalar):

| Modül | Bugün |
|---|---|
| `agents/local_first_router.py` | Değişmedi: `tools/telegram_agent.py` → 1 adım, ses hattında yok. |
| `agents/assistant_executor.py` | Değişmedi: import eden yalnız `tools/telegram_agent.py`. |
| `agents/cost_ledger.py` | **Değişti:** import edenler `agent/local_agent.py`, `agents/api_budget_gate.py`, `tools/telegram_agent.py` — artık **ses hattında da** (`main.py`'den 2 adım; `23943c6`). `local_first_router` bu listede yok. |
| `agents/api_executor.py` | Değişmedi: `tools/telegram_agent.py` → 3 adım. Dosya hâlâ BOM taşıdığı için **kendi** import'ları ölçülemiyor (§I). |
| `agents/provider_profiles.py` | Hâlâ iki hatta (`main.py`'den 3 adım, `data_classifier` üzerinden) ama **artık tek değil** — `cost_ledger` da iki hatta. |
| `agents/api_budget_gate.py` | Değişmedi: **YALNIZ-TEST**, hiçbir üretim modülü import etmiyor. |

> **Statik ölçüm.** `cost_ledger`'ın ses yolunda import edilmesi bütçe
> kapısının bağlı olduğunu **KANITLAMAZ** — `agents/api_budget_gate.py`
> hâlâ YALNIZ-TEST.

**Çalışması için eksik olanlar** (ölçüldü — hiçbirinin *içeriği* okunmadı):

- `config/provider_profiles.json` — `agents/assistant_executor.py:144`
  bu dosyayı okuyor; diskte yalnız `.example` var. *(K16: değişmedi — L144
  bugün de okuyor; §F hâlâ YOK.)*
- `config/api_providers.json` — yalnız `.example` var; üretim kodunda okuyan
  bulunamadı, yalnız `tests/test_api_executor.py:327` örneği doğruluyor.
  *(K16: değişmedi — üretim kodunda okuyan hâlâ yok; §F hâlâ YOK.)*
- `.env` — **diskte yok.** `agents/api_executor.py:287` sağlayıcı anahtarını
  `os.environ`'dan okuyor (`GEMINI_API_KEY`, `DEEPSEEK_API_KEY`; satır 75, 84).
  Anahtar yoksa `api_executor.py:391` "Missing API key environment variable"
  döndürür — yani hat **kurulu ama yakıtsız**.
  *(Yalnız varlık kontrolü yapıldı; `.env` okunmadı, loglanmadı — §9.)*
  *(K16: `.env` artık diskte **var** (§F: EVET) — yine yalnız varlık
  kontrol edildi, içerik okunmadı. Bu yüzden "yakıtsız" hükmü bu belgeden
  artık ne doğrulanabilir ne çürütülebilir. `api_executor.py` satır
  numaraları yeniden doğrulanmadı [DOĞRULANMADI].)*

**Özet:** mimari raftaki bir prototip değil, **bağlanmış ama tek hatta
sınırlı ve yapılandırmasız** bir sistem. "Kuralım" demeden önce bakılacak
yer burası. *(K16: Telegram'ın dış model hattı için hâlâ geçerli —
`config/provider_profiles.json` yok. Ses hattının 2026-09-11'de açılan
bulut yolu bu hatta dahil değil, ayrı bir yol; §0'daki K16 notu.)*

### Yanındaki ikinci örnek: proaktif katman

Aynı desen bir kez daha. `agents/proactive_core.py` CANLI (Telegram, 1 adım),
ama üstüne kurulan katmanın tamamı **YALNIZ-TEST**:
`proactive_runner` · `proactive_policy` · `proactive_delivery` ·
`proactive_runtime` · `proactive_telegram_adapter`. *(K16: değişmedi —
`proactive_core`'u import edenler `jarvis_server.py` ve
`tools/telegram_agent.py`; beşi hâlâ YALNIZ-TEST.)*

Çekirdek bağlı, çalıştırıcı bağlı değil. *(Bunun bir kısmı bilinçli olabilir —
E1 hattı insan onayı bekliyordu. [EMİN DEĞİLİM])*

---

## 3. Çelişkiler — belge bir şey, kod başka şey diyor

`CLAUDE.md` §12 bu türden üç çelişkiyi zaten kaydetmiş. Aşağıdakiler
**yeni** ve ölçümle bulundu.

**Ç1 — `auto_runner.py` park edilmiş ama dosyanın kendisi bunu söylemiyor.**
`README.md:181` ve `BOOT_CHECK.md` §11 "PARK EDİLMİŞ (ÇALIŞTIRMA)" banner'ı
taşıyor (§12'de çözüldü diye kayıtlı). Ama `auto_runner.py`'nin kendi
docstring'i hâlâ *"Tek komut: `python auto_runner.py`"* diyor — dosyayı açan
biri park işareti değil, davet görüyor. Banner belgeye konmuş, **koda
konmamış**. *(K16: değişmedi — `auto_runner.py:3` hâlâ "Tek komut:" diyor.
`README.md:181` yeniden doğrulanmadı [DOĞRULANMADI].)*

**Ç2 — Bütçe kapısı belgede var, hatta yok.** `agents/api_budget_gate.py`
testleriyle birlikte duruyor ama hiçbir üretim modülü onu çağırmıyor. Dış
model çağrısı yapan hat (`assistant_executor` → `executor_registry` →
`api_executor`) bütçe kapısından geçmiyor.
*(K16: değişmedi — `api_budget_gate.py` hâlâ hiçbir üretim modülünden
import edilmiyor. Artık ikinci bir dış model yolu da var: ses hattının
`agent/cloud_llm.py` yolu (`23943c6`), ve `api_budget_gate` `main.py`'nin
erişim kümesinde de yok. `cost_ledger`'ın ses yolunda import edilmesi bir
bütçe kapısının bağlı olduğunu **KANITLAMAZ** — statik ölçüm.)*

**Ç3 — `config/*.json` yalnız `.example` olarak var.** İki yapılandırma
dosyası da gerçek hâliyle diskte yok; biri (`provider_profiles.json`) üretim
kodunda **okunuyor**. *(K16: değişmedi — §F'de ikisi de hâlâ YOK.)*

**Ç4 — Öneri belgeleri, tamamlanmış iş gibi okunabiliyor.**
`docs/OSS_HARVEST_REPORT_2026-08.md` altı modül adı veriyor
(`core/log_safety.py`, `llm/tiers.py`, `memory/recall_gate.py`, `listener.py`,
`research_handler.py`, `hwfit/fit.py`); hiçbiri repoda yok.
`automation/FAZ4_ADIM_ONERISI.md` benzer şekilde beş test dosyası ve iki
modül anıyor. Bunlar büyük olasılıkla **öneri**, iddia değil — ama belgeler
bunu başlıkta söylemiyor. Tam liste §G'de. *[EMİN DEĞİLİM: niyetin öneri
olduğunu belgelerin tonundan çıkardım, açık bir "önerilen" etiketi yok.]*
*(K16: sayılar yeniden sayılmadı [DOĞRULANMADI] — §G'nin kendisi K15
kusurunu taşıyor: kendi çıktısını tarıyor ve `.venv`'i "var" sayıyor.
K15'ten sonra tazelenmeli.)*

**Ç5 — 24 modül yalnız kendi testinden erişilebiliyor.** Bunların bir kısmı
gerçekten hazırda beklemek üzere yazılmış olabilir; ama bir modülün tek
kullanıcısının kendi testi olması, "entegre" ile "yazılmış" arasındaki farkın
tam olarak ölçüsüdür. Liste §C'de, `agents/` tablosunda. *(K16: sayı değişmedi —
test dışı YALNIZ-TEST 24, §A.)*

---

## 4. Ne ölçülemedi — sessizce CANLI sayılmadı

Bu bölüm haritanın kendi sınırıdır. **Yanlış bir harita, haritasızlıktan
kötüdür**; ölçemediğimi ölçmüş gibi göstermedim.

1. **`sys.path` ile bağlanan modüller.** `voice/voice_loop.py:165`
   `scripts/` dizinini `sys.path`'e ekliyor, `:167` oradan
   `EdgeTTSAdapter`'ı import ediyor. Bu bağ **import grafiğinde görünmez**.
   Sonuç: `scripts/j0_tts_adapters.py` tabloda "giriş noktası (B: araç)"
   diye işaretli — CANLI olduğu doğru ama **gerekçesi eksik**: aslında
   ses hattının bir parçası. Aynı numara 12 dosyada daha var (§E).
   *(K16: `sys.path` satırı artık `voice/voice_loop.py:204` (§E); `:167`
   import satırı yeniden doğrulanmadı [DOĞRULANMADI]. "12 dosya" bugün
   **20** — üreticinin `dinamik_izler()`'iyle sayıldı. 2026-09-06'daki
   §E'de de 18'di; sayı yazıldığı gün de tutmuyordu.)*
2. **`tools/tools.py`'deki `exec`/`eval`.** İncelendi: `L482` ve `L509`
   `run_python_code` aracının kum havuzu; **modül yüklemiyor**. Yani
   `tools/` altındaki 8 yetim dosya dinamik olarak da çağrılmıyor —
   gerçekten erişilemez durumdalar.
   *(K16: `tools/tools.py` artık `exec`/`eval` içermiyor — B09 (`4778d72`)
   kaldırdı, §E'den düştü. `tools/` altındaki yetim sayısı §D'ye göre **9**;
   2026-09-06'daki §D'de de 9'du.)*
**B08 emeklilik notu (2026-09-07):** Eski `main.py claude` girisi ve
`agent/jarvis_agent.py` kaldirildi; AssistantExecutor/APIExecutor korunuyor.
Asagidaki eski httpx gozlemi tarihseldir.

3. **`agent/jarvis_agent.py:84` ve `agents/query_cache.py:188`**
   `__import__("httpx")` / `__import__("datetime")` kullanıyor; ikisi de
   dış kütüphane, repo modülü değil — haritayı etkilemiyor. *(K16:
   `agents/query_cache.py:188` değişmedi, §E.)*
4. **Çalışma zamanı davranışı ölçülmedi.** Bu harita statiktir: bir modülün
   import edilmesi, o kod yolunun *çalıştığını* kanıtlamaz. Bir `if` içinde
   hiç sağlanmayan koşulun arkasındaki import de CANLI görünür.
   (`FAILURES.md` → "YEŞİL ile ÖLÇÜLDÜ aynı şey değildir" deseninin
   buradaki karşılığı.)
5. **`.env` ve secret dosyaları okunmadı** (§9). Yalnız varlıkları
   kontrol edildi; hangi anahtarların *tanımlı olması gerektiği* koddan
   çıkarıldı, değerleri değil.

---


<!-- OTOMATIK-BOLUM: asagisi scripts/envanter_uret.py tarafindan uretilir -->

*Uretim: `python scripts/envanter_uret.py`. Bu bolum elle duzenlenmez; isaretcinin ustu elle yazilir.*

## A. Sayilar

Izlenen `.py`: **335** (test: 176, test disi: 159)

| Sinif | Adet |
|---|---|
| CANLI | 121 |
| YALNIZ-TEST | 200 |
| YETIM | 14 |

Test disi dosyalarin sinif dagilimi:

| Sinif | Adet |
|---|---|
| CANLI | 121 |
| YALNIZ-TEST | 24 |
| YETIM | 14 |

## B. Giris noktalari

**A — sistemi calistiranlar.** JARVIS'i baslatan kapilar.

| Dosya | Buradan erisilen dosya sayisi |
|---|---|
| `main.py` | 27 |
| `jarvis_desktop.py` | 19 |
| `jarvis_server.py` | 35 |
| `jarvis_brain.py` | 22 |
| `agent/local_agent.py` | 18 |
| `tools/telegram_agent.py` | 49 |

**PARK EDILMIS (CLAUDE.md §9 — CALISTIRMA).** Grafige neyi besledigi gorunsun diye dahil edildi.

| Dosya | Buradan erisilen dosya sayisi |
|---|---|
| `auto_runner.py` | 2 |

**B — arac kapilari** (33 dosya): olcum, kurulum, bakim. Bunlardan erisilen bir modul CANLI'dir ama ses hattinda olmayabilir; kanit sutunu hangisinden geldigini soyler.

## C. Her `.py` dosyasinin sinifi

`kanit` sutunu erisilebilirligin NASIL hesaplandigini soyler: hangi giris noktasindan kac adim.

### `(kok)` — 11 dosya

| Dosya | Sinif | Kanit | Not |
|---|---|---|---|
| `auto_runner.py` | CANLI | giris noktasi (PARK EDILMIS) |  |
| `config.py` | CANLI | main.py -> 1 adim |  |
| `indir.py` | CANLI | giris noktasi (B: arac) |  |
| `jarvis_brain.py` | CANLI | giris noktasi (A) |  |
| `jarvis_desktop.py` | CANLI | giris noktasi (A) |  |
| `jarvis_server.py` | CANLI | giris noktasi (A) |  |
| `jarvis_snapshot.py` | CANLI | giris noktasi (B: arac) |  |
| `main.py` | CANLI | giris noktasi (A) |  |
| `setup.py` | CANLI | giris noktasi (B: arac) |  |
| `setup_password.py` | CANLI | giris noktasi (B: arac) |  |
| `voice_test.py` | CANLI | giris noktasi (B: arac) |  |

### `agent` — 4 dosya

| Dosya | Sinif | Kanit | Not |
|---|---|---|---|
| `agent/__init__.py` | CANLI | main.py -> 1 adim |  |
| `agent/cloud_llm.py` | CANLI | agent/local_agent.py -> 1 adim |  |
| `agent/local_agent.py` | CANLI | giris noktasi (A) |  |
| `agent/local_agent_memory.py` | CANLI | agent/local_agent.py -> 1 adim |  |

### `agents` — 75 dosya

| Dosya | Sinif | Kanit | Not |
|---|---|---|---|
| `agents/__init__.py` | CANLI | main.py -> 1 adim |  |
| `agents/answer_crystallizer.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
| `agents/api_budget_gate.py` | YALNIZ-TEST | yalniz testlerden: tests/b10_execution_support.py -> 1 adim |  |
| `agents/api_executor.py` | CANLI | tools/telegram_agent.py -> 3 adim |  |
| `agents/api_executor_adapter.py` | CANLI | tools/telegram_agent.py -> 3 adim |  |
| `agents/assistant_executor.py` | CANLI | tools/telegram_agent.py -> 1 adim | `config/provider_profiles.json` bekliyor |
| `agents/audit_logger.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
| `agents/auto_updater.py` | CANLI | jarvis_server.py -> 1 adim |  |
| `agents/blackbox_log.py` | YALNIZ-TEST | yalniz testlerden: tests/test_blackbox_log.py -> 1 adim |  |
| `agents/cost_ledger.py` | CANLI | agent/local_agent.py -> 1 adim |  |
| `agents/daily_digest.py` | CANLI | jarvis_server.py -> 1 adim |  |
| `agents/data_classifier.py` | CANLI | agent/local_agent.py -> 1 adim |  |
| `agents/e1_s4_smoke_sender.py` | YALNIZ-TEST | yalniz testlerden: tests/test_e1_s4_live_smoke_wiring.py -> 1 adim |  |
| `agents/episodic_buffer.py` | YALNIZ-TEST | yalniz testlerden: tests/jarvis_system_audit.py -> 1 adim |  |
| `agents/execution_policy.py` | CANLI | tools/telegram_agent.py -> 2 adim |  |
| `agents/executor_registry.py` | CANLI | tools/telegram_agent.py -> 2 adim |  |
| `agents/hardware_sentinel.py` | CANLI | main.py -> 1 adim |  |
| `agents/internal_trace.py` | YALNIZ-TEST | yalniz testlerden: tests/test_c4_mini_internal_trace.py -> 1 adim |  |
| `agents/inventory_model.py` | YALNIZ-TEST | yalniz testlerden: tests/test_m0_2_inventory_model.py -> 1 adim |  |
| `agents/knowledge_card_editor.py` | YALNIZ-TEST | yalniz testlerden: tests/jarvis_system_audit.py -> 1 adim |  |
| `agents/knowledge_card_promoter.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
| `agents/knowledge_card_retriever.py` | CANLI | tools/telegram_agent.py -> 2 adim |  |
| `agents/knowledge_card_store.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
| `agents/local_first_router.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
| `agents/memory_candidate_queue.py` | CANLI | jarvis_brain.py -> 1 adim |  |
| `agents/memory_candidate_writer.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
| `agents/memory_maturity.py` | YALNIZ-TEST | yalniz testlerden: tests/test_c1_7_maturity.py -> 1 adim |  |
| `agents/memory_policy.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
| `agents/memory_provenance.py` | YALNIZ-TEST | yalniz testlerden: tests/test_c1_6g_provenance.py -> 1 adim |  |
| `agents/memory_retrieval_policy.py` | CANLI | jarvis_brain.py -> 1 adim |  |
| `agents/memory_schema.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
| `agents/memory_scorer.py` | CANLI | jarvis_brain.py -> 1 adim |  |
| `agents/memory_synthesis_promoter.py` | YALNIZ-TEST | yalniz testlerden: tests/test_c1_6e_synthesis_promoter.py -> 1 adim |  |
| `agents/memory_synthesizer.py` | YALNIZ-TEST | yalniz testlerden: tests/test_c1_6_memory_synthesizer.py -> 1 adim |  |
| `agents/model_cascade.py` | CANLI | tools/telegram_agent.py -> 2 adim |  |
| `agents/model_registry.py` | CANLI | jarvis_brain.py -> 1 adim |  |
| `agents/next_action_planner.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
| `agents/ollama_executor.py` | CANLI | tools/telegram_agent.py -> 2 adim |  |
| `agents/orchestrator.py` | CANLI | jarvis_brain.py -> 1 adim |  |
| `agents/organ_base.py` | YALNIZ-TEST | yalniz testlerden: tests/test_h1_5_organ_contract.py -> 1 adim |  |
| `agents/persona.py` | CANLI | agent/local_agent.py -> 1 adim |  |
| `agents/privacy_level_bridge.py` | CANLI | tools/telegram_agent.py -> 2 adim |  |
| `agents/proactive_agent.py` | CANLI | jarvis_server.py -> 1 adim |  |
| `agents/proactive_core.py` | CANLI | jarvis_server.py -> 1 adim |  |
| `agents/proactive_delivery.py` | YALNIZ-TEST | yalniz testlerden: tests/test_e1_6b_delivery_result.py -> 1 adim |  |
| `agents/proactive_policy.py` | YALNIZ-TEST | yalniz testlerden: tests/test_e1_6b_delivery_result.py -> 1 adim |  |
| `agents/proactive_runner.py` | YALNIZ-TEST | yalniz testlerden: tests/test_e1_6a_proactive_runner.py -> 1 adim |  |
| `agents/proactive_runtime.py` | YALNIZ-TEST | yalniz testlerden: tests/test_e1_6b_delivery_result.py -> 1 adim |  |
| `agents/proactive_telegram_adapter.py` | YALNIZ-TEST | yalniz testlerden: tests/test_proactive_telegram_adapter.py -> 1 adim |  |
| `agents/project_intelligence.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
| `agents/project_reporter.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
| `agents/project_state.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
| `agents/project_summarizer.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
| `agents/project_workspace.py` | YALNIZ-TEST | yalniz testlerden: tests/test_m0_4_project_workspace.py -> 1 adim |  |
| `agents/provider_decision.py` | CANLI | tools/telegram_agent.py -> 2 adim |  |
| `agents/provider_profiles.py` | CANLI | agent/local_agent.py -> 2 adim |  |
| `agents/provider_selector.py` | CANLI | tools/telegram_agent.py -> 2 adim |  |
| `agents/provider_smoke.py` | YALNIZ-TEST | yalniz testlerden: tests/test_provider_smoke.py -> 1 adim |  |
| `agents/query_cache.py` | YALNIZ-TEST | yalniz testlerden: tests/jarvis_system_audit.py -> 1 adim |  |
| `agents/redaction_guard.py` | CANLI | agent/local_agent.py -> 1 adim |  |
| `agents/reporting_state.py` | YALNIZ-TEST | yalniz testlerden: tests/test_c3_1_reporting_state.py -> 1 adim |  |
| `agents/retrieval_priority.py` | CANLI | tools/telegram_agent.py -> 2 adim |  |
| `agents/roadmap_detector.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
| `agents/self_improver.py` | CANLI | jarvis_server.py -> 1 adim |  |
| `agents/semantic_router.py` | CANLI | jarvis_brain.py -> 1 adim |  |
| `agents/session_closure.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
| `agents/skill_library.py` | CANLI | jarvis_server.py -> 1 adim |  |
| `agents/source_scorer.py` | CANLI | jarvis_brain.py -> 2 adim |  |
| `agents/structured_output_guard.py` | YALNIZ-TEST | yalniz testlerden: tests/test_c3_1_structured_output_guard.py -> 1 adim |  |
| `agents/task_executor.py` | CANLI | jarvis_server.py -> 1 adim |  |
| `agents/telemetry_event_store.py` | CANLI | tools/telegram_agent.py -> 2 adim |  |
| `agents/tiered_memory.py` | CANLI | tools/telegram_agent.py -> 2 adim |  |
| `agents/web_research_policy.py` | CANLI | jarvis_brain.py -> 1 adim |  |
| `agents/world_inventory_linker.py` | YALNIZ-TEST | yalniz testlerden: tests/test_m0_3_world_inventory_linker.py -> 1 adim |  |
| `agents/world_model.py` | YALNIZ-TEST | yalniz testlerden: tests/test_m0_world_model.py -> 1 adim |  |

### `automation` — 1 dosya

| Dosya | Sinif | Kanit | Not |
|---|---|---|---|
| `automation/TERAZI_ETAP4_2026-09-10/kapsam_olc.py` | YETIM | hicbir giristen ve testten erisilemiyor |  |

### `dev_patches` — 1 dosya

| Dosya | Sinif | Kanit | Not |
|---|---|---|---|
| `dev_patches/project_inspect_v2.py` | YETIM | hicbir giristen ve testten erisilemiyor |  |

### `eval` — 5 dosya

| Dosya | Sinif | Kanit | Not |
|---|---|---|---|
| `eval/__init__.py` | CANLI | eval/run_turkish_quality.py -> 1 adim (arac hatti) |  |
| `eval/quality_scorer.py` | CANLI | eval/run_turkish_quality.py -> 1 adim (arac hatti) |  |
| `eval/run_benchmark.py` | CANLI | giris noktasi (B: arac) |  |
| `eval/run_d2_web_policy_eval.py` | CANLI | giris noktasi (B: arac) |  |
| `eval/run_turkish_quality.py` | CANLI | giris noktasi (B: arac) |  |

### `mcp` — 1 dosya

| Dosya | Sinif | Kanit | Not |
|---|---|---|---|
| `mcp/__init__.py` | YETIM | hicbir giristen ve testten erisilemiyor |  |

### `memory` — 5 dosya

| Dosya | Sinif | Kanit | Not |
|---|---|---|---|
| `memory/__init__.py` | CANLI | main.py -> 1 adim |  |
| `memory/entity_extractor.py` | CANLI | main.py -> 2 adim |  |
| `memory/jarvis_db.py` | YETIM | hicbir giristen ve testten erisilemiyor |  |
| `memory/life_graph.py` | CANLI | main.py -> 1 adim |  |
| `memory/memory_manager.py` | CANLI | agent/local_agent.py -> 1 adim |  |

### `rag` — 3 dosya

| Dosya | Sinif | Kanit | Not |
|---|---|---|---|
| `rag/__init__.py` | CANLI | main.py -> 1 adim |  |
| `rag/indexer.py` | CANLI | main.py -> 1 adim |  |
| `rag/rag_engine.py` | CANLI | agent/local_agent.py -> 1 adim |  |

### `scripts` — 18 dosya

| Dosya | Sinif | Kanit | Not |
|---|---|---|---|
| `scripts/_utf8io.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/checkpoint_summary.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/daily_report.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/envanter_uret.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/escalation_policy.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/j0_live_status.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/j0_mic_check.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/j0_spike_b_latency_probe.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/j0_tts_adapters.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/j0_voice_adapters.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/j0_voice_latency_probe.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/j0_voice_loop.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/mutation_gate.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/olc_llm_anatomisi.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/olc_ses_gecikmesi.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/olc_tts_anatomisi.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/orchestrator.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/verifier_runner.py` | CANLI | giris noktasi (B: arac) |  |

### `tests/` — 176 dosya

Hepsi **YALNIZ-TEST**: test kosucusundan baska cagirani yok. Bu bir kusur degil, tanim. Tek tek listelenmedi.

### `tools` — 23 dosya

| Dosya | Sinif | Kanit | Not |
|---|---|---|---|
| `tools/__init__.py` | CANLI | jarvis_desktop.py -> 1 adim |  |
| `tools/browser_agent.py` | YETIM | hicbir giristen ve testten erisilemiyor |  |
| `tools/diagnostics.py` | CANLI | jarvis_brain.py -> 1 adim |  |
| `tools/document_analyst.py` | YETIM | hicbir giristen ve testten erisilemiyor |  |
| `tools/document_reader.py` | CANLI | jarvis_server.py -> 1 adim |  |
| `tools/document_writer.py` | YETIM | hicbir giristen ve testten erisilemiyor |  |
| `tools/file_tools.py` | CANLI | jarvis_brain.py -> 1 adim |  |
| `tools/jarvis_interpreter.py` | YETIM | hicbir giristen ve testten erisilemiyor |  |
| `tools/project_analyst.py` | YETIM | hicbir giristen ve testten erisilemiyor |  |
| `tools/save_conversation.py` | YETIM | hicbir giristen ve testten erisilemiyor |  |
| `tools/security_snapshot.py` | CANLI | jarvis_server.py -> 2 adim |  |
| `tools/system_control.py` | CANLI | jarvis_brain.py -> 1 adim |  |
| `tools/system_intelligence.py` | CANLI | jarvis_server.py -> 1 adim |  |
| `tools/task_snapshot.py` | CANLI | jarvis_server.py -> 2 adim |  |
| `tools/telegram_agent.py` | CANLI | giris noktasi (A) |  |
| `tools/telegram_formatter.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
| `tools/tools.py` | CANLI | jarvis_desktop.py -> 1 adim |  |
| `tools/vector_memory.py` | CANLI | jarvis_brain.py -> 1 adim |  |
| `tools/vision_analyst.py` | YETIM | hicbir giristen ve testten erisilemiyor |  |
| `tools/voice_io.py` | CANLI | jarvis_server.py -> 1 adim |  |
| `tools/wake_word.py` | YETIM | hicbir giristen ve testten erisilemiyor |  |
| `tools/web_research.py` | CANLI | jarvis_brain.py -> 1 adim |  |
| `tools/web_research_eski.py` | YETIM | hicbir giristen ve testten erisilemiyor |  |

### `training` — 7 dosya

| Dosya | Sinif | Kanit | Not |
|---|---|---|---|
| `training/conversation_summarizer.py` | CANLI | giris noktasi (B: arac) |  |
| `training/dashboard.py` | CANLI | giris noktasi (B: arac) |  |
| `training/data_curator.py` | CANLI | giris noktasi (B: arac) |  |
| `training/fine_tune.py` | CANLI | giris noktasi (B: arac) |  |
| `training/fine_tune_eski.py` | CANLI | giris noktasi (B: arac) |  |
| `training/migrate_format.py` | CANLI | giris noktasi (B: arac) |  |
| `training/quality_evaluator.py` | CANLI | giris noktasi (B: arac) |  |

### `voice` — 5 dosya

| Dosya | Sinif | Kanit | Not |
|---|---|---|---|
| `voice/__init__.py` | CANLI | main.py -> 1 adim |  |
| `voice/stt.py` | CANLI | main.py -> 2 adim |  |
| `voice/voice_engine.py` | CANLI | voice_test.py -> 1 adim (arac hatti) |  |
| `voice/voice_interface.py` | YETIM | hicbir giristen ve testten erisilemiyor |  |
| `voice/voice_loop.py` | CANLI | main.py -> 1 adim |  |

## D. Cop adaylari — LISTE, SILME DEGIL

CLAUDE.md §3: *"onceden var olan dead code'a dokunma (gor, soyle, silme)."* Bu bolum bir karar listesidir; bu kart hicbirini silmedi.

| Dosya | Boyut | Son commit |
|---|---|---|
| `automation/TERAZI_ETAP4_2026-09-10/kapsam_olc.py` | 3,594 B | 2026-09-11 |
| `dev_patches/project_inspect_v2.py` | 13,170 B | 2026-05-17 |
| `mcp/__init__.py` | 0 B | 2026-05-12 |
| `memory/jarvis_db.py` | 2,209 B | 2026-05-17 |
| `tools/browser_agent.py` | 1,839 B | 2026-05-12 |
| `tools/document_analyst.py` | 1,253 B | 2026-05-17 |
| `tools/document_writer.py` | 3,695 B | 2026-05-12 |
| `tools/jarvis_interpreter.py` | 1,724 B | 2026-05-17 |
| `tools/project_analyst.py` | 1,349 B | 2026-05-17 |
| `tools/save_conversation.py` | 3,030 B | 2026-05-12 |
| `tools/vision_analyst.py` | 1,015 B | 2026-05-17 |
| `tools/wake_word.py` | 3,159 B | 2026-05-12 |
| `tools/web_research_eski.py` | 5,924 B | 2026-05-12 |
| `voice/voice_interface.py` | 6,159 B | 2026-05-12 |

## E. Erisilebilirligi HESAPLANAMAYAN yerler

Dinamik cagri (`importlib`, `__import__`, `exec`, `getattr`) statik grafikte gorunmez. Asagidaki dosyalar bu bicimleri kullaniyor; onlardan cikan baglar **eksik olabilir**. Bir modul yalniz dinamik yoldan cagriliyorsa YETIM gorunur ama olmayabilir.

- `agents/memory_scorer.py`
  - `L16: sys.path.insert(0, str(ROOT_DIR))`
- `agents/next_action_planner.py`
  - `L26: sys.path.insert(0, str(ROOT))`
- `agents/project_reporter.py`
  - `L26: sys.path.insert(0, str(ROOT))`
- `agents/project_summarizer.py`
  - `L25: sys.path.insert(0, str(ROOT))`
- `agents/query_cache.py`
  - `L188: data[best_key]["last_hit_at"] = __import__("datetime").datetime.now().isoformat(timespec`
- `agents/reporting_state.py`
  - `L26: sys.path.insert(0, str(ROOT))`
- `agents/roadmap_detector.py`
  - `L23: sys.path.insert(0, str(ROOT))`
- `eval/run_d2_web_policy_eval.py`
  - `L36: sys.path.insert(0, str(ROOT))`
- `eval/run_turkish_quality.py`
  - `L36: sys.path.insert(0, str(_REPO))`
- `jarvis_desktop.py`
  - `L10: sys.path.insert(0, str(JARVIS_DIR))`
- `main.py`
  - `L8: sys.path.insert(0, str(Path(__file__).parent))`
- `scripts/j0_mic_check.py`
  - `L25: sys.path.insert(0, str(Path(__file__).resolve().parents[1]))`
- `scripts/j0_spike_b_latency_probe.py`
  - `L521: sys.path.insert(0, str(_repo_root))`
- `scripts/j0_voice_adapters.py`
  - `L17: import importlib.util`
  - `L87: spec = importlib.util.find_spec("RealtimeSTT")`
- `scripts/j0_voice_loop.py`
  - `L102: sys.path.insert(0, str(_scripts))`
  - `L143: sys.path.insert(0, str(_scripts))`
- `scripts/olc_llm_anatomisi.py`
  - `L78: sys.path.insert(0, str(_REPO))`
- `scripts/olc_ses_gecikmesi.py`
  - `L69: sys.path.insert(0, str(_REPO))`
- `scripts/olc_tts_anatomisi.py`
  - `L53: sys.path.insert(0, _yol)`
- `scripts/orchestrator.py`
  - `L48: sys.path.insert(0, str(Path(__file__).resolve().parent))`
- `setup.py`
  - `L48: sys.path.insert(0, str(Path("training")))`
- `tools/telegram_agent.py`
  - `L22: sys.path.insert(0, str(ROOT))`
- `training/data_curator.py`
  - `L7: sys.path.insert(0, str(Path(__file__).parent))`
- `training/fine_tune.py`
  - `L69: __import__(pkg)`
- `voice/voice_loop.py`
  - `L204: sys.path.insert(0, _scripts)`

## F. ORNEK/SABLON — gercek yapilandirma bekleyenler

| Sablon | Beklenen gercek dosya | Var mi |
|---|---|---|
| `.env.example` | `.env` | EVET |
| `.mcp.json.example` | `.mcp.json` | **YOK** |
| `config/api_providers.example.json` | `config/api_providers.json` | **YOK** |
| `config/provider_profiles.example.json` | `config/provider_profiles.json` | **YOK** |
| `docs/templates/autocoder_task.example.md` | `docs/templates/autocoder_task.md` | **YOK** |
| `docs/templates/outcome_contract.example.json` | `docs/templates/outcome_contract.json` | **YOK** |

Bu dosyalarin ICERIGI okunmadi (CLAUDE.md §9). Yalniz varliklari kontrol edildi.

## G. BELGE-VAR-KOD-YOK

Belgelerde adi gecen ama diskte bulunmayan `.py` dosyalari.

| Anilan dosya | Nerede aniliyor |
|---|---|
| `Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/agent/jarvis_agent.py` | `automation/CODEX_DENETIM_2026-09-06.md` |
| `agent/jarvis_agent.py` | `FAILURES.md`, `automation/AHMET_ONAYI_BEKLEYENLER.md`, `automation/CODEX_V2_UYGULAMA_2026-09-07.md` (+7) |
| `agents/presence_model.py` | `automation/FAZ4_ADIM_ONERISI.md`, `automation/IMZASIZ_IS_KUYRUGU.md`, `docs/JARVIS_ENVANTER.md` |
| `agents/proactive_throttle.py` | `automation/E1_S6_DECOMPOSITION.md`, `docs/JARVIS_ENVANTER.md` |
| `core/log_safety.py` | `automation/IMZASIZ_IS_KUYRUGU.md`, `docs/JARVIS_ENVANTER.md`, `docs/OSS_HARVEST_REPORT_2026-08.md` |
| `gen_climate.py` | `automation/FAZ4_ADIM_ONERISI.md`, `docs/JARVIS_ENVANTER.md` |
| `hwfit/fit.py` | `automation/IMZASIZ_IS_KUYRUGU.md`, `docs/JARVIS_ENVANTER.md`, `docs/OSS_HARVEST_REPORT_2026-08.md` |
| `listener.py` | `docs/JARVIS_ENVANTER.md`, `docs/OSS_HARVEST_REPORT_2026-08.md` |
| `llm/tiers.py` | `automation/IMZASIZ_IS_KUYRUGU.md`, `docs/JARVIS_ENVANTER.md`, `docs/OSS_HARVEST_REPORT_2026-08.md` |
| `memory/recall_gate.py` | `automation/IMZASIZ_IS_KUYRUGU.md`, `docs/JARVIS_ENVANTER.md`, `docs/OSS_HARVEST_REPORT_2026-08.md` |
| `research_handler.py` | `docs/JARVIS_ENVANTER.md`, `docs/OSS_HARVEST_REPORT_2026-08.md` |
| `scripts/gen_uydu.py` | `automation/FAZ4_ADIM_ONERISI.md`, `automation/IMZASIZ_IS_KUYRUGU.md`, `docs/JARVIS_ENVANTER.md` |
| `src/config_parser.py` | `docs/JARVIS_ENVANTER.md`, `docs/templates/autocoder_task.example.md` |
| `test_c1_memory_policy.py` | `docs/JARVIS_ENVANTER.md`, `docs/JARVIS_v5_MASTER_ROADMAP.md` |
| `test_j0_tts_adapters.py` | `automation/BLACKBOX_RUNBOOK.md`, `docs/JARVIS_ENVANTER.md` |
| `tests/test_config_parser.py` | `docs/JARVIS_ENVANTER.md`, `docs/templates/autocoder_task.example.md` |
| `tests/test_e1_6e_throttle.py` | `automation/E1_S6_DECOMPOSITION.md`, `docs/JARVIS_ENVANTER.md` |
| `tests/test_gen_uydu.py` | `automation/FAZ4_ADIM_ONERISI.md`, `docs/JARVIS_ENVANTER.md` |
| `tests/test_ha_kesif.py` | `automation/FAZ4_ADIM_ONERISI.md`, `docs/JARVIS_ENVANTER.md` |
| `tests/test_metrics.py` | `docs/JARVIS_ENVANTER.md`, `docs/automation/INTERFACE_CONTRACT.md` |
| `tests/test_panel_model.py` | `automation/FAZ4_ADIM_ONERISI.md`, `docs/JARVIS_ENVANTER.md` |
| `tests/test_presence_model.py` | `automation/FAZ4_ADIM_ONERISI.md`, `docs/JARVIS_ENVANTER.md` |
| `tiers.py` | `docs/JARVIS_ENVANTER.md`, `docs/OSS_HARVEST_REPORT_2026-08.md` |

## H. Kendi `__main__` blogu olan ama giris noktasi SAYILMAYAN moduller

32 modul kendini-deneme blogu tasiyor. Bunlari giris noktasi saymak neredeyse her seyi CANLI gosterirdi; ayri tutuldular. Bir modul bu listedeyse **elle** calistirilabilir demektir.

- `agents/audit_logger.py`, `agents/auto_updater.py`, `agents/daily_digest.py`, `agents/internal_trace.py`, `agents/memory_candidate_queue.py`, `agents/memory_candidate_writer.py`, `agents/memory_retrieval_policy.py`, `agents/memory_schema.py`, `agents/memory_scorer.py`, `agents/model_registry.py`, `agents/next_action_planner.py`, `agents/proactive_core.py`, `agents/proactive_runner.py`, `agents/project_intelligence.py`, `agents/project_reporter.py`, `agents/project_state.py`, `agents/project_summarizer.py`, `agents/provider_smoke.py`, `agents/reporting_state.py`, `agents/roadmap_detector.py`, `agents/semantic_router.py`, `agents/source_scorer.py`, `agents/web_research_policy.py`, `automation/TERAZI_ETAP4_2026-09-10/kapsam_olc.py`, `dev_patches/project_inspect_v2.py`, `memory/jarvis_db.py`, `tools/jarvis_interpreter.py`, `tools/save_conversation.py`, `tools/security_snapshot.py`, `tools/task_snapshot.py`, `tools/wake_word.py`, `tools/web_research_eski.py`

## I. Olcumun kendisi ne kadar guvenilir

Erisilebilirlik iki bagimsiz kaynaktan hesaplandi ve karsilastirildi.

| Kaynak | Dosya-duzeyi kenar |
|---|---|
| Bu betigin AST taramasi | 684 |
| graphify `graph.json` (yalniz `ast` kokenli kod iliskileri) | 472 |
| Yalniz AST'de var | 262 |
| Yalniz graphify'da var | 50 |

Siniflandirma **AST taramasindan** hesaplandi: import iliskisi belirlenimci ve satir satir dogrulanabilir. graphify grafigi ikinci kaynak olarak tutuldu; `calls`/`method` gibi cagri kenarlari import grafiginin gormedigi baglari da tasidigi icin sayisi farklidir.

Yalniz graphify'da gorunen kenarlardan ornekler (cagri kenarlari — import olmadan da olusabilir):

- `eval/run_turkish_quality.py` -> `agents/assistant_executor.py`
- `scripts/j0_live_status.py` -> `scripts/_utf8io.py`
- `scripts/j0_spike_b_latency_probe.py` -> `scripts/_utf8io.py`
- `scripts/j0_spike_b_latency_probe.py` -> `scripts/j0_live_status.py`
- `scripts/j0_tts_adapters.py` -> `tools/tools.py`
- `scripts/j0_voice_loop.py` -> `scripts/_utf8io.py`
- `scripts/j0_voice_loop.py` -> `scripts/j0_live_status.py`
- `scripts/j0_voice_loop.py` -> `scripts/j0_tts_adapters.py`
- `scripts/j0_voice_loop.py` -> `scripts/j0_voice_adapters.py`
- `scripts/olc_ses_gecikmesi.py` -> `agents/provider_profiles.py`

**Ayristirilamayan dosyalar (sozdizimi):**

- `agents/api_executor.py: invalid non-printable character U+FEFF (<unknown>, line 1)`

