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
bırakır. Altı ay sonra tekrar koşturulabilir; harita eskimez.

---

## 0. Tek cümlelik bulgu — JARVIS'in iki ayrı beyni var

`main.py` (**ses hattı**) 24 dosyaya ulaşıyor.
`tools/telegram_agent.py` (**Telegram hattı**) 49 dosyaya ulaşıyor.
**Ortak kümeleri 8 dosya** — ve o sekizin hepsi yaprak yardımcı:

`agents/persona.py` · `agents/model_registry.py` · `agents/data_classifier.py`
`agents/hardware_sentinel.py` · `agents/provider_profiles.py`
`tools/system_intelligence.py` + iki `__init__.py`

Yani **hiçbir karar katmanı paylaşılmıyor.** Router, cascade, maliyet defteri,
dış sağlayıcı hattı, bilgi kartları, aday hafıza kuyruğu — hepsi yalnızca
Telegram tarafında. Sesle konuştuğunuzda JARVIS bunların hiçbirini görmüyor;
`agent/local_agent.py` doğrudan Ollama'ya gidiyor.

Ahmet'in "her şey darmadağın" hissi buradan geliyor: dağınıklık dosya
düzeninde değil, **iki hattın birbirini tanımamasında.**

> Bu bir kusur tespitidir, bir onarım önerisi değil. Ne yapılacağı Faz 2'nin
> ve Ahmet'in konusu.

---

## 1. Ses hattının kablolaması — "Hey JARVIS" dendiğinde ne oluyor

Her ok `dosya:satır` ile doğrulanabilir.

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

**Bu hatta olmayanlar** (ve Telegram hattında olanlar): `local_first_router`,
`assistant_executor`, `model_cascade`, `cost_ledger`, `api_executor`,
`redaction_guard`, `provider_selector`, `executor_registry`, `web_research`,
`vector_memory`, `knowledge_card_*`, `tiered_memory`, `retrieval_priority`.

---

## 2. Dış model hattının gerçek durumu

Kartın işaret ettiği beş modül **yazılmış, test edilmiş ve birbirine
bağlanmış** — ama tek bir kapıdan asılı duruyorlar.

| Modül | Sınıf | Gerçek durum |
|---|---|---|
| `agents/local_first_router.py` | CANLI | `tools/telegram_agent.py` → 1 adım. Ses hattında **yok**. |
| `agents/assistant_executor.py` | CANLI | Yalnız `tools/telegram_agent.py` import ediyor. |
| `agents/cost_ledger.py` | CANLI | `telegram_agent`, `local_first_router`, `api_budget_gate` besliyor. |
| `agents/api_executor.py` | CANLI | 3 adım uzakta; `executor_registry` ve `api_executor_adapter` üzerinden. |
| `agents/provider_profiles.py` | CANLI | Tek modül ki **her iki hatta da** ulaşılıyor (ses hattına `data_classifier` üzerinden, 3 adım). |
| **`agents/api_budget_gate.py`** | **YALNIZ-TEST** | **Hiçbir üretim modülü import etmiyor.** Bütçe kapısı canlı hatta bağlı değil. |

**Çalışması için eksik olanlar** (ölçüldü — hiçbirinin *içeriği* okunmadı):

- `config/provider_profiles.json` — `agents/assistant_executor.py:144`
  bu dosyayı okuyor; diskte yalnız `.example` var.
- `config/api_providers.json` — yalnız `.example` var; üretim kodunda okuyan
  bulunamadı, yalnız `tests/test_api_executor.py:327` örneği doğruluyor.
- `.env` — **diskte yok.** `agents/api_executor.py:287` sağlayıcı anahtarını
  `os.environ`'dan okuyor (`GEMINI_API_KEY`, `DEEPSEEK_API_KEY`; satır 75, 84).
  Anahtar yoksa `api_executor.py:391` "Missing API key environment variable"
  döndürür — yani hat **kurulu ama yakıtsız**.
  *(Yalnız varlık kontrolü yapıldı; `.env` okunmadı, loglanmadı — §9.)*

