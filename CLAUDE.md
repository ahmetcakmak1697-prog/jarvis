# CLAUDE.md — JARVIS Kodlama Anayasası (AI eş-geliştirici kuralları)

> Bu repoda kod üreten her AI (Claude / GPT / Gemini / Claude Code) bu kurallara uyar.
> Kaynak: Karpathy 4 ilke + JARVIS v5.9 Konsolidasyon disiplini.
> "Heyecan vizyonu besler; projeyi sıralı mühendislik bitirir."

---

## 1. Think Before Coding (önce düşün)
- Varsayımları **açıkça söyle**; emin değilsen sor, sessizce tahmin etme.
- Belirsizlik varsa birden çok yorumu sun, birini sessizce seçme.
- Daha basit bir yol varsa **itiraz et**, push back yap.
- Kafan karıştıysa dur, neyin belirsiz olduğunu adlandır.

## 2. Simplicity First (önce sadelik)
- Problemi çözen **minimum kod**. Spekülatif hiçbir şey yok.
- İstenmeyen özellik / tek kullanımlık soyutlama / "ileride lazım olur" esnekliği YOK.
- İmkânsız senaryolar için error handling yazma.
- "Kıdemli mühendis buna 'fazla karmaşık' der mi?" → evetse sadeleştir. (No rewrite; v5 korunur.)

## 3. Surgical Changes (cerrahi değişiklik)
- Sadece dokunman gerekeni değiştir. Komşu kodu/yorumu/formatı "iyileştirme".
- Bozuk olmayanı refactor etme; mevcut stile uy.
- Kendi değişikliğinin yarattığı orphan import/değişkeni temizle; **önceden var olan dead code'a dokunma** (gör, söyle, silme).
- Her değişen satır doğrudan isteğe izlenebilmeli.

## 4. Goal-Driven Execution (hedef-odaklı, test-first)
- "Düzelt" değil → **"hatayı üreten testi yaz, sonra geçir."**
- "Doğrulama ekle" değil → "geçersiz girdi testleri yaz, sonra geçir."
- Çok adımlı işte kısa plan: `1. adım → doğrula: kontrol`.
- Kuvvetli başarı kriteri = bağımsız loop. Zayıf kriter ("çalışsın") = sürekli soru.

---

