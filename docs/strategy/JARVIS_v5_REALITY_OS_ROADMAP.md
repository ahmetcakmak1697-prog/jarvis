# JARVIS v5 — Reality OS Strategic Roadmap
### Claude + GPT + Gemini üçlü mutabakatı ile süzülmüş stratejik üst harita

> **Not:** Bu dosya mevcut teknik `JARVIS_v5_MASTER_ROADMAP.md`'nin **yerine geçmez**;
> onun **yanında stratejik üst harita** olarak durur. Teknik sıra orada, "neden / nereye / neye kapılmayacağız" burada.
> Repo'da önerilen konum: `docs/strategy/JARVIS_v5_REALITY_OS_ROADMAP.md`
>

> Bu doküman, üç gün süren araştırmanın + commit gerçeğinin + üç yapay zekanın
> ortak kararının nihai birleşimidir. Amaç: Ahmet'e özel, local-first, sesli,
> sadık, sinematik bir kişisel işletim sistemine **sıralı mühendislikle** yaklaşmak.
>
> **Altın kural:** Heyecan vizyonu besler, ama projeyi başarıya götüren sıralı
> mühendisliktir. Yeni çıkan her güçlü model/proje "stratejik not"tur, "sıra değiştirici" değildir.

---

## 0. Sembol Dili

| Sembol | Anlamı |
|--------|--------|
| ✅ | Tamamlandı |
| 🟧 | Şu an kaldığımız / aktif nokta |
| ⬜ | Yapılacak |
| 🟡 | Açık kaynak inceleme / araştırma (kapanmaz) |
| 🔒 | Güvenlik kritik |
| ⚠️ | Riskli / sandbox şart |
| 🚀 | 2×RTX 3090 sonrası güçlenecek |
| ⚪ | Vision Catalog / uzak gelecek |

---

## 1. Vizyon (tek cümle)

Jarvis = Ahmet'in dünyasını bilen (oda/cihaz/proje/envanter), öğrendiğinden sonuç çıkaran
(memory synthesis), önce yerelde çözen / gerektiğinde dışarı görev dağıtan (local-first router),
sesle birlikte çalışan, **tek bir karakter gibi** davranan kişisel gerçeklik işletim sistemi.

> Tasarım pusulası: *"Tony Stark zeki değildi; API limiti yoktu."*
> → önce local → cache/memory → ucuz model → en son premium API; her zaman redaction'dan sonra.

---

## 2. Cross-cutting İlkeler (her blokta geçerli)

- **Local-first cascade:** L0 exact cache → L1 semantic cache → L2 RAG/memory → L3 local LLM → L4 ucuz gateway → L5 ucuz-güçlü model → L6 premium API.
- **Redaction-before-external:** dış modele giden hiçbir veri redaction'dan geçmeden gitmez.
- **No overwrite, patch only:** byte-safe, anchor-based, fail-loud.
- **Her blok = küçük patch → test → smoke → commit → review.**
- **Dual/Triple-control:** kod ritmi + mimari/güvenlik review ayrı kanaldan (GPT ritim, Claude vizyon/mimari, Gemini denge).
- **Model kilidi yok:** hiçbir model "ana beyin" ilan edilmez; görev ataması G1 Benchmark Lab ile belirlenir.
- **schema_version her veri dosyasında**, test izolasyonu temp root ile, model adı koda değil ModelRegistry'ye.
- **Her ~%10 görünür ilerlemede:** eşe/aileye gösterilebilir küçük bir demo/motivasyon çıktısı.

### 2.1 — JarvisOrgan Sözleşmesi (sinir sistemi · H1.5'te tanımlandı)

> Açık kaynak araçlar Jarvis'e komut vermez; Jarvis onları **organ** olarak kullanır.
> Core hiçbir organın özel API'sine doğrudan bağımlı olmaz; her organ önce bu sözleşmeye sarılır.
> Taşıma yolu serbest (REST / MCP / import / socket); ama Core'un gördüğü sözleşme tektir.