**Özet:** mimari raftaki bir prototip değil, **bağlanmış ama tek hatta
sınırlı ve yapılandırmasız** bir sistem. "Kuralım" demeden önce bakılacak
yer burası.

### Yanındaki ikinci örnek: proaktif katman

Aynı desen bir kez daha. `agents/proactive_core.py` CANLI (Telegram, 1 adım),
ama üstüne kurulan katmanın tamamı **YALNIZ-TEST**:
`proactive_runner` · `proactive_policy` · `proactive_delivery` ·
`proactive_runtime` · `proactive_telegram_adapter`.

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
konmamış**.

**Ç2 — Bütçe kapısı belgede var, hatta yok.** `agents/api_budget_gate.py`
testleriyle birlikte duruyor ama hiçbir üretim modülü onu çağırmıyor. Dış
model çağrısı yapan hat (`assistant_executor` → `executor_registry` →
`api_executor`) bütçe kapısından geçmiyor.

**Ç3 — `config/*.json` yalnız `.example` olarak var.** İki yapılandırma
dosyası da gerçek hâliyle diskte yok; biri (`provider_profiles.json`) üretim
kodunda **okunuyor**.

**Ç4 — Öneri belgeleri, tamamlanmış iş gibi okunabiliyor.**
`docs/OSS_HARVEST_REPORT_2026-08.md` altı modül adı veriyor
(`core/log_safety.py`, `llm/tiers.py`, `memory/recall_gate.py`, `listener.py`,
`research_handler.py`, `hwfit/fit.py`); hiçbiri repoda yok.
`automation/FAZ4_ADIM_ONERISI.md` benzer şekilde beş test dosyası ve iki
modül anıyor. Bunlar büyük olasılıkla **öneri**, iddia değil — ama belgeler
bunu başlıkta söylemiyor. Tam liste §G'de. *[EMİN DEĞİLİM: niyetin öneri
olduğunu belgelerin tonundan çıkardım, açık bir "önerilen" etiketi yok.]*

**Ç5 — 24 modül yalnız kendi testinden erişilebiliyor.** Bunların bir kısmı
gerçekten hazırda beklemek üzere yazılmış olabilir; ama bir modülün tek
kullanıcısının kendi testi olması, "entegre" ile "yazılmış" arasındaki farkın
tam olarak ölçüsüdür. Liste §C'de, `agents/` tablosunda.

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
2. **`tools/tools.py`'deki `exec`/`eval`.** İncelendi: `L482` ve `L509`
   `run_python_code` aracının kum havuzu; **modül yüklemiyor**. Yani
   `tools/` altındaki 8 yetim dosya dinamik olarak da çağrılmıyor —
   gerçekten erişilemez durumdalar.
3. **`agent/jarvis_agent.py:84` ve `agents/query_cache.py:188`**
   `__import__("httpx")` / `__import__("datetime")` kullanıyor; ikisi de
   dış kütüphane, repo modülü değil — haritayı etkilemiyor.
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

Izlenen `.py`: **306** (test: 151, test disi: 155)

| Sinif | Adet |
|---|---|
| CANLI | 118 |
| YALNIZ-TEST | 175 |
| YETIM | 13 |

Test disi dosyalarin sinif dagilimi:

| Sinif | Adet |
|---|---|
| CANLI | 118 |
| YALNIZ-TEST | 24 |
| YETIM | 13 |

## B. Giris noktalari

**A — sistemi calistiranlar.** JARVIS'i baslatan kapilar.

| Dosya | Buradan erisilen dosya sayisi |
|---|---|
| `main.py` | 24 |
| `gui.py` | 15 |
| `jarvis_desktop.py` | 15 |
| `jarvis_server.py` | 35 |
| `jarvis_brain.py` | 22 |
| `agent/local_agent.py` | 14 |
| `tools/telegram_agent.py` | 49 |

