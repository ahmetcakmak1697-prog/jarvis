# AÇIK KAYNAK HASAT RAPORU — JARVIS-benzeri kişisel asistanlar

**Tarih:** 2026-08-23 · **Yöntem:** GitHub REST API (yıldız/lisans/push doğrudan), repo ağacı + kaynak dosya okuma
**Kural:** *"Deseni çal, güvenliğini alma. Çekirdeği hiçbir projeye taşıma."*
**Bu rapor `docs/strategy/JARVIS_v5_REALITY_OS_ROADMAP.md` §7 OSS Borrow Map'in derinleştirilmiş hâlidir.**

---

## 0. İNCELENEN 10 PROJE

| # | Proje | Yıldız | Son push | Lisans | Dil | Canlı |
|---|---|---|---|---|---|---|
| 1 | **isair/jarvis** | 1.642 | 2026-08-17 | ⚠️ **Özel, ticari-olmayan** | Python | ✅ |
| 2 | **Odysseus** (`odysseus-dev/odysseus`) | 86.032 | 2026-08-20 | ⚠️ AGPL-3.0+ | Python | ✅ |
| 3 | **OpenClaw** | 387.229 | 2026-08-23 | MIT | TypeScript | ✅ |
| 4 | **nanobot** (HKUDS) | 47.305 | 2026-08-23 | MIT | Python | ✅ |
| 5 | **HA Assist + OHF-Voice** | 90.061 | 2026-08-23 | Apache-2.0 | Python | ✅ |
| 6 | **OVOS** (`ovos-core`) | 283 | 2026-08-17 | Apache-2.0 | Python | ✅ |
| 7 | **Khoj** | 36.675 | 2026-08-02 | ⚠️ AGPL-3.0 | Python | ✅ |
| 8 | **Letta (MemGPT)** | 24.363 | 2026-08-23 | Apache-2.0 | Python | ✅ |
| 9 | DawoodTouseef/J.AR.V.I.S. | 30 | 2026-01-15 | Apache-2.0 | Python | 🟡 durgun |
| 10 | gia-guar/JARVIS-ChatGPT | 457 | 2023-09-07 | MIT | Python | ❌ **ARŞİV** |

Sıralama yıldıza göre değil, **hasat değerine** göre.

> **DOĞRULAMA NOTU (27.08):** yukarıdaki yıldız/push değerleri **23.08 anlık**
> okumalardır ve bir alt-ajanın GitHub API sorgularından gelir; Claude Code
> bunları yeniden doğrulamadı (DANIŞMAN MODU: kendi başına web/GitHub
> taraması yapmaz). **[EMİN DEĞİLİM]** özellikle OpenClaw'ın 387.229 yıldızı
> olağandışı yüksek — adopt kararı verilmeden önce elle bakılmalı.
> **Lisans sütunu kararı etkiler; yıldız sütunu etkilemez.**

---

## 1. 🔴 SENİN AÇIK MADDELERİNE DEĞEN ÜÇ BULGU

### 1.1 `wyoming-satellite` ARŞİVLENDİ — HA/Wyoming kararının girdisi değişti
`rhasspy/wyoming-satellite` arşivli (son push 2026-01-24). README'sinin kendi notu:

> "This project is no longer maintained as it has been replaced by
> **Linux Voice Assistant** that uses the **ESPHome protocol**"

Halefi: `OHF-Voice/linux-voice-assistant` (581 yıldız, Apache-2.0, aktif).

**Ayrım önemli:** Wyoming *protokolünün kendisi* (`OHF-Voice/wyoming`, MIT, son push
2026-07-23) yaşıyor, HA'nın STT/TTS add-on'ları hâlâ onu kullanıyor. **Ölen protokol
değil, uydu implementasyonu.**

→ `LOOP0D_J0B_SAFETY_CONTRACT.md` §6'daki A/B/C seçenekleri bu bilgiyle yeniden
bakılmalı. "B: HA/Wyoming'e devret" artık uydu katmanında geçiş yaşayan bir
ekosisteme devretmek demek. **Karar Ahmet'in; bu bulgu kararı vermez, girdisini değiştirir.**

### 1.2 🆕 Piper GPL-3.0 — J0B cephesinde YENİ açık madde
`OHF-Voice/piper1-gpl` lisansı **GPL-3.0**. J0B Piper kullanıyor.

- **Subprocess olarak çağırmak** → temiz, yükümlülük doğmaz
- **Python binding'i import edip aynı süreçte linklemek** → türev eser tartışması açar

