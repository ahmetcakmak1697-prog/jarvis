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