**PARK EDILMIS (CLAUDE.md §9 — CALISTIRMA).** Grafige neyi besledigi gorunsun diye dahil edildi.

| Dosya | Buradan erisilen dosya sayisi |
|---|---|
| `auto_runner.py` | 2 |

**B — arac kapilari** (29 dosya): olcum, kurulum, bakim. Bunlardan erisilen bir modul CANLI'dir ama ses hattinda olmayabilir; kanit sutunu hangisinden geldigini soyler.

## C. Her `.py` dosyasinin sinifi

`kanit` sutunu erisilebilirligin NASIL hesaplandigini soyler: hangi giris noktasindan kac adim.

### `(kok)` — 12 dosya

| Dosya | Sinif | Kanit | Not |
|---|---|---|---|
| `auto_runner.py` | CANLI | giris noktasi (PARK EDILMIS) |  |
| `config.py` | CANLI | main.py -> 1 adim | `.env` bekliyor |
| `gui.py` | CANLI | giris noktasi (A) |  |
| `indir.py` | CANLI | giris noktasi (B: arac) |  |
| `jarvis_brain.py` | CANLI | giris noktasi (A) |  |
| `jarvis_desktop.py` | CANLI | giris noktasi (A) | `.env` bekliyor |
| `jarvis_server.py` | CANLI | giris noktasi (A) | `.env` bekliyor |
| `jarvis_snapshot.py` | CANLI | giris noktasi (B: arac) | `.env` bekliyor |
| `main.py` | CANLI | giris noktasi (A) | `.env` bekliyor |
| `setup.py` | CANLI | giris noktasi (B: arac) |  |
| `setup_password.py` | CANLI | giris noktasi (B: arac) | `.env` bekliyor |
| `voice_test.py` | CANLI | giris noktasi (B: arac) |  |

### `agent` — 4 dosya

| Dosya | Sinif | Kanit | Not |
|---|---|---|---|
| `agent/__init__.py` | CANLI | main.py -> 1 adim |  |
| `agent/jarvis_agent.py` | CANLI | main.py -> 1 adim |  |
| `agent/local_agent.py` | CANLI | giris noktasi (A) |  |
| `agent/local_agent_memory.py` | CANLI | agent/local_agent.py -> 1 adim |  |

### `agents` — 75 dosya