Mevcut `scripts/j0_tts_adapters.py` zaten subprocess planlıyor — yani doğru
taraftayız, ama bu **bilinçli bir karar olarak kayda geçmeli.** Phase B onayından
önce netleşmesi mantıklı.
*(Hukuki görüş değildir; GPL linkleme alanında yerleşik belirsizlik var. Mühendislik
açısından süreç sınırı en temiz yol.)*

### 1.3 Letta — geçici karar DOĞRULANDI
Bulgular `LOOP0D` §7'deki *"Letta runtime onaylı değil, yalnızca mimari desen"*
kararını **destekliyor**:
- Runtime = Postgres + pgvector + REST sunucu + agent harness → tek-PC 1.5s hedefi
  için orantısız
- Kavram isimleri sürümler arası kayıyor (memory blocks → MemFS → "agent dreaming"),
  doküman geride, bazı sayfalar 404
- Buna karşılık **üç katmanlı hafıza ontolojisi ve RRF hibrit arama gerçekten değerli**

→ Öneri: geçici kararı **kalıcı** yap, `JARVIS_HARVEST_MAP.md` REJECT tablosunu tek
doğruluk kaynağı ilan et, roadmap'teki "adopt candidate" etiketini
**"pattern reference"** olarak düzelt. (Bkz. `ROADMAP_AUDIT.md` §2 — çelişki zaten yoktu.)

---

## 2. PROJE PROJE — EN DEĞERLİ HASATLAR

### 2.1 isair/jarvis — **en yüksek hasat değeri**
⚠️ Lisans: "Jarvis AI Assistant License" — ticari kullanım yasak + share-alike.
**Kod alınamaz, desen okunur.**

**Al:**
- **`llm/tiers.py` (1,7 KB)** — en küçük, en yüksek getirili dosya.
  `Tier.FAST` (~2B, sürekli RAM'de, sınıflandırma yapar) + `Tier.CHAT` (yanıt üretir).
  `fast_model` boşsa chat'e düşer. VRAM tablosu **ikisi birlikte yüklü** varsayımıyla.
- **`memory/recall_gate.py` (4 KB) + spec'i** — hafıza geri-çağırmasını ne zaman
  ATLAYACAĞINI belirler. Kural: **her ikisi de** doğruysa atla — (a) sıcak pencerede
  en az bir tool mesajı var, (b) sorgu kelimelerinin **≥%50'si** sıcak pencere
  transkriptiyle örtüşüyor. Örtüşme yönlü: `|kesişim| / |sorgu_kelimeleri|`.
  **Herhangi bir istisnada fail-open** → kapı asla servisi bozmaz.
  *Kapı bir optimizasyondur, güvenlik sınırı değildir — ikisini karıştırma.*
- **3 durumlu dinleme makinesi:** `WakeWord → IntentJudge → DuringTTS → HotWindow`.
  Ayrı wake-word modeli **yok** — transkript tamponunda fuzzy eşleşme +
  **alias normalizasyonu** (yanlış duyulan varyantlar birincil isme çevrilir).
  → Türkçe'de "Jarvis" çok şekilde yanlış transkribe edilir; alias listesi 20 satırlık iş.
- **4 katmanlı eko bastırma:** `rapidfuzz partial_ratio ≥ 70` → LLM judge
  (`last_tts_text` bağlamıyla) → zaman damgası → kelime sayısı koruması.
  Zamanlar: eko toleransı 0,3s · hot window 3s · judge timeout 6s · keep-alive 30dk.
  **TTS sırasında "dur/sus" tespiti LLM ÇAĞIRMADAN, saf metinle.**
- **Erken geri bildirim:** wake görülür görülmez bip + durum göstergesi, judge'ı bekleme.
  Takas: judge reddederse ara sıra yanlış bip. Kazanç: algılanan gecikmede ciddi düşüş.
  **1,5s hedefi için kritik.**
- **`.spec.md` disiplini** — her modülün yanında davranış sözleşmesi
  (`reply.spec.md` 42 KB, `listening.spec.md` 26 KB). Pazarlama değil, sözleşme.
- **`EVALS.md`** — 145+ davranış testi, 48 intent-judge iddiası, 11 hafıza senaryosu;
  sonuçlar **model başına yan yana**. Adversarial kategori dahil:
  *"kullanıcı tercihi (USER) vs sistem direktifi (DIRECTIVES)"* →
  approval-queue tasarımını test etmek için doğrudan geçerli.

**Alma:** kodu (lisans) · 120 KB'lık tek-dosya modüller (`listener.py` 128 KB,
`reply/engine.py` 123 KB) · UPnP router sorgusu + OpenDNS lookup (yerel-önce ilkesine aykırı).