## 5. JARVIS'e özel — byte-safe patch disiplini (ACI İLE ÖĞRENİLDİ)
- **PowerShell paste Türkçe karakteri bozar** (ş→?, ı→?) + BOM ekler.
- Güvenli patch: `@' ... '@ | python` here-string; içinde `"""` kullan, **asla `'''`** (here-string'i kapatır).
- Türkçe içerik koda girecekse: `\uXXXX` escape ile yaz **veya** dosyayı indirilebilir patch olarak ver (paste etme).
- Her patch **idempotent**: yazmadan önce `if "ANCHOR" in text: raise SystemExit(...)`.
- Patch sonrası **mutlaka doğrula**: `py_compile` + `git status`/`git diff` + import smoke. "Başarılı" deme, **gör.**
- No overwrite, patch only. Anchor-based, fail-loud.

## 6. Türkçe gotcha'ları (sessiz bug kaynağı)
- `"İ".lower()` → `'i̇'` (combining dot!), `"I".lower()` → `'i'` (Türkçe'de `'ı'` olmalı). Düz `.lower()` ile keyword eşleştirme KAÇIRIR.
- Çözüm: eşleştirmede ASCII-fold uygula (İ/I→i, ş→s, ğ→g, ü→u, ö→o, ç→c, ı→i) — hem keyword hem metin aynı şekilde fold'lanır.
- Türkçe sondan eklemeli: "rapor" → "raporu/raporları". Exact match değil **substring/contains** kullan (kısa köklerde false-positive'e dikkat).

## 7. Mimari anayasa (v5.9 — kısa)
- Yerel-önce cascade: cache → RAG → local LLM → (sufficiency) → cost-ledger kapısı → external. Redaction'dan sonra.
- İki eksenli güvenlik: veri sınıfı (ne dışarı çıkar) × güven (içerik nereden). **Untrusted içerik asla otomatik kalıcı hafıza olmaz → approval queue.**
- Deterministik routing = güvenlik özelliği. Vector skor *girdi*, karar değil. Router kararı `confidence` + `route_reason` ile C4'e yazılır.
- **Human override her katmandan üstün:** kullanıcı her an dur/iptal/unut/yerel-kal diyebilir.
- ESHOT: pandas hesaplar, LLM anlatır; kurallar Rules.json'da.
- Model adı koda gömülmez → ModelRegistry. Her veri dosyasında `schema_version`.
- Her blok: küçük patch → test → smoke → git clean → commit → çift review. DoD ile kapat.

---
*Bu dosya repoda `CLAUDE.md` (kök) olarak durur. Cursor için `.cursor/rules/`'a da kopyalanabilir.*

---

## 8. PUSULA

JARVIS'in tek cümlelik hedefi: Ahmet'in "Hey Jarvis, nerede kaldık?" sorusuna
~1.5 saniye içinde, Türkçe sesli ve **repo'nun o anki gerçek durumunu**
yansıtan bir yanıt vermek — uydurma değil, canlı.

His-testi: cevap doğru mu diye anlamak için "bu, repo'yu şu an açıp
`git log` + son BLACKBOX event'ine bakan biri gibi mi konuşuyor?" sorusu
sorulur. Değilse yanıt yanlıştır.

## 9. DEĞİŞMEZ KURALLAR

- `git add -A` yasak; yalnız isimli dosya ekle.
- Push yalnız insan (Ahmet) onayıyla.
- `--dangerously-*` bayrakları (`--dangerously-skip-permissions`,
  `--dangerously-bypass-approvals-and-sandbox`, vb.) kalıcı yasak.
- `.env` / secret dosyalarına dokunulmaz, okunmaz, loglanmaz.
- Auto-fix retry **NOT APPROVED** — bir kontrol BLOCKER/CONCERN verirse
  otomatik düzeltip tekrar denenmez, Ahmet'e gider.
- Otomatik sıradaki-işe-geçiş yok — her adım tamamlandığında durulur,
  bir sonraki adım insan onayı bekler.
- Park edilmiş cepheler (AUTO / orchestrator / scheduler / Telegram
  auto-send) hiçbir isimle, hiçbir gerekçeyle yeniden açılmaz.
- Adopt-over-build: yeni bir şey yazmadan önce olgun açık-kaynak/mevcut
  çözüm var mı diye sorulur (bkz. `automation/LOOP0D_J0B_SAFETY_CONTRACT.md`
  §6 — HA/Wyoming adopt-vs-build örneği).

## 10. MEVCUT DURUM

*(bu bölüm repo'dan çıkarılmıştır: `git log`, `roadmap_state.json`,
`automation/BLACKBOX.jsonl`, `automation/AUTONOMY_LOG.md`)*

- **Aktif branch:** `auto/opencode-deepseek`
- **Son commit:** `0537895b6` — "feat(voice): add safe Piper Phase A command
  planning" (2026-07-13)
- **Aktif cephe:** J0 ses hattı (J0B/Piper) — `docs/THIRD_PARTY_VOICE.md` ve
  `scripts/j0_tts_adapters.py` altında, LOOP-0 zinciri disipliniyle
  ilerliyor.
- **BLACKBOX son durum** (`automation/BLACKBOX.jsonl`, append-only, 6
  event):
  - `sequence=6`, `sprint_id=LOOP0E`,
    `task_id=LOOP0E_J0B_PHASE_A_CORRECTION_VERIFICATION`, `status=PASS`.
  - Bu event, Codex'in `sequence=5`'te işaretlediği iki sorunun (NaN
    timeout false-positive'i ve Phase B manuel komut şablonundaki
    off-by-one argüman eşlemesi) düzeltmesinin doğrulamasıdır.
  - `sequence=5` (CONCERN) silinmedi/yeniden yazılmadı — append-only
    disiplinine göre tarihsel kayıt olarak duruyor.
- **LOOP-0 zincirinde neredeyiz:** LOOP-0A (capability probe) → LOOP-0S
  (machine-gate spec) → LOOP-0B (stub rehearsal, CONCERN kabul edildi) →
  LOOP-0C (first real cargo + readiness inventory) → LOOP-0D (J0B safety
  contract, runtime onayı değil) → **LOOP-0E Phase A tamamlandı ve
  düzeltmesi Codex PASS aldı; Phase B (gerçek Piper komutunun elle
  çalıştırılması) hâlâ yürütülmedi ve ayrı, açık bir Ahmet onayı
  bekliyor.**

## 11. SIRADAKİ TEK ADIM

Repo'da literal bir "LOOP-0E Phase B0" kart dosyası **bulunamadı**. En
güncel kart bilgisi `automation/AUTONOMY_LOG.md`'nin son girişinden
("LOOP-0E Phase A manual correction after Codex CONCERN", 2026-07-12)
alınmıştır:

> Ahmet, düzeltme/Codex PASS sonucunu inceler, Piper çalıştırılabilir
> dosyası/model yollarını elle doğrular ve Phase B'yi (gerçek Piper
> komutunun manuel çalıştırılması) onaylayıp onaylamayacağına ayrıca
> karar verir.

Bu adım `human_required` niteliktedir — otomatik başlamaz, otomatik
onaylanmaz.

## 12. BİLİNEN AÇIK MADDELER

- **Letta çelişkisi:** `docs/JARVIS_HARVEST_MAP.md` (REJECT tablosu)
  "Letta runtime | Rejected" derken, `docs/strategy/JARVIS_v5_REALITY_OS_ROADMAP.md`
  Letta (MemGPT)'yi "verified, adopt candidate" olarak işaretliyor.
  `docs/JARVIS_v5_MASTER_ROADMAP.md` ise net bir taahhüt vermeden her
  ikisine de referans veriyor. Bu çelişki `automation/LOOP0D_J0B_SAFETY_CONTRACT.md`
  §7'de belgelendi; geçici (provisional) karar: Letta runtime **onaylı
  değil**, yalnızca mimari desen olarak referans alınabilir. Kalıcı
  çözüm için tek bir doğruluk kaynağı dokümanı güncellenmeli — bunu
  Ahmet ayrıca karara bağlamalı.
- **HA/Wyoming adopt-vs-build kararı:** `automation/LOOP0D_J0B_SAFETY_CONTRACT.md`
  §6, J0/J0B (bu Windows PC) ile Home Assistant + Wyoming (ayrı donanım,
  J2/J5) arasındaki ilişkinin (A: ayrı, B: HA/Wyoming'e devir, C: hibrit)
  henüz Ahmet tarafından tek bir kararla netleştirilmediğini kaydediyor.
  Danışma niteliğinde öneri (C) hibrit yönünde, ama bağlayıcı değil.
- **HUMAN_NEEDED.md ↔ roadmap_state.json tutarsızlığı:** `automation/HUMAN_NEEDED.md`
  hâlâ `[2026-06-24] [E1-S4]` maddesini "Pending" olarak listeliyor, ama
  `roadmap_state.json`'daki `FAZ-3-E1.evidence.e1_s4` alanı bu maddeyi
  `"verdict": "DONE"` (2026-06-27, Ahmet imzalı telefon onayı) olarak
  gösteriyor. İki dosya senkron değil — hangisinin güncel olduğu burada
  varsayılmadı, repo'da açıkça netleştirilmemiş.
- **~~auto_runner çelişkisi~~ — ÇÖZÜLDÜ (2026-08-30).** Graphify grafiği,
  `README.md` §10 ve `BOOT_CHECK.md` §11'in `auto_runner.py`'yi desteklenen
  bir akış olarak belgelerken §9'un tüm AUTO cephelerini kalıcı park
  ettiğini AMBIGUOUS bir kenar olarak yakaladı. Çelişki **§9 lehine**
  sabitlendi: §9 DEĞİŞMEZ bir kural, README/BOOT_CHECK ise operasyon
  belgesi — anayasa kazanır. Her iki bölüm de "PARK EDİLMİŞ / ÇALIŞTIRMA"
  banner'ıyla işaretlendi; başlatma komutu geçersiz, yalnızca kaçak süreç
  temizliği geçerli. Bölümler silinmedi (tarihsel kayıt + temizlik gereği).

## 13. YALIN SAVUNMA VE DENETİM ALTYAPISI

### 13.1 Sözleşme Kilidi (Contract Lock)

`tests/contracts/` altındaki her dosya ve her `*.spec.py` dosyası
**salt-okunurdur (read-only)**. Bir test başarısız olduğunda test kodu ASLA
değiştirilemez; yalnızca kaynak kod düzeltilerek testin geçmesi sağlanmalıdır.

Testin kendisinin yanlış olduğu kanısına varılırsa bu bir kaynak-kod düzeltmesi
değil, **sözleşme değişikliğidir**: durulur ve Ahmet'e sorulur. Sözleşmeyi
gevşeterek yeşile boyamak yasaktır.

*[Durum notu, 2026-08-30: `tests/contracts/` dizini ve `*.spec.py` deseni repoda
henüz yok. Kural ileriye dönüktür — ilk sözleşme testi yazıldığı anda yürürlüğe
girer.]*

### 13.2 Yerel Deterministik Kapı

Bir görev "tamamlandı" olarak işaretlenmeden önce terminalde **sırasıyla**
`pytest` ve `ruff check` çalıştırılmalıdır. Testler %100 geçmeden Ahmet'e
"bitti" denilemez.

Bu repoda kapının doğru çalıştırılışı:

```powershell
$env:PYTHONPATH = (Get-Location).Path
& "C:\Program Files\Python311\Scripts\pytest.exe" tests -q
& "C:\Program Files\Python311\Scripts\ruff.exe" check .
```

Neden bu biçim: `.venv` içinde pytest de ruff da kurulu **değil** (ikisi de
sistem Python 3.11'inde); `PYTHONPATH` verilmezse `agents` / `tools` import'ları
daha toplama (collection) aşamasında patlar; kök dizindeki `voice_test.py`
`edge_tts` istediği için tam kök taraması toplama hatası verir, bu yüzden kapı
`tests` dizinine daraltılmıştır.

**Bilinen taban çizgisi (2026-08-30, `auto/opencode-deepseek`):**
`pytest tests` → **1351 geçti / 0 başarısız**; `ruff check .` → **296 bulgu**.

Test hattı **yeşildir**; bu artık bir hedef değil, korunması gereken bir
durumdur. Yeni bir başarısızlık eklemek doğrudan DoD ihlalidir.

Lint borcu (296 bulgu) hâlâ açıktır ve kapatılmamıştır. `ruff check .`
sayısının **artmaması** zorunludur; azaltmak ayrı bir karttır.

**Sıra bağımsızlığı kuralı:** Bir testin tek başına geçmesi onu geçmiş
saymaz. Kapı **tam süit** üzerinde çalıştırılır. Yeşil hat iddiası, süit
alfabetik *ve* ters sırada geçtiğinde kanıtlanmış olur:

```powershell
$files = Get-ChildItem tests -Filter "test_*.py" -File |
         Sort-Object Name -Descending | ForEach-Object { "tests/$($_.Name)" }
& "C:\Program Files\Python311\Scripts\pytest.exe" @files -q
```

Testler arası izolasyon **tek noktadan**, `tests/conftest.py`'de sağlanır
(belirsiz modül adları + ağır opsiyonel ses kütüphaneleri). İzolasyonu tek
tek test dosyalarına yamamak yasaktır — kök neden ve çözüm için
`FAILURES.md` → "Test State Pollution & Isolation".

### 13.3 Graphify Otomasyonu

3'ten fazla dosya değiştiğinde veya büyük bir refactor yapıldığında arka planda
kod grafiği güncellenmelidir:

```powershell
graphify update .                # AST-only, LLM yok, en ucuz yol (tercih edilen)
graphify extract . --code-only   # tam yeniden çıkarım, yine LLM'siz
```

Not: `--code-only` yalnızca `graphify extract` alt komutunun bayrağıdır;
`graphify . --code-only` diye bir kullanım **yoktur**. Doküman/PDF içeriği
değiştiyse AST yetmez, tam `/graphify` akışı (semantik çıkarım) gerekir.

### 13.4 Hata Hafızası

Karşılaşılan ve çözülen kritik mimari/mantık hataları kısaca `FAILURES.md`
dosyasına işlenmelidir. Kayıt tek satırlık "düzelttim" notu değil; **tuzak +
kök neden + tekrar düşmemek için kural** üçlüsüdür.

---

## DANIŞMAN MODU (her stratejik soruda uygula)

Ahmet "ilerleyelim mi / sıradaki adım ne olmalı / bu doğru mu" tarzı bir
soru sorduğunda:

- Önce olası riski/eksiği söyle, sonra öneriyi.
- Övgü/onay cümlesiyle başlama ("harika fikir" yok).
- Park edilmiş bir cepheye (AUTO/orchestrator/scheduler/Telegram
  auto-send) dokunma ihtiyacı doğarsa, adı ne olursa olsun dur ve sor.
- Kendi ürettiğin işi kendi değerlendirirken özellikle şüpheci ol —
  "bunu ben yazdım, iyi olduğunu düşünüyorum" önyargısına karşı dikkatli
  ol; Codex'in diff-review'ı bunu tam kapatmaz, stratejik "sıradaki adım
  doğru mu" sorusunu SEN sormalısın kendine.
- Emin olmadığın şeyi [EMİN DEĞİLİM] diye işaretle, uydurma.
- Ahmet'in pozisyonuna yeni kanıt olmadan katılma; katılmıyorsan neden
  + alternatif söyle.
- Araştırma disiplinli olsun: Claude Code kendi başına GitHub/web taraması
  YAPMAZ ve yeni teknoloji/repo önermez. Araştırma ihtiyacı doğarsa
  ("bu iş için hazır bir kütüphane var mı?" sorusu), bunu Ahmet'e AÇIKÇA
  sorar; Ahmet onaylarsa Claude (danışman) ya da GPT dışarıdan araştırır,
  sonucu Ahmet onaylayıp karta çevirir. Claude Code'un görevi onaylanmış
  kararları uygulamak, kendi başına strateji/teknoloji değiştirmek değil
  ancak arada bir öneride bulunulabilir.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