| Dosya | Sinif | Kanit | Not |
|---|---|---|---|
| `agents/__init__.py` | CANLI | main.py -> 1 adim |  |
| `agents/answer_crystallizer.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
| `agents/api_budget_gate.py` | YALNIZ-TEST | yalniz testlerden: tests/test_api_budget_gate.py -> 1 adim |  |
| `agents/api_executor.py` | CANLI | tools/telegram_agent.py -> 3 adim | `.env` bekliyor |
| `agents/api_executor_adapter.py` | CANLI | tools/telegram_agent.py -> 3 adim |  |
| `agents/assistant_executor.py` | CANLI | tools/telegram_agent.py -> 1 adim | `config/provider_profiles.json` bekliyor |
| `agents/audit_logger.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
| `agents/auto_updater.py` | CANLI | jarvis_server.py -> 1 adim |  |
| `agents/blackbox_log.py` | YALNIZ-TEST | yalniz testlerden: tests/test_blackbox_log.py -> 1 adim | `.env` bekliyor |
| `agents/cost_ledger.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
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
| `agents/persona.py` | CANLI | agent/local_agent.py -> 1 adim | `.env` bekliyor |
| `agents/privacy_level_bridge.py` | CANLI | tools/telegram_agent.py -> 2 adim |  |
| `agents/proactive_agent.py` | CANLI | jarvis_server.py -> 1 adim |  |
| `agents/proactive_core.py` | CANLI | jarvis_server.py -> 1 adim |  |
| `agents/proactive_delivery.py` | YALNIZ-TEST | yalniz testlerden: tests/test_e1_6b_delivery_result.py -> 1 adim |  |
| `agents/proactive_policy.py` | YALNIZ-TEST | yalniz testlerden: tests/test_e1_6b_delivery_result.py -> 1 adim | `.env` bekliyor |
| `agents/proactive_runner.py` | YALNIZ-TEST | yalniz testlerden: tests/test_e1_6a_proactive_runner.py -> 1 adim | `.env` bekliyor |
| `agents/proactive_runtime.py` | YALNIZ-TEST | yalniz testlerden: tests/test_e1_6b_delivery_result.py -> 1 adim |  |
| `agents/proactive_telegram_adapter.py` | YALNIZ-TEST | yalniz testlerden: tests/test_proactive_telegram_adapter.py -> 1 adim |  |
| `agents/project_intelligence.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
| `agents/project_reporter.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
| `agents/project_state.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
| `agents/project_summarizer.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
| `agents/project_workspace.py` | YALNIZ-TEST | yalniz testlerden: tests/test_m0_4_project_workspace.py -> 1 adim |  |
| `agents/provider_decision.py` | CANLI | tools/telegram_agent.py -> 2 adim | `.env` bekliyor |
| `agents/provider_profiles.py` | CANLI | agent/local_agent.py -> 2 adim |  |
| `agents/provider_selector.py` | CANLI | tools/telegram_agent.py -> 2 adim |  |
| `agents/provider_smoke.py` | YALNIZ-TEST | yalniz testlerden: tests/test_provider_smoke.py -> 1 adim | `.env` bekliyor |
| `agents/query_cache.py` | YALNIZ-TEST | yalniz testlerden: tests/jarvis_system_audit.py -> 1 adim |  |
| `agents/redaction_guard.py` | CANLI | tools/telegram_agent.py -> 2 adim | `.env` bekliyor |
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
| `agents/web_research_policy.py` | CANLI | jarvis_brain.py -> 1 adim | `.env` bekliyor |
| `agents/world_inventory_linker.py` | YALNIZ-TEST | yalniz testlerden: tests/test_m0_3_world_inventory_linker.py -> 1 adim |  |
| `agents/world_model.py` | YALNIZ-TEST | yalniz testlerden: tests/test_m0_world_model.py -> 1 adim |  |

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
| `rag/indexer.py` | CANLI | main.py -> 1 adim | `.env` bekliyor |
| `rag/rag_engine.py` | CANLI | agent/local_agent.py -> 1 adim |  |

### `scripts` — 14 dosya

| Dosya | Sinif | Kanit | Not |
|---|---|---|---|
| `scripts/_utf8io.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/checkpoint_summary.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/daily_report.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/escalation_policy.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/j0_live_status.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/j0_mic_check.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/j0_spike_b_latency_probe.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/j0_tts_adapters.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/j0_voice_adapters.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/j0_voice_latency_probe.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/j0_voice_loop.py` | CANLI | giris noktasi (B: arac) | `.env` bekliyor |
| `scripts/mutation_gate.py` | CANLI | giris noktasi (B: arac) |  |
| `scripts/orchestrator.py` | CANLI | giris noktasi (B: arac) | `.env` bekliyor |
| `scripts/verifier_runner.py` | CANLI | giris noktasi (B: arac) |  |

### `tests/` — 151 dosya

Hepsi **YALNIZ-TEST**: test kosucusundan baska cagirani yok. Bu bir kusur degil, tanim. Tek tek listelenmedi.

### `tools` — 23 dosya

| Dosya | Sinif | Kanit | Not |
|---|---|---|---|
| `tools/__init__.py` | CANLI | gui.py -> 1 adim |  |
| `tools/browser_agent.py` | YETIM | hicbir giristen ve testten erisilemiyor |  |
| `tools/diagnostics.py` | CANLI | jarvis_brain.py -> 1 adim |  |
| `tools/document_analyst.py` | YETIM | hicbir giristen ve testten erisilemiyor |  |
| `tools/document_reader.py` | CANLI | jarvis_server.py -> 1 adim |  |
| `tools/document_writer.py` | YETIM | hicbir giristen ve testten erisilemiyor |  |
| `tools/file_tools.py` | CANLI | jarvis_brain.py -> 1 adim | `.env` bekliyor |
| `tools/jarvis_interpreter.py` | YETIM | hicbir giristen ve testten erisilemiyor |  |
| `tools/project_analyst.py` | YETIM | hicbir giristen ve testten erisilemiyor |  |
| `tools/save_conversation.py` | YETIM | hicbir giristen ve testten erisilemiyor |  |
| `tools/security_snapshot.py` | CANLI | jarvis_server.py -> 2 adim |  |
| `tools/system_control.py` | CANLI | jarvis_brain.py -> 1 adim |  |
| `tools/system_intelligence.py` | CANLI | jarvis_server.py -> 1 adim |  |
| `tools/task_snapshot.py` | CANLI | jarvis_server.py -> 2 adim |  |
| `tools/telegram_agent.py` | CANLI | giris noktasi (A) | `.env` bekliyor |
| `tools/telegram_formatter.py` | CANLI | tools/telegram_agent.py -> 1 adim |  |
| `tools/tools.py` | CANLI | gui.py -> 1 adim |  |
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
| `voice/stt.py` | CANLI | main.py -> 2 adim | `.env` bekliyor |
| `voice/voice_engine.py` | CANLI | voice_test.py -> 1 adim (arac hatti) |  |
| `voice/voice_interface.py` | YETIM | hicbir giristen ve testten erisilemiyor |  |
| `voice/voice_loop.py` | CANLI | main.py -> 1 adim |  |

## D. Cop adaylari — LISTE, SILME DEGIL

CLAUDE.md §3: *"onceden var olan dead code'a dokunma (gor, soyle, silme)."* Bu bolum bir karar listesidir; bu kart hicbirini silmedi.

| Dosya | Boyut | Son commit |
|---|---|---|
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

- `agent/jarvis_agent.py`
  - `L84: http_client=__import__("httpx").Client(verify=False)`
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
  - `L35: sys.path.insert(0, str(_REPO))`
- `gui.py`
  - `L11: sys.path.insert(0, str(Path(__file__).parent))`
- `jarvis_desktop.py`
  - `L10: sys.path.insert(0, str(JARVIS_DIR))`
- `main.py`
  - `L9: sys.path.insert(0, str(Path(__file__).parent))`
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
- `scripts/orchestrator.py`
  - `L48: sys.path.insert(0, str(Path(__file__).resolve().parent))`
- `setup.py`
  - `L48: sys.path.insert(0, str(Path("training")))`
- `tools/telegram_agent.py`
  - `L22: sys.path.insert(0, str(ROOT))`
- `tools/tools.py`
  - `L436: "import shutil", "__import__", "eval(", "exec(", "open("]`
  - `L482: exec(code, safe_globals)`
  - `L509: result = eval(expression, {"__builtins__": {}}, safe_dict)`
- `training/data_curator.py`
  - `L7: sys.path.insert(0, str(Path(__file__).parent))`
- `training/fine_tune.py`
  - `L69: __import__(pkg)`
- `voice/voice_loop.py`
  - `L165: sys.path.insert(0, _scripts)`

## F. ORNEK/SABLON — gercek yapilandirma bekleyenler

| Sablon | Beklenen gercek dosya | Var mi |
|---|---|---|
| `.env.example` | `.env` | **YOK** |
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
| `agents/presence_model.py` | `automation/FAZ4_ADIM_ONERISI.md` |
| `agents/proactive_throttle.py` | `automation/E1_S6_DECOMPOSITION.md` |
| `core/log_safety.py` | `docs/OSS_HARVEST_REPORT_2026-08.md` |
| `gen_climate.py` | `automation/FAZ4_ADIM_ONERISI.md` |
| `hwfit/fit.py` | `docs/OSS_HARVEST_REPORT_2026-08.md` |
| `listener.py` | `docs/OSS_HARVEST_REPORT_2026-08.md` |
| `llm/tiers.py` | `docs/OSS_HARVEST_REPORT_2026-08.md` |
| `memory/recall_gate.py` | `docs/OSS_HARVEST_REPORT_2026-08.md` |
| `research_handler.py` | `docs/OSS_HARVEST_REPORT_2026-08.md` |
| `scripts/gen_uydu.py` | `automation/FAZ4_ADIM_ONERISI.md` |
| `src/config_parser.py` | `docs/templates/autocoder_task.example.md` |
| `test_c1_memory_policy.py` | `docs/JARVIS_v5_MASTER_ROADMAP.md` |
| `test_j0_tts_adapters.py` | `automation/BLACKBOX_RUNBOOK.md` |
| `tests/test_config_parser.py` | `docs/templates/autocoder_task.example.md` |
| `tests/test_e1_6e_throttle.py` | `automation/E1_S6_DECOMPOSITION.md` |
| `tests/test_gen_uydu.py` | `automation/FAZ4_ADIM_ONERISI.md` |
| `tests/test_ha_kesif.py` | `automation/FAZ4_ADIM_ONERISI.md` |
| `tests/test_metrics.py` | `docs/automation/INTERFACE_CONTRACT.md` |
| `tests/test_panel_model.py` | `automation/FAZ4_ADIM_ONERISI.md` |
| `tests/test_presence_model.py` | `automation/FAZ4_ADIM_ONERISI.md` |
| `tiers.py` | `docs/OSS_HARVEST_REPORT_2026-08.md` |

## H. Kendi `__main__` blogu olan ama giris noktasi SAYILMAYAN moduller

31 modul kendini-deneme blogu tasiyor. Bunlari giris noktasi saymak neredeyse her seyi CANLI gosterirdi; ayri tutuldular. Bir modul bu listedeyse **elle** calistirilabilir demektir.

- `agents/audit_logger.py`, `agents/auto_updater.py`, `agents/daily_digest.py`, `agents/internal_trace.py`, `agents/memory_candidate_queue.py`, `agents/memory_candidate_writer.py`, `agents/memory_retrieval_policy.py`, `agents/memory_schema.py`, `agents/memory_scorer.py`, `agents/model_registry.py`, `agents/next_action_planner.py`, `agents/proactive_core.py`, `agents/proactive_runner.py`, `agents/project_intelligence.py`, `agents/project_reporter.py`, `agents/project_state.py`, `agents/project_summarizer.py`, `agents/provider_smoke.py`, `agents/reporting_state.py`, `agents/roadmap_detector.py`, `agents/semantic_router.py`, `agents/source_scorer.py`, `agents/web_research_policy.py`, `dev_patches/project_inspect_v2.py`, `memory/jarvis_db.py`, `tools/jarvis_interpreter.py`, `tools/save_conversation.py`, `tools/security_snapshot.py`, `tools/task_snapshot.py`, `tools/wake_word.py`, `tools/web_research_eski.py`

## I. Olcumun kendisi ne kadar guvenilir

Erisilebilirlik iki bagimsiz kaynaktan hesaplandi ve karsilastirildi.

| Kaynak | Dosya-duzeyi kenar |
|---|---|
| Bu betigin AST taramasi | 607 |
| graphify `graph.json` (yalniz `ast` kokenli kod iliskileri) | 418 |
| Yalniz AST'de var | 226 |
| Yalniz graphify'da var | 37 |

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
- `scripts/orchestrator.py` -> `scripts/escalation_policy.py`

**Ayristirilamayan dosyalar (sozdizimi):**

- `agents/api_executor.py: invalid non-printable character U+FEFF (<unknown>, line 1)`
- `tests/conftest.py: invalid non-printable character U+FEFF (<unknown>, line 1)`
- `tests/test_api_executor.py: invalid non-printable character U+FEFF (<unknown>, line 1)`