### 2.2 Odysseus — desen gerçek, runtime alınmaz
⚠️ AGPL-3.0-or-later. **Kod alınamaz.**

**Al:**
- **`services/hwfit/` VRAM uyum motoru** (formül, kod değil). Profil sözlüğü:
  `key, label, quant, n_gpu_layers, n_cpu_moe, cache_type, ctx, est_vram_gb, fits, offloads, note`.
  Eşikler: vision +**1,1 GB** encoder, vision-olmayan +**0,4 GB** runtime tamponu,
  min kullanılabilir bütçe **1,0 GB**, runtime tamponu **0,6 GB**, ctx tabanı **8192**,
  metadata yoksa ctx tavanı **131072**. **Sabit VRAM sınıfı yok** — kademeler
  kuantizasyon merdiveninden dinamik çıkıyor. → `ModelRegistry`'ye girer.
- **`core/log_safety.py::redact_url`** (~30 satır, yeniden yazılabilir):
  scheme/host/port/path **korunur**; userinfo (`user:pass@`), query (API anahtarları),
  fragment **atılır**. IPv6 yeniden köşelenir. Geçersizse `"<endpoint>"`.
  → Log hem sır sızdırmaz hem debug'da kullanışlı kalır.
- **`docker-compose.yml` üçlüsü** (konfigürasyon kararı, AGPL bulaşmaz):
  tüm portlar `${APP_BIND:-127.0.0.1}` · imajlar tam sürüm-pinli
  (`searxng:2026.5.31-7159b8aed`) · `cap_drop` + sadece `CHOWN,SETGID,SETUID,DAC_OVERRIDE` ·
  gerçek healthcheck · telemetri kapalı.
- **`research_handler.py` araştırma boru hattı iskeleti:** maks **8 tur** + zaman
  bütçesi → her turda LLM bulguları analiz edip takip sorgusu planlar → küme-tabanlı
  dedup + `is_low_quality()` filtresi → sentez. **Fallback zinciri:**
  `DeepResearcher` → `ResearchOrchestrator` → `comprehensive_web_search()`.
  Yaşam döngüsü: `get_status()` / `cancel_research()` / `get_result()`.
  → "Tur bütçesi + zaman bütçesi + iptal + kademeli fallback" = cost-ledger kapısının iskeleti.
- **`THREAT_MODEL.md` formatı** — özellikle **"Bilinen açıklar"** bölümünün varlığı.
  Kendi 4 açığını sayıyor: shell sandbox yok, `base_url` üzerinden SSRF, arama modülü
  çoğaltması, kaba token kapsamları.

**Alma:** kod (AGPL) · **sandbox'sız shell aracı** (kendi threat model'i kabul ediyor) ·
`base_url`'i kullanıcı girdisinden almak (kendi SSRF açığı) · 119 KB tek-dosya MCP sunucusu.

**Hype notu:** 86.032 yıldıza karşı **598 fork** = **%0,7**. Sağlıklı geliştirici
projesinde %5-10 olur (OpenClaw %21, nanobot %18, Khoj %6,5). Yıldızlar koda
dokunmayan izleyiciden. **Ama kod gerçek** — `hwfit/fit.py` 37 KB ve VRAM matematiği ciddi.
→ **Yıldız şişkin, mühendislik şişkin değil. DESEN al, RUNTIME alma.**

### 2.3 OpenClaw — desen zengini, güvenlik modeli ders kitabı örneği (olumsuz)
MIT. Fork/yıldız %21 = gerçek benimseme.

**Al:**
- **`SOUL.md` / `AGENTS.md` / `USER.md` rol ayrımı.**
  **SOUL = "kimsin?"** (kişilik, değerler, ton, sınırlar) ·
  **AGENTS = "ne yaparsın, nasıl?"** (prosedür) · **USER = kullanıcı**.
  → Senin `CLAUDE.md`'n şu an **üçünü birden** yapıyor (kimlik + prosedür + repo
  durumu + danışman modu). Ayırmak, kimliği bozmadan prosedürü güncellemeyi sağlar.
- **Oturum sözleşmesi:** *"You are a fresh instance each session; continuity lives in
  these files"* → senin PUSULA'n bunun daha doğru çözümü (dosyaya yazmak yerine
  repo'yu **canlı okumak**), ama dosya şeması yine de faydalı.