Her organ şunları sunmak zorundadır:
- **Mevcut (H1.5'te tanımlı):** `health` · `capabilities` · `invoke` · `trace_hook` · `permission_level` · `degrade_mode`
- **Hedef (henüz tam kodlanmadı):** `timeout_policy` · `fallback_policy`

Güvenlik çizgisi: `candidate → analysis → proposal → approval → memory`

---

## 3. Tamamlananlar ✅

| Blok | İçerik |
|------|--------|
| ✅ A1–A6 | Temel güvenlik, çekirdek stabilizasyon, redaction guard |
| ✅ B1–B2.7 | Task sistemi, task allowlist, Telegram, Tailscale, mobil hotfix |
| ✅ C1.1–C1.5 | MemoryPolicy, SchemaMapper, CandidateQueue, Expiry/GC, RetrievalPolicy, Writer route guard |
| ✅ C1.T1–T7 | Türkçe sensitive/encoding kalite hattı (şifre/eşim/hastalık/ırk/din doğru route) |
| ✅ C1.6A | Memory Synthesizer — SynthesisState skeleton |
| ✅ C1.6B | Memory Synthesizer — CandidateCollector (filtre + guard'lar) |
| ✅ C1.6C | Memory Synthesizer — Keyword Frequency Synthesizer (proposal-only + Turkish fold + sensitive guard) |
| ✅ C2 | Project intelligence, state, roadmap detect, next-action, telegram intel |
| ✅ C3 / C4 | Reporting state, structured output guard, internal trace |
| ✅ H1.5 / H1.6 | Organ contract (JarvisOrgan), repo hygiene |
| ✅ M0–M0.4 | World model, inventory, world-inventory linker, project workspace |
| ✅ — | Deep encoding cleanup (BOM, UTF-16→UTF-8, Türkçe string'ler, 22 dosya) |

---

## 4. ✅ SON TAMAMLANAN ADIM — C1.6C

### ✅ C1.6C — Keyword Frequency Synthesizer

> Jarvis'in tekrar eden temalari guvenli sekilde fark etmesinin ilk somut adimi tamamlandi.
> Bu blok memory yazmaz; sadece proposal uretir.

**Kapsam:** LLM yok ? VectorMemory yazimi yok ? ApprovalQueue yazimi yok ? yan etki sifir.
Sadece `_synthesis_text` okur, kural tabanli analiz eder, **proposal** doner.

**Tema seti:**
| Tema | Keywords | Summary |
|------|----------|---------|
| jarvis | jarvis, roadmap, commit, patch, test, repo, kod | Jarvis gelistirme calismalari aktif gorunuyor. |
| arduino | arduino, esp32, elektronik, breadboard, jumper, maker | Elektronik ve Arduino ogrenme sureci aktif gorunuyor. |
| eshot | eshot, rapor, telemetri, rolanti, yakit, ihlal | ESHOT raporlama ve telemetri calismalari aktif gorunuyor. |
| health_rest | yorgun, uykusuz, dinlen, mola, gece | Dinlenme ve enerji yonetimi dikkat gerektiriyor. |

**E?ik:** `min_mentions = 3` (testte 2) ? **Confidence:** `min(95, 50 + source_count * 10)`

**Output:** `{ theme, summary, source_count, confidence, source_ids[], proposal_type: "synthesized_memory" }`

**Done kriteri:**
- ✅ threshold alti proposal uretmez
- ✅ threshold ustu tema proposal uretir
- ✅ source_ids dogru gelir
- ✅ sensitive candidate tekrar yazima gitmez + savunma guard'i
- ✅ output sadece proposal olur
- ✅ C1.6C testleri gecer (`tests/test_c1_6_memory_synthesizer.py` -> `21 passed`)
- ✅ C1 memory smoke gecer (`51 passed, 78 deselected, 2 warnings`)
- ✅ core integration smoke gecer (`22 passed, 107 deselected, 2 warnings`)

### ✅ C1.6C Kapanis Notu

C1.6C teknik olarak tamamlandi ve commitlendi.

- Commit: `e76abb55c Add C1.6C keyword synthesizer safety tests`
- Test: `tests/test_c1_6_memory_synthesizer.py` -> `21 passed`
- Memory/C1 smoke: `51 passed, 78 deselected, 2 warnings`
- Core smoke: `22 passed, 107 deselected, 2 warnings`
- Kapsam: proposal-only; LLM yok, vector yazimi yok, approval queue yazimi yok.
- Guvenlik: sensitive/review/untrusted benzeri adaylar sentez threshold'una katkida bulunmaz.
- Turkce kalite: ASCII-fold + suffix/substring matching ile `I/?/?`, `?/?/?/?/?` kaynakli sessiz kacislar test altinda.
- Not: Pytest `TestCore __init__` collection warning'leri bu bloktan once de vardir; bloklayici degildir.

---


### ? C1.6D Kapanis Notu

C1.6D teknik olarak tamamlandi ve commitlendi.

- Commit: `3a43c63e5 Add public memory candidate listing API`
- Commit: `d2195c6c4 Add C1.6D synthesis proposal review queue`
- Commit: `70ac0652e Add transactional C1.6D synthesis submitter`
- Commit: `bd2b38b09 Add C1.6D synthesis end-to-end test`
- Test: `tests/test_c1_6_memory_synthesizer.py` -> `29 passed`
- Memory/C1 smoke: `42 passed, 95 deselected, 2 warnings`
- Core smoke: `22 passed, 115 deselected, 2 warnings`
- Kapsam: synthesized proposal -> `pending_review` review queue.
- Guvenlik: queue yazimi basarili olmadan `source_ids` processed isaretlenmez.
- Guvenlik: dogrudan VectorMemory/long-term memory yazimi yoktur.
- Debt: `MemoryCandidateQueue.list_candidates/list_all` public API eklendi; synthesizer private `_load` kullanmiyor.
- Not: Pytest `TestCore __init__` collection warning'leri bu bloktan once de vardir; bloklayici degildir.

### [DONE] C1.6E-1 Kapanis Notu

C1.6E'nin ilk guvenlik/gorunurluk halkasi tamamlandi ve commitlendi.

- Commit: `de8cb9273 Add C1.6E synthesis review status tests`
- Commit: `a5aaec685 Show synthesis review metadata in Telegram memory display`
- Test: `tests/test_c1_2_telegram_memory_display.py` -> `4 passed`
- Test: `tests/test_c1_5_memory_candidate_writer_route_guard.py` -> `4 passed`
- Test: `tests/test_c1_6_memory_synthesizer.py` -> `32 passed`
- Memory/C1 smoke: `52 passed, 90 deselected, 2 warnings`
- Core smoke: `22 passed, 120 deselected, 2 warnings`
- Kapsam: synthesis candidate approved/rejected/deferred lifecycle test altina alindi.
- Kapsam: invalid decision reddediliyor.
- Kapsam: `decide()` basarili durumda `candidate_id` donduruyor.
- Guvenlik: approved synthesis candidate bile `review_queue` nedeniyle vector memory'ye otomatik yazilmiyor.
- Gorunurluk: Telegram memory display synthesis metadata gosteriyor (`status`, `decision`, `proposal_type`, `theme`, `source_ids`).
- Not: Pytest `TestCore __init__` collection warning'leri bu bloktan once de vardir; bloklayici degildir.

C1.6E-2 tamamlandi. Siradaki kontrollu adim: [ACTIVE] C1.6E-3 - Synthesis Promotion Gate Design.

### [DONE] C1.6E-2 Kapanis Notu

C1.6E-2A/2B tamamlandi ve commitlendi.

- Commit: `af9d095d7 Add C1.6E Telegram approve behavior tests`
- Commit: `408110391 Add Telegram mem_store command`
- Test: `tests/test_c1_6e_telegram_memory_approve.py` -> `3 passed`
- Test: `tests/test_c1_6e_telegram_memory_store.py` -> `5 passed`
- Focused approve/store suite: `8 passed`
- Writer guard + C1.6 synthesizer suite: `36 passed`
- Memory/C1 smoke: `60 passed, 90 deselected, 2 warnings`
- Core smoke: `22 passed, 128 deselected, 2 warnings`
- Kapsam: `/mem_approve` davranisi test altina alindi.
- Kapsam: `/mem_store <id>` ayri uzun hafiza yazim kapisi olarak eklendi.
- Guvenlik: `/mem_store` pending/rejected/deferred/expired adaylari dogrudan yazmaz; once approved status ister.
- Guvenlik: writer policy/route bloklarsa sebebiyle birlikte yazilmadi mesaji doner.
- Not: synthesis review_queue adaylari halen otomatik semantic vector yazimina acilmadi.

Siradaki kontrollu adim: [ACTIVE] C1.6E-3 - Synthesis Promotion Gate Design.

## 5. Kritik Yol — C1.6 Sentez Omurgası (sırayla)

| Blok | İçerik |
|------|--------|
| ✅ C1.6C | Keyword/tema frekans sentezleyici (tamamlandi: proposal-only, Turkish fold, source_ids, sensitive guard) |
| ✅ C1.6D | Synthesis proposal -> approval queue (dogrudan vector'e YAZMAZ) |
| ✅ C1.6D-debt | Tech debt tamamlandi: MemoryCandidateQueue.list_candidates/list_all eklendi; synthesizer private _load kullanmiyor |
| ✅ C1.6E | Synthesized memory review/status + `/mem_approve` behavior + `/mem_store` write gate tamamlandi |
| ✅ C1.6E-3 | Synthesis Promotion Gate Design: MemorySynthesisPromoter + /mem_promote + globals() fix + mark_stored failure test |
| ✅ C1.6F | Session/day closure summary ("bugün şunları öğrendim efendim") |
| ✅ C1.6G | Source-linked memory provenance (resolver + promotion metadata + provenance links) |
| ✅ **C1.6H** | **Answer Crystallization** ⭐ (KnowledgeCardStore + AnswerCrystallizer + Promoter + Retriever + Telegram) |

### ✅ C1.6H — Answer Crystallization (tamamlandi)

> "Bir kez pahalı modelden öğren, yerelde ömür boyu sakla, bir daha sorma."
> API-limit problemini çözmenin en güçlü yolu. Senin Vulcan S örneğinin tam karşılığı.

Akış: pahalı modelden (L6) kaliteli cevap al → özet + kaynak + yapısal bilgi kartı üret →
`knowledge/<konu>.md` + vector index'e işle → sonraki sefer API'ye gitmeden yereldan cevapla.

- ⬜ kristalleştirme tetikleyici (hangi cevap kalıcı bilgiye değer?)
- ⬜ yapısal bilgi kartı şeması (konu, kaynak model, tarih, alanlar)
- ⬜ `knowledge/` registry + vector yazım (approval kapılı)
- ⬜ memory_search önce kristalize bilgiye bakar
- ⬜ örnek: `VULCAN_S_2023_MAINTENANCE_MIND` (tork, buji sırası, prosedür)

> Eval notu: C1.6 hattına LoCoMo-tarzı uzun-bağlam hatırlama test seti ekle
> (kaynak: NirDiamant/Agent_Memory_Techniques). `eval/turkish_quality_cases.json`'a memory-routing case'leri ekle.

---

## 6. Tematik Hatlar (Tracks)

### ✅ C1.7 — Tiered Memory & Olgunlasma
- ✅ C1.7 TieredMemoryRouter + MemoryRoute tier/tier_reason + MemoryMaturityScorer + RetrievalPriorityRanker
- ✅ C1.8 EpisodicBuffer (append/list/prune/stats) — memory/episodic_buffer.jsonl
- ✅ C1.9 KnowledgeCardEditor versioning (superseded + previous_version_id)
- 🟡 Borrow: Letta (core/recall/archival), Graphiti (episodic→semantic), Mem0, NirDiamant notebooks

### ⬜ Y — Model Gateway / Local-First Router (en yüksek kaldıraç)
- ⬜ Y0 Router skeleton: L0–L6 katmanlarını ayrı, test edilebilir modüle çıkar
- ⬜ Y1 Local/rule + cache (L0 exact + L1 semantic) — aynı soruyu iki kez dışarı sorma
- ⬜ Y2 L2 memory/RAG entegrasyonu (router arkasına)
- ⬜ Y3 **LiteLLM adopt** — L4–L6 dış katman: OpenAI-uyumlu proxy, fallback chain, virtual keys, cost tracking
- ⬜ Y4 Redaction-before-external gate
- ⬜ Y5 Cost/latency/quality telemetry (per-call; "bugün şu kadar harcandı / kaçı localde çözüldü")
- ⬜ Y6 **RouteLLM** kalite-bazlı yönlendirme (ucuz model yetiyor mu? otomatik karar)
- 🟡 Borrow: LiteLLM (gateway), RouteLLM (routing), OpenRouter (strateji)

> **Model cascade adayları (kilit DEĞİL — G1 ile test edilecek):**
>
> | Katman | Aday modeller | Rol |
> |--------|---------------|-----|
> | L3 (yerel/bedava) | Qwen 2.5, Llama 3.2 (3070/3090) | basit komut, sınıflandırma |
> | L4 (ucuz iş gücü) | DeepSeek V4-Flash, Qwen, MiniMax | günlük rutin, %80 sorgu |
> | L5 (ucuz-güçlü) | Kimi K2.6, MiMo-V2.5-Pro, DeepSeek V4-Pro | agent/coding/derin akıl |
> | L6 (premium karar) | Opus 4.6/4.7/4.8, GPT-5.5, Gemini | hassas mimari, kristalleştirme kaynağı |
>
> ⚠️ Hiçbir model kendi Jarvis testimiz olmadan "ana beyin" ilan edilmez.

### ⬜ G1 — Jarvis-specific Model Benchmark Lab 🚀 (2×3090 sonrası tam güç)
- ⬜ Türkçe teknik cevap testi
- ⬜ Jarvis repo patch üretimi
- ⬜ uzun roadmap takibi
- ⬜ ESHOT rapor dili
- ⬜ memory routing güvenliği
- ⬜ persona/tone tutarlılığı
- ⬜ tool-use güvenliği + maliyet/latency
- 🟡 Test edilecekler: DeepSeek · Kimi · MiMo · Qwen · local · Claude/GPT/Gemini

### ⬜ V — Voice-First Co-working (cloud sızıntısını kapatır)
- ⬜ V0 Wake word: openWakeWord + "hey_jarvis" modeli (Wyoming)
- ⬜ V1 STT: faster-whisper (GPU) / Whisper large-v3 (Türkçe baseline)
- ⬜ **V2 Original Butler-like TTS Voice** — RVC/XTTS/Chatterbox; JARVIS *tınısı* referans, **birebir Paul Bettany klon DEĞİL**; Türkçe konuşabilen özgün ses
- ⬜ V3 Streaming response (token akışı → TTS pipeline)
- ⬜ V4 Komut/sohbet ayrımı + barge-in (Jarvis konuşurken kesebilme)
- ⬜ V5 "dinliyor / düşünüyor / konuşuyor" state göstergesi
- ⚪ V6 Vision/screen input (geç)
- 🟡 Borrow: faster-whisper, Piper, openWakeWord, Wyoming, wyoming-satellite, RVC, Chatterbox, CorentinJ RTVC

### ⬜ Z — Character & Presence Layer (filmdeki JARVIS hissi)
- ⬜ **Z0 Persona Constitution / SOUL.md** — sadık, koruyucu, ince esprili, "efendim" dengesi; "for you sir, always"
- ⬜ Z1 Presence Modes: karşılama / çalışma / yorgunluk / kriz-panik protokolleri
- ⬜ **Z2 Anti-Repetition Style Engine** — son N cevaba bakıp kalıp tekrarını kır ("anlaşıldı/tamamdır" yasağı)
- ⬜ Z3 Motivation / Progress Demo Moments (eşe/aileye gösterilebilir çıktı)
- ⬜ Z4 Late-night / Stress / Calm Protocol (gece çalışma uyarısı)
- ⚪ Z5 Sinematik HUD (özgün tasarım, geç)
- 🟡 Borrow: Khoj (persona + proaktif desen — fikir, adopte değil)

### ⬜ M — World / Reality & Maker Lab
- ⬜ M0.5 Link validation + ortak status constants (`agents/constants.py`)
- ⬜ M1 Device/scene köprüsü: M0 world model → Home Assistant + Wyoming Assist
- ⬜ M2 **Project Forge / Maker Lab**: Arduino 01 kit, ESP32, breadboard, multimeter, lehim → "bu projeyi yapmak için ne lazım?" zekâsı + fiziksel demo
- ⬜ M3 Home/IoT/scene yönetimi (oda/cihaz/sahne)
- 🟡 Borrow: Home Assistant + Wyoming + ESPHome + Node-RED

### ⬜ W — Work Intelligence (ESHOT) (ayrı alan, hobiyle karışmaz)
- ⬜ W1 Telemetri/rölanti/yakıt/ihlal analiz hattı
- ⬜ W2 Veri kaybı vs gerçek iyileşme ayrımı (kritik — yanlış pozitif riski)
- ⬜ W3 Üst yönetime sade, sayfa-sayfa executive özet
- ⬜ W4 Excel/rapor "insan eliyle yazılmış gibi" çıktı
- 🟡 Borrow: Docling, MinerU (belge sindirimi)

### ⬜ C4+ — Observability / Kara Kutu (organ sayısı artmadan önce)
- ⬜ internal event schema + LLM/tool call trace
- ⬜ error/retry/fallback log
- 🟡 Borrow: Langfuse (self-host trace), Phoenix (eval)

### ⚪ I — Vision / Perception (Vision Catalog)
- ⚪ ekran görüntüsü yorumlama, oda/kamera analizi, belge/görsel anlama
- ⚪ ileride ESP32-CAM / USB kamera
- 🟡 Borrow: MiMo-V2.5 base (multimodal), Qwen2.5-VL, Moondream

### ⬜ D — Research
- ⬜ D3–D5 Derin araştırma orkestrasyonu + decision support (D1–D2 var)
- 🟡 Borrow: SearXNG, Crawl4AI, Perplexica, Tongyi DeepResearch

---

## 7. 🟡 OSS Borrow Map (kapanmaz inceleme listesi)

> **Kural:** Deseni çal, güvenliğini alma. Çekirdeği hiçbir projeye taşıma.
> Terminal/dosya yetkilerini OpenClaw gibi geniş açma.

| Hedef | Proje | Ne incelenecek | Strateji | Durum |
|-------|-------|----------------|----------|-------|
| Çekirdek mimari | 🟡 OpenClaw | SOUL.md, skills/, workspace, heartbeat, memory_search desenleri | Desen çal, güvenlik modeli **kopyalanmaz** | ⚠️ careful security review |
| Çekirdek mimari | 🟡 Odysseus (PewDiePie) | Cookbook (donanım profili), Docker compose bundle, research pipeline | Desen çal, agent shell alma | ⚠️ hype risk, security review |
| Hafıza/ses | 🟡 isair/jarvis | local voice + memory routing (offline, "odada üçüncü kişi") | Desen incele | verified, pattern review |
| Proaktif/vision | 🟡 DawoodTouseef/J.AR.V.I.S. | voice + vision + proactive + sistem izleme (mem0/crewai/pvporcupine) | Desen incele | verified, needs code review |
| Ses pipeline | 🟡 gia-guar/JARVIS-ChatGPT | TTS/voice clone pipeline (CorentinJ RTVC) | Pipeline referansı | verified, old stack |
| Hafıza | 🟡 Letta (MemGPT) | core/recall/archival tiered model, self-editing | Pattern çal | verified, adopt candidate |
| Hafıza | 🟡 Graphiti / Mem0 | episodic→semantic çıkarım, ajan hafızası | Pattern çal | verified, adopt candidate |
| Gateway | 🟡 LiteLLM + RouteLLM | OpenAI-uyumlu proxy, fallback, cost; kalite-bazlı routing | **Adopt** (L4–L6) | verified, adopt candidate |
| Ses | 🟡 Wyoming + faster-whisper + Piper + openWakeWord | tam yerel ses pipeline | **Adopt** | verified, adopt candidate |
| Ses kalite | 🟡 Chatterbox / RVC / XTTS | yüksek kalite TTS + voice conversion | **Adopt** (V2) | verified, adopt candidate |
| Araştırma | 🟡 SearXNG + Crawl4AI + Perplexica | private arama + temiz crawl + kaynaklı cevap | **Adopt** (D) | verified, adopt candidate |
| Ev | 🟡 Home Assistant + ESPHome + Node-RED | cihaz/oda/sahne + ESP32 köprüsü | Köprü kur | verified, mature |
| Belge | 🟡 Docling / MinerU | Excel/PDF → yapısal (ESHOT) | **Adopt** (W) | verified, adopt candidate |
| Güvenlik | 🟡 LLM Guard / Rebuff | prompt injection / tool poisoning tarama | **Adopt** (H0) | verified, adopt candidate |
| Kodlama ajanı | 🟡 Aider / OpenHands / Goose | git-güvenli patch, sandbox | ⚠️ sadece sandbox | verified, sandbox only |
| Gözlemlenebilirlik | 🟡 Langfuse / Phoenix | trace + eval | **Adopt** (C4) | verified, adopt candidate |
| Model | 🟡 MiMo / DeepSeek V4 / Kimi K2.6 | cascade L4–L5 adayları | Test (G1) | ⚠️ benchmark candidate, not trusted yet |
| Türkçe | 🟡 Trendyol-LLM / CosmosGemma / Kumru + TurkishMMLU | Türkçe model + benchmark | Test (G1) | ⚠️ benchmark candidate |

---

## 8. İlerleme Tahmini

| Alan | % |
|------|---|
| Çekirdek/altyapı (A, B, C2–C4, H, M0) | ~90 |
| Memory (C1 + synthesis) | ~55 |
| Y — Gateway/Router | ~15 |
| V — Voice (yerel yığın) | ~20 |
| Z — Character/Presence | ~10 |
| M — World + Maker Lab | ~25 |
| W — Work Intelligence (ESHOT) | ~30 |
| D — Research | ~40 |
| G — Benchmark | ~0 |

**Çalışan-MVP olgunluğu: ~%70 · Tam "Reality OS" hayali: ~%38**

> ⚠️ Bu yüzdeler test sayısı/commit sayısından değil, **mimari olgunluk hissinden** türetilmiş yaklaşık/subjektif değerlerdir. Kesin metrik olarak görülmemeli.

---

## 9. Stratejik Sıra (sıra DEĞİŞMEZ)

1. ✅ **C1.6C** — Keyword Frequency Synthesizer <- **tamamlandi**
2. ✅ C1.6D -> review queue entegrasyonu <- tamamlandi
3. ✅ C1.6E -> Synthesized memory review/status + mem_store <- tamamlandi
4. ✅ C1.6E-3 -> Synthesis Promotion Gate Design <- tamamlandi
5. ✅ C1.6F → ✅ C1.6G → ✅ **C1.6H (Answer Crystallization)** ← tamamlandi
6. ⬜ Sonra secim: Z0 (persona) / Y0 (gateway) / G1 (benchmark) / D-serisi
7. ⬜ V0-V2 (yerel ses + butler voice)
8. ⬜ M1 (Home Assistant koprusu) + M2 (Maker Lab) - fiziksel demo motivasyonu
9. 🚀 G1 tam guc (2×3090 sonrasi)

> Her blok sonunda iki rapor: (1) **Teknik kapanış** — dosya/test/commit/risk,
> (2) **Büyük vizyon bağlantısı** — bu blok Jarvis'i hangi hayale yaklaştırdı.

---

## 10. Frenler (üç AI mutabakatı — unutma)

- ⚠️ OpenClaw / Odysseus çekirdeğe taşınmaz; terminal/dosya yetkisi geniş açılmaz.
- ⚠️ Model isimleri "ana beyin" diye sabitlenmez; G1 benchmark karar verir.
- ⚠️ Paul Bettany birebir klon hedef değil; özgün JARVIS *tınısı* hedef.
- ⚠️ DeepSeek/MiMo/Kimi benchmark iddiaları kendi Jarvis testimizle doğrulanmadan kabul edilmez.
- ⚠️ Hiçbir yeni model/proje heyecanı C1.6C sırasını bozmaz.

---

*Son güncelleme: 5 Haziran 2026 · Üçlü AI mutabakatı (Claude vizyon/mimari · GPT ritim/güvenlik · Gemini denge)*
*Siradaki teknik adim: [ACTIVE] C2 / Y0 Router ? hafiza zinciri tamamlandi, siradaki katman*