- **"Existing solutions preflight"** bölümünün prompt'a yazılma biçimi
  → senin adopt-over-build kuralının aynısı, **bağımsız olarak aynı sonuca varılmış.**
- `memory/YYYY-MM-DD.md` günlük + `MEMORY.md` uzun vadeli iki katman.
- **`HEARTBEAT_OK` sessiz-dönüş protokolü** — proaktif ajanın "söyleyecek bir şeyim
  yok" diyebilmesi için sentinel; teslimi bastırır, boş listede koşuyu atlar.
  ⚠️ **Scheduler park edilmiş cephe — kayda geçer, uygulanmaz.**

**Alma — güvenlik modelinin hiçbir parçası:**
- **CVE-2026-25253** — tek tıkla RCE. Kök neden: yerel sunucu **WebSocket origin
  başlığını doğrulamıyordu** → ziyaret edilen herhangi bir site çalışan ajana bağlanabiliyordu.
- **"ClawJacked"** (Oasis Security) — dolaylı prompt injection; kötü niyetli site
  yerel örneği ele geçirip **ajanın kendi otonomisini kullanarak** veri sızdırıyor.
- SecurityScorecard STRIKE: 82 ülkede **135.000+ IP**, **12.812'si RCE'ye açık**.
  Tarama HN duyurusuyla **aynı gün** başlamış. Yama: 2026.2.26.
- ⚠️ **`security/` dizini çalışma zamanı güvenliği DEĞİL** — içinde sadece README +
  `opengrep/`. Kendi belgesi kabul ediyor: statik kurallar PR'da regresyon duvarı,
  *"runtime state, product policy, or external data"* gerektiren durumlarda uygun değil.
  **Bir projede `security/` klasörü görmek onun güvenli olduğu anlamına gelmiyor.**
- Çok-kanallı gateway mimarisi (= senin park edilmiş Telegram cephen; krizin saldırı
  yüzeyi de oydu).

### 2.4 nanobot — küçük çekirdek + gerçek sandbox
MIT, Python 3.11+, Ollama/vLLM uyumlu.

**Al:**
- **tmpfs ile secret maskeleme.** bwrap sandbox'ta: workspace RW · media RO ·
  sistem RO · **config + API anahtarları (`~/.nanobot/config.json`) tmpfs ile maskelenip
  GİZLENİYOR.** Ajanın çalıştırdığı shell komutu kendi config'ini **göremiyor**.
  → Senin *".env okunmaz"* kuralın şu an bir **kural**; bu onu **mekanizmaya** çevirir.
  **Kural ihlal edilebilir, mount edilmemiş dosya okunamaz.**
- **`allowFrom` boş = herkesi REDDET.** v0.1.4.post3'e kadar boş liste "herkese izin"
  demekti; post4'te tersine çevrildi ve sürüm numarasıyla belgelendi.
- **`core_agent_lines.sh`** — çekirdek satır sayısını ölçen script.
  → "Simplicity First" ilkesinin otomatik kontrolü.
- **`SECURITY.md`'deki "kapsam dışı" listesinin biçimi** — neyin korunmadığını yazmak,
  korunanı yazmaktan faydalı.

**Alma:** `docker-compose.bwrap.yml`'i olduğu gibi — container içinde bwrap kurabilmek
için container'ın **kendi** izolasyonu zayıflatılıyor: `cap_add: SYS_ADMIN`,
`apparmor=unconfined`, `seccomp=unconfined`. Gerekçesi dosyada **yok**.
Ayrıca: rate limiting yok, audit trail yok, veri düz metin.

### 2.5 HA Assist + OHF-Voice — tek ölçülmüş gecikme kaynağı
**Al:**
- **Protokol sınırı = süreç sınırı.** STT/TTS/wake ayrı süreç, ağ protokolüyle konuşur.
  Piper'ı Whisper'dan bağımsız değiştirebilirsin; biri çökerse diğeri gitmez.
  **Ayrıca GPL sınırını süreç sınırında tutar** (bkz. §1.2).
- **Ölçülmüş rakamlar** (yığındaki diğer 9 projenin hiçbiri uçtan uca gecikme vermiyor):
  Speech-to-Phrase HA Green/Pi4'te **&lt;1 sn** · Whisper Pi4'te **~8 sn** ·
  Piper **1,6 sn ses / 1 sn** (gerçek-zamandan hızlı, CPU'da).
- **İki-yollu STT:** kapalı komut kümesi için hızlı özel model + açık uçlu için genel model.
  → "Hey Jarvis, nerede kaldık?" hızlı yola; serbest sorular yavaş yola.
  Bu, iki-kademeli LLM mimarisinin ses tarafındaki karşılığı.

**Alma:** HA Core'u asistan çekirdeği yapmak (devasa platform + entegrasyon yüzeyi) ·
`wyoming-satellite`'i yeni iş için temel almak (arşivli) · Piper'ı süreç-içi linklemek.

### 2.6 OVOS — deterministik yönlendirmenin referans implementasyonu
283 yıldız ama **bu bir asistan uygulaması değil, platform çekirdeği** — ekosistem
onlarca repoya dağılmış. Yıldıza bakıp elemek hata olur.

**Al — pipeline sıralaması, doğrudan:**
```
stop_high, converse, ocp_high, padatious_high, adapt_high,
persona_high, ocp_medium, fallback_high, stop_medium,
adapt_medium, padatious_medium, adapt_low, common_qa,
fallback_medium, persona_low, fallback_low
```
Eşikler: **Adapt** 0,65 / 0,45 / 0,25 · **Padatious** 0,95 / 0,8 / 0,5

Mantık: liste **sırayla** denenir, **ilk eşleşen kazanır, LLM'e sorulmaz.**

Üç kritik detay:
1. **`stop_high` listenin EN BAŞINDA** → *"human override her katmandan üstün"*
   ilkesinin mimari ifadesi, tek satır.
2. **Aynı matcher birden çok eşikte tekrar ediyor** (`adapt_high` erken, `adapt_low` geç)
   → "hangi matcher" ve "ne kadar emin" **iki bağımsız eksen**, çarpımları sıraya diziliyor.
3. **Padatious eşikleri Adapt'tan çok yüksek** (0,95 vs 0,65) → farklı motorların güven
   skorları **aynı ölçekte değil**. Senin *"vector skor girdi, karar değil"* kuralının
   somut gerekçesi bu.

→ **Aşama adı = `route_reason`.** "confidence + route_reason logla" gereksinimi bedavaya çözülüyor.

**Alma:** message bus / skill runtime (LLM-öncesi çağdan, ağır) ·
Padatious/Adapt'ı Türkçe için olduğu gibi kullanmak (morfoloji için hazır değil).

### 2.7 Letta — hafıza ontolojisi
**Al:** üç katman (**core** = bağlamda, ajan `core_memory_append/replace` ile doğrudan
yazar · **recall** = aranabilir geçmiş · **archival** = tool ile sorgulanır) ·
`human` + `persona` blok ayrımı (**OpenClaw'ın `USER.md`+`SOUL.md`'siyle bağımsız
yakınsama — sınırın doğru olduğuna işaret**) · **RRF ile hibrit arama** (vektör + tam
metin füzyonu) · **MemFS git-destekli hafıza** (her değişiklik commit → hafıza yazımı = PR,
onay = merge).

**Alma:** runtime (§1.3) · **sleep-time compute'u olduğu gibi** — otonom hafıza yazımı,
kaynağın güvenini **hiç sorgulamıyor**, senin güvenlik modelinle doğrudan çelişiyor.

### 2.8–2.10 Kısa
- **Khoj:** Automation veri modeli `(sorgu, cron, teslim kanalı, son çalışma, sonuç)`
  → **park edilmiş cephe, kayda geçer.** **PostgreSQL + pgvector tek-veritabanı kararı**
  (ayrı vektör DB yok, operasyonel yükü yarıya indirir) → doğrudan uygulanabilir.
  ⚠️ AGPL, kod alınmaz. Ses yok.
- **DawoodTouseef:** tek harvest — **farklı algı kanalları için farklı sabit örnekleme
  periyodu** (kamera 60 sn / ekran 120 sn) + eşik tetikleme. OpenClaw'ın 30 dk LLM
  heartbeat'inden hem ucuz hem öngörülebilir. Gerisi: 0 issue = "kimse bakmıyor",
  izin/gizlilik notu yok, bulut LLM'e sürekli kamera besliyor, `pvporcupine` ticari lisans.
- **gia-guar:** **kod olarak hiçbir şey** (arşiv, 2023). Ders olarak bir şey:
  457 yıldız aldı ve **öldü** — sebebi bakımsızlık değil, temel tercihlerin
  (bulut API + Tacotron) altındaki zeminin kayması. **Senin ModelRegistry kararın
  (*"model adı koda gömülmez"*) tam olarak bu ölüm biçimine karşı sigorta.**

---

## 3. ⭐ BİRLEŞİK MİMARİ — hangi işlev, hangi projeden

| Katman | İşlev | Desen | Kaynak |
|---|---|---|---|
| **Ses girişi** | Dinleme durum makinesi | 3 durum + eko toleransı 0,3s, hot window 3s | isair |
| | Wake tespiti | Ayrı model yok; fuzzy metin + **alias normalizasyonu** | isair |
| | Eko bastırma | 4 katman, `partial_ratio ≥ 70` ilk | isair |
| | Barge-in / dur | **LLM'siz saf metin**; `stop_high` en üstte | isair + OVOS |
| | Erken geri bildirim | Wake görülünce bip, judge'ı bekleme | isair |
| **STT** | İki-yollu | Kapalı komut &lt;1s + açık uçlu Whisper | HA |
| **Yönlendirme** | Deterministik router | Sıralı `<matcher>_<tier>`, ilk eşleşen kazanır, aşama adı = `route_reason` | OVOS |
| | Güven kalibrasyonu | Her matcher kendi eşiğiyle | OVOS |
| | Model kademeleri | `Tier.FAST` (hep yüklü) + `Tier.CHAT` | isair |
| | Model seçimi | VRAM bütçesi − headroom → kuantizasyon merdiveni | Odysseus hwfit |
| **Hafıza** | Katman ontolojisi | core / recall / archival | Letta |
| | Kimlik blokları | `human` + `persona` = `USER.md` + `SOUL.md` | Letta + OpenClaw |
| | Geri-çağırma kapısı | tool mesajı **ve** ≥%50 örtüşme → atla; **fail-open** | isair |
| | Arama | Vektör + tam metin, **RRF** füzyonu | Letta |
| | Depolama | Tek DB: PostgreSQL + pgvector | Khoj + Letta |
| | Denetlenebilirlik | Git-destekli hafıza, her değişiklik commit | Letta MemFS |
| | Günlük katman | `memory/YYYY-MM-DD.md` + `MEMORY.md` | OpenClaw |
| **Kimlik** | Rol ayrımı | SOUL / AGENTS / USER | OpenClaw |
| | Build-öncesi | "Existing solutions preflight" | OpenClaw |
| **Araştırma** | Derin araştırma | 8 tur + zaman bütçesi + dedup + fallback + `cancel()` | Odysseus |
| **Güvenlik** | Log redaksiyonu | `redact_url` | Odysseus |
| | Secret erişimi | **tmpfs maskesi** (kural → mekanizma) | nanobot |
| | Erişim varsayılanı | Boş allow-list = **reddet** | nanobot |
| | Ağ varsayılanı | `127.0.0.1` bind + sürüm-pin + `cap_drop` | Odysseus |
| | Tehdit belgesi | Kapsam dışı + **bilinen açıklar** | Odysseus |
| **Ses çıkışı** | TTS | Piper **ayrı süreç** (GPL sınırı = süreç sınırı) | OHF-Voice |
| **Süreç** | Spec disiplini | Modül yanında `X.spec.md` | isair |
| | Eval | Kategori bazlı suite, model başına tablo, adversarial dahil | isair |
| | Sadelik denetimi | Çekirdek satır sayacı | nanobot |

**Sende ZATEN VAR (yeniden inşa etme):** cascade · cost-ledger kapısı · iki-eksenli
güvenlik · approval queue · ModelRegistry · `schema_version` · append-only BLACKBOX ·
human override.

**GERÇEKTEN YENİ:** recall_gate · OVOS pipeline sıralaması · `tiers.py` ·
hwfit formülü · eko bastırma katmanları · tmpfs secret maskesi · `.spec.md` disiplini ·
eval taksonomisi.

---

## 4. ÇELİŞEN TASARIM KARARLARI + ÖNERİ

### Çelişki 1 — Deterministik pipeline mi, LLM orchestrator mı?
| Yaklaşım | Kimde |
|---|---|
| Deterministik sıralı pipeline | OVOS |
| LLM-in-the-loop orchestrator | Odysseus, Khoj |
| Tek küçük agent loop | nanobot, OpenClaw |
| **Hibrit** | **isair/jarvis** |

**→ Hibrit, OVOS'un sıralama biçimiyle.** Üç gerekçe:
1. **Anayasa uyumu** — saf LLM orchestrator'da kararın nedeni prompt içinde kaybolur,
   `route_reason` uydurma olur.
2. **Gecikme** — her LLM turu 200–800 ms. "Dur" için LLM'e sormak bütçeyi bitirir.
3. **Denetlenebilirlik** — OVOS'ta karar bir string (`padatious_high`), test edilir;
   orchestrator'da karar bir prompt cevabı, edilemez.

*Karşı argüman, dürüstçe:* deterministik pipeline yeni niyet eklemeyi pahalılaştırır.
Ama senin kullanım alanın dar ve iyi tanımlı — genelleşme ihtiyacı düşük,
denetlenebilirlik ihtiyacı yüksek. **Takas senin lehine.**

### Çelişki 2 — Hafıza: markdown mı, veritabanı mı?
**→ Katmanlı hibrit, sınırı DEĞİŞİM SIKLIĞINA göre çiz:**
- **Kimlik + kurallar** (nadir değişir, insan yazar, denetlenmeli) → **markdown, git'li**
- **Olgular + konuşma geçmişi** (sık değişir, makine yazar, aranmalı) → **PostgreSQL + pgvector, RRF**
- **Arasında** → recall_gate

⭐ **Bu ayrım aynı zamanda GÜVENLİK sınırıdır:** markdown katman insan-yazımlı ve
güvenilir; DB katman makine-yazımlı ve untrusted içerik barındırabilir.
**Senin approval queue'n tam olarak ikisi arasındaki kapıdır.**
*(Bu, tabloya bakınca çıkan ve hiçbir projenin açıkça ifade etmediği bir şey.)*

### Çelişki 3 — Sandbox: yok / bwrap / statik analiz
Üçü **aynı problemi çözmüyor**: Odysseus dürüst ama korumasız · nanobot koruyor ama
başka bir sınırı zayıflatarak · OpenClaw'ın `security/`'si **hiçbir çalışma zamanı
koruması sağlamıyor** (135.000 açık örnek bunun sonucu).

**→ Senin için doğru cevap dördüncüsü: YETKİYİ HİÇ VERMEMEK.**
Anayasan zaten `git add -A` yasağı, insan-onaylı push, `--dangerously-*` yasağı içeriyor.
**Sandbox'tan daha güçlü konum** — sandbox yetkisi olan sürecin hasarını sınırlar;
yetki vermemek hasarı hiç doğurmaz.
(nanobot'un tmpfs maskesi yine de alınmalı: sandbox değil, **kuralı mekanizmaya çeviren** katman.)

### Çelişki 4 — Proaktiflik
Cephe **park edilmiş**. Desenler kayda geçer. Cephe açılırsa sıralama:
**sabit periyot + eşik** (en ucuz, en öngörülebilir) → cron → LLM heartbeat (en pahalı).

### Çelişki 5 — Ses: süreç-içi mi, protokol arkasında mı?
**→ TTS'i bugün subprocess olarak çağır, arayüzü protokol-değiştirilebilir tut.**
İki gerekçe: (1) **Piper GPL-3.0, süreç sınırı = lisans sınırı**; (2) J2/J5 ayrı donanım
cephesi zaten haritada — bugün süreç-içi hızlı yol yazıp yarın protokol eklemek,
bugün protokol yazıp asla optimize etmemekten az iş.

---

## 5. 🏆 HİÇBİRİNİN ÇÖZMEDİĞİ BOŞLUKLAR — senin önde olduğun yerler

| # | Boşluk | Durum |
|---|---|---|
| 1 | **Türkçe** | 10 projenin **hiçbirinde** Türkçe'ye özel yol yok. isair'in spec'i *"non-English queries skip this step"* diyor — çözüm değil, **geri çekilme**. Morfolojiye ve `"I".lower()` tuzağına kimse değinmiyor. **`CLAUDE.md` §6 bunu zaten çözmüş.** |
| 2 | **Uçtan uca gecikme bütçesi** | Hiçbiri "wake→ilk ses X ms" bütçesi tanımlayıp CI'da ölçmüyor. isair'in 145+ testlik suite'inde bile **gecikme metriği yok**. → Bunu **sen yazmalısın**: `wake → ilk_ses_ms`, bileşen başına böl (STT/router/TTFT/TTS ilk chunk), her koşuda tablola. |
| 3 | **Maliyet defteri** | Hiçbirinde harcama tavanı + kapı yok. nanobot rate limiting'in olmadığını kabul ediyor. **Senin cost-ledger'ın literatürün önünde.** |
| 4 | **İki eksenli güvenlik** | Hepsi tek eksenli (rol / kanal / statik kural). **"İçerik nereden geldi × veri nereye gidebilir" matrisi hiçbirinde yok.** |
| 5 | **Untrusted → kalıcı hafıza** | Alanın en ciddi çözülmemiş problemi. Odysseus dış içeriği prompt'ta sarıyor ama **hafızaya yazarken kapı yok**. Letta'nın sleep-time ajanı güveni **hiç sorgulamıyor**. ClawJacked tam olarak buydu. **Senin approval queue kuralın 10 projede karşılıksız.** |
| 6 | **Repo durumu farkındalığı** | Hiçbiri kendi projesinin canlı durumunu bilmiyor. OpenClaw'ın çözümü dosyaya yazmak → bayatlama problemi. **Senin PUSULA'n (`git log` + BLACKBOX canlı okuma) yapısal olarak daha doğru.** |
| 7 | **Kill switch / geri alma** | Hiçbirinde insan override birincil tasarım öğesi değil. OpenClaw krizinde 135.000 örnek vardı ve kullanıcının elinde "durdur" düğmesi yoktu. nanobot audit trail'in yokluğunu kabul ediyor. **Senin "her an dur/iptal/unut" ilken alanda karşılıksız.** |
| 8 | **Lisans hijyeni** | Aşağıdaki tablo |

### Lisans tablosu — en değerli üç proje kod olarak ALINAMAZ
| Proje | Lisans | Risk |
|---|---|---|
| isair/jarvis | Özel non-commercial + share-alike | ❌ **Kod alınamaz** |
| Odysseus | AGPL-3.0+ | ❌ **Kod alınamaz** |
| Khoj | AGPL-3.0 | ❌ **Kod alınamaz** |
| Piper | GPL-3.0 | ⚠️ Süreç olarak çağır, **linkleme** |
| Open WebUI | BSD-3 + marka kısıtı | ✅ kişisel kullanımda sorun yok |
| OpenClaw, nanobot, Letta, OVOS, HA | MIT / Apache-2.0 | ✅ temiz |

**→ En yüksek desen değerine sahip üç proje kod olarak alınamaz. Bu, *"Deseni çal,
güvenliğini alma"* kuralının hukuki karşılığı ve kuralın ne kadar yerinde olduğunun kanıtı.**

---

## 6. DEĞERLENDİRİLDİ, ELENDİ
Open WebUI (arayüz, mimari değil; marka kısıtı) · AnythingLLM (JS, Khoj ile örtüşür) ·
Onyx (kurumsal, ağır) · LibreChat (yerel-önce değil) · Leon (OVOS aynı deseni daha
olgun sunuyor) · Dify (kurumsal workflow) · n8n (fair-code; park edilmiş cepheye denk) ·
mem0 (Letta'nın modeli daha net; **yakın takip adayı**) ·
**pipecat** (Python/BSD, teknik olarak güçlü — bulut ses servisleri etrafında
tasarlanmış; **ses gecikmesi cephesi açılınca yeniden bak**) · LiveKit Agents (WebRTC,
tek makinede fazla) · airi (VTuber companion, hedef örtüşmüyor).

---

## 7. KAYNAKLAR
GitHub API sorguları (2026-08-23) + repo ağacı/kaynak okuma. Ana URL'ler:
`isair/jarvis` · `odysseus-dev/odysseus` · `openclaw/openclaw` · `HKUDS/nanobot` ·
`home-assistant/core` · `OHF-Voice/{piper1-gpl,wyoming,linux-voice-assistant}` ·
`rhasspy/wyoming-satellite` · `dscripka/openWakeWord` · `OpenVoiceOS/ovos-core` ·
`khoj-ai/khoj` · `letta-ai/letta` · `DawoodTouseef/J.AR.V.I.S.` · `gia-guar/JARVIS-ChatGPT`

Güvenlik olayı: IBM X-Force · Giskard · SecurityScorecard STRIKE · Oasis Security.

**[DOĞRULANMADI]** işaretli olanlar: Odysseus'un MIT→AGPL geçişi · "48 saatte SSRF +
auth bypass" · "vibecoded" eleştirisi (çoklu kaynakta tutarlı ama birincil doğrulama yok) ·
bir ikincil kaynağın Odysseus için verdiği "10.000 fork" rakamı (GitHub API 598 diyor;
API esas alındı).

**Bu raporda hiçbir kod yazılmadı, hiçbir dosya değiştirilmedi, hiçbir öneri uygulanmadı.**
