# ROADMAP DENETİM RAPORU — Faz 1

**Tarih:** 2026-08-20 gece
**Talep:** Ahmet — *"önce sen rapor çıkar, kararları ben veririm, sonra tek kaynağa çevir."*
**Durum:** 🟡 Faz 1 bitti (roadmap doğruluğu). Faz 2 (kod bug/mantık denetimi) **yapılmadı**.
**Ön koşul bağlamı:** `automation/AUTONOMY_CHARTER_PROPOSAL.md` §2 — bu rapor
bitmeden otonom döngü başlamaz.

---

## 0. KAPSAM — NE OKUNDU, NE OKUNMADI

**Okundu ve doğrulandı:**
- `roadmap_state.json` (14 adımın tamamı, tüm evidence alanları)
- `automation/HUMAN_NEEDED.md`
- `docs/JARVIS_HARVEST_MAP.md` (REJECT tablosu)
- `docs/strategy/JARVIS_v5_REALITY_OS_ROADMAP.md` (adopt/borrow tablosu)
- `docs/JARVIS_v5_MASTER_ROADMAP.md` (Letta referansı)
- `scripts/orchestrator.py` (docstring + güvenlik sözleşmesi), dizin envanteri
- `CLAUDE.md` §10-§12

**HENÜZ OKUNMADI (Faz 2'ye kaldı):**
- Kök dizindeki **50+ `TASK_*.md`** dosyası
- `agents/` altındaki ~40 modülün kodu
- Test paketinin gerçekten neyi doğruladığı
- `scripts/orchestrator.py`'ın gövdesi (yalnız docstring okundu)
- `docs/JARVIS_BACKLOG.md`, `docs/JARVIS_REPO_AUDIT.md`

Bu rapordaki hiçbir "DONE" iddiası kod okunarak doğrulanmadı; **belge
tutarlılığı** denetlendi. Kod doğrulaması Faz 2'dir.

---

## 1. ⭐ EN ÖNEMLİ BULGU — İSTENEN DÖNGÜ ZATEN YAZILMIŞ

`scripts/orchestrator.py` **581 satır** ve tam olarak "PC açık oldukça kodlansın"
döngüsünün kendisi. Kendi docstring'inden, birebir:

```
roadmap_state oku -> sıradaki eligible adımı seç
-> task dosyası + outcome contract üret
-> [spec-by-test] implement adımında tests/ allowed_paths'ten çıkarılır
-> checkpoint al (geri dönüş noktası)
-> jarvis_auto_task.ps1 çağır (maker + verifier + repair; AUTO-COMMIT YOK)
-> verifier verdict + diff istatistiği oku
-> escalation_policy ile karar ver
-> PROCEED_COMMIT / HUMAN_GATE / HALT
-> roadmap_state güncelle, log yaz
```

**Güvenlik varsayılanları, sözleşme taslağımla neredeyse birebir aynı:**

| orchestrator.py'ın kendi kuralı | Sözleşme taslağındaki karşılığı |
|---|---|
| DRY-RUN varsayılan; `--arm` VE `--budget` zorunlu | §1.3 (dur-varsayılan) |
| `acceptance_criteria_machine` boş `auto` adım **asla** otonom koşmaz → human_gate | §7 (insan kapısı) |
| implement adımında maker `tests/` göremez (spec-by-test) | §4.5 (testi geçirmek için testi değiştirme yasağı) |
| commit yalnız `allowed_paths`; asla `git add -A`; asla push | §1.3 (delinmeyen kurallar) |
| her koşum `--max-steps` sınırlı; bütçe aşımında HALT | §4 (3 deneme sınırı) |
| HALT → checkpoint'e geri sar | (taslakta yoktu — **daha iyi**) |

Destek dosyaları da yerinde: `scripts/verifier_runner.py` (323),
`scripts/escalation_policy.py`, `scripts/mutation_gate.py` (158),
`scripts/jarvis_auto_task.ps1` (531), `scripts/jarvis_autonomy_status.ps1` (102),
`scripts/checkpoint_summary.py`, `scripts/daily_report.py`.
`roadmap_state.json`'daki `policy_defaults` (`budget_usd: 5.0`,
`max_repair_rounds: 4`) bu motorun ayarları.

### Bunun anlamı
**Sıfırdan yazmak büyük olasılıkla gereksiz.** Yapılacak iş, yeni bir sistem
kurmak değil; **var olanı denetleyip maker tarafını değiştirmek.**

Mevcut maker **OpenCode/DeepSeek** (dal adı `auto/opencode-deepseek`, ve
`TASK_FIX_RUNNER_OPENCODE_FAILURE.md`, `TASK_FIX_RUNNER_OPENCODE_CWD_AND_FALSE_SUCCESS.md`,
`TASK_FIX_RUNNER_OPENCODE_STDERR_HANDLING.md`, `TASK_FIX_RUNNER_OPENCODE_TIMEOUT_AND_LOGGING.md`
dosyaları o hattın sancılı olduğunu gösteriyor).

Önerilen yön: **iskelet kalsın, maker Claude Code + denetçi `codex review` olsun.**
Bu, Ahmet'in "0'dan yazıp gereksiz iş yükü oluşturmayalım" talimatının deponun
kendi içine uygulanmış hâli.

> ⚠️ **Dikkat:** bu motor `CLAUDE.md` §9'un "park edilmiş cepheler" listesindeki
> orchestrator'ın ta kendisi. Yani sözleşme imzalanmadan buna dokunulmaz.
> [EMİN DEĞİLİM] neden parklandığı henüz okunmadı — Faz 2'de `AUTONOMY_RULES.md`
> ve ilgili TASK dosyaları okunacak. **Parklanma sebebi öğrenilmeden yeniden
> silahlandırılmamalı.**

---

## 2. ✅ ÇÖZÜLDÜ — "LETTA ÇELİŞKİSİ" ÇELİŞKİ DEĞİL

`CLAUDE.md` §12 bunu açık madde olarak listeliyor. **Kanıtlar okunduğunda
çelişki ortadan kalkıyor.**

| Kaynak | Ne diyor |
|---|---|
| `JARVIS_HARVEST_MAP.md:99` | "Letta **runtime** \| Rejected." |
| `REALITY_OS_ROADMAP.md:330` | kullanım sütunu: "**Pattern çal**" |
| `REALITY_OS_ROADMAP.md:231` | "🟡 **Borrow**: Letta (core/recall/archival)" |
| `JARVIS_v5_MASTER_ROADMAP.md:273` | "**Referans**: Letta / MemGPT" |

Aynı tabloda LiteLLM ve Wyoming satırları kullanım sütununda "**Adopt**" diyor.
Yani tablo "Pattern çal" ile "Adopt"u **bilinçli olarak ayırıyor**. Letta
"Pattern çal" tarafında.

Çelişki sanılan şey, son sütundaki `verified, adopt candidate` etiketinin
desen-satırlarına da aynı yazılmış olması (Graphiti/Mem0 satırlarında da aynı).
Bu bir **etiket tutarsızlığı**, karar çatışması değil.

**Sonuç:** üç doküman da aynı şeyi söylüyor — *runtime reddedildi, desen ödünç
alınacak*. `LOOP0D_J0B_SAFETY_CONTRACT.md` §7'deki geçici karar zaten bununla
uyumlu. Yapılacak: son sütunun ifadesini düzeltmek (`pattern only, runtime
rejected`) ve `CLAUDE.md` §12'den bu maddeyi kaldırmak.

**→ Ahmet'ten karar gerekmiyor, yalnız onay.**

---

## 3. ✅ DOĞRULANDI — HUMAN_NEEDED.md BAYAT (E1-S4)

`CLAUDE.md` §12'nin bu maddesi **doğru**, ve hangisinin güncel olduğu artık belli.

| Kaynak | İddia |
|---|---|
| `HUMAN_NEEDED.md` | `- [ ] [2026-06-24] [E1-S4]` — **Pending** |
| `roadmap_state.json` → `FAZ-3-E1.evidence.e1_s4` | **DONE** |

roadmap_state'teki kayıt ayrıntılı ve daha yeni:
```
verdict: DONE
at: 2026-06-27T22:51:38Z          (HUMAN_NEEDED girdisinden 3 gün SONRA)
signed_by: "Ahmet (phone receipt confirmed)"
messages_sent: 1
wiring_commit: a39db4568
codex_pass_before_execution: true
token_exposed: false, chat_id_exposed: false
notes: "Codex PASS (33/33 wiring + 157/157 regression). No scheduler, no retry, no background loop."
```

Ayrıca `FAZ-3-E1.evidence.remaining` içinde de yazıyor:
`"E1-S4: DONE — live Telegram smoke confirmed by Ahmet 2026-06-27"`.

**Değerlendirme:** `HUMAN_NEEDED.md` bayat. E1-S4 maddesi "Resolved" bölümüne
taşınmalı (2026-06-27, imza: Ahmet, telefon teyidi).

**→ Ahmet'ten onay: bu doğru mu? Telefonda o mesajı gerçekten aldın mı?**
Kayıt öyle diyor ama imzayı sen attın, teyidi sen verebilirsin.

---

## 4. 🔧 DÜZELTME — `roadmap_state.json` "2 aydır güncellenmemiş" DEĞİL

`CLAUDE.md` §10 dolaylı olarak, ve ben bu akşam Ahmet'e açıkça, dosyanın
2026-06-18'den beri güncellenmediğini söyledim. **Yanlış.**

- Üst düzey alan: `"updated": "2026-06-18"`
- Ama içeriğinde **2026-06-27** ve **2026-06-28** tarihli, `signed_by: "Codex"`
  imzalı evidence kayıtları var (E1-S6A/B/C/D/E, E1-S4).

Yani dosya güncellenmiş; **güncellenmeyen şey `updated` alanının kendisi.**
Bayat olan içerik değil, etiket.

**Etkisi:** "tek doğruluk kaynağı bayat, o yüzden güvenilmez" gerekçesi düşüyor.
İçerik, git log'un gösterdiği son gerçek çalışmayla (2026-06-28) tutarlı.

**Yapılacak:** `updated` alanı her yazımda otomatik güncellensin (orchestrator
zaten `roadmap_state` yazıyor — oraya eklenecek küçük bir madde).

---

## 5. ❓ KARAR GEREKTİREN — FAZ-3-E1 gerçekten `in_progress` mi?

`FAZ-3-E1` tek `in_progress` adım. Ama **kendi `remaining` listesi her şeyi
DONE gösteriyor:**
```
remaining: [
  "E1-S6A-E: DONE (see individual E1-S6x steps below)",
  "E1-S4: DONE — live Telegram smoke confirmed by Ahmet 2026-06-27"
]
```
Ve E1-S6A, S6B, S6C, S6D, S6E adımlarının **beşi de** `status: done`,
hepsi Codex imzalı.

Neden hâlâ `in_progress` olabilir: `kind: architectural`,
`autonomy: human_required`, ve **5 maddelik `acceptance_criteria_human`** var:
1. Proactive trigger policy reviewed
2. No automatic push/background behavior enabled blindly
3. Default-off `JARVIS_PROACTIVE_ENABLED` invariant accepted
4. Cooldown/rate-limit ve mute/opt-out tasarımı gözden geçirildi
5. Proaktif davranış rahatsız edici olmadan yardımcı oluyor

evidence'ta bu beş madde için **açık bir Ahmet imzası yok** (E1-S4 ve E1-S5
için var, mimari kapının kendisi için yok).

**Değerlendirme:** bu muhtemelen bir hata değil, **imzalanmamış mimari kapı**.
Yani makine işi bitmiş, insan onayı eksik. Bu tam olarak sistemin doğru
davranışı.

**→ Ahmet'ten karar:** yukarıdaki 5 maddeyi onaylıyor musun?
- Onaylarsan FAZ-3-E1 → `done`, ve **FAZ-3'ten sonrası açılır**.
- Onaylamazsan, hangi madde eksik? O, döngünün ilk gerçek görevi olur.

⚠️ Not: bu adımın `allowed_paths`'inde `tools/telegram_agent.py` var ve konu
proaktif Telegram teslimatı — yani `CLAUDE.md` §9'daki **park edilmiş
"Telegram auto-send" cephesine** temas ediyor. FAZ-3-E1'i `done` işaretlemek
o cepheyi **açmaz** (kod default-off ve pull-based), ama sıradaki adımların
oraya yaklaşması muhtemel. Sözleşme §7'ye göre orada durulur.

---

## 6. ÖZET TABLO — 14 ADIM

| # | id | status | not |
|---|---|---|---|
| 1 | FAZ-0 | done | temel sistem |
| 2 | DEVOPS-verifier | done | `867b471b0` |
| 3 | FAZ-1B.13H | done | Türkçe `İ` fold düzeltmesi |
| 4 | FAZ-1B.13-audit | done | spec, read-only |
| 5 | FAZ-1B.13I-api-executor-routing | done | `dacf2aeaf` |
| 6 | FAZ-2-D2 | done | web research, **default-off** |
| 7 | **FAZ-3-E1** | **in_progress** | **§5 — imzasız mimari kapı** |
| 8 | E1-S6A | done | proactive_runner dry-run CLI |
| 9 | E1-S6B | done | DeliveryResult |
| 10 | E1-S6C | done | Task Scheduler **şablonu** (görev oluşturulmadı) |
| 11 | E1-S6D | done | live-mode guard |
| 12 | E1-S6E | done | throttle/cooldown |
| 13 | FAZ-T1 | done | Türkçe kalite, **Ahmet imzalı** |
| 14 | FAZ-PHASE2-integration | done | canlı ağ yok |

**13 done / 1 in_progress.** Roadmap'te FAZ-3 sonrası **hiç adım yok** — yani
döngü açılsa bile *yapacak iş listesi boş*. Bu, §7'deki en kritik boşluk.

---

## 7. 🔴 EN BÜYÜK BOŞLUK — SIRADAKİ İŞ LİSTESİ YOK

Otonom döngünün yakıtı `roadmap_state.json`'daki `status: pending` adımlardır.
**Şu anda öyle bir adım yok.** 13 done, 1 imza bekleyen.

Yani sözleşme bugün imzalansa ve orchestrator silahlandırılsa, sistem
**ilk turda duracak** — seçecek uygun adım bulamayacak.

Buradaki iş sırası kaçınılmaz olarak şu:
1. FAZ-3-E1 imzalanır (§5) →
2. FAZ-4+ adımları **yazılır** — makine kriterli, `allowed_paths`'li,
   `autonomy` etiketli →
3. ancak o zaman döngü anlamlı çalışır.

2. madde, `docs/JARVIS_BACKLOG.md` ve `REALITY_OS_ROADMAP.md`'deki hedeflerin
`roadmap_state.json` formatına çevrilmesi demek. **Bu, Faz 2'nin ana çıktısı
olmalı** ve Ahmet'in karar vereceği en büyük kalem.

---

## 8. AHMET'TEN GEREKEN KARARLAR

| # | Karar | Zorluk |
|---|---|---|
| **K1** | Mevcut `scripts/orchestrator.py` yeniden kullanılsın mı, yoksa yenisi mi yazılsın? (Önerim: yeniden kullan, maker'ı Claude+Codex yap) | orta |
| **K2** | Orchestrator neden parklanmıştı? ✅ **Claude araştırdı (26.08)** — `AUTONOMY_CHARTER_PROPOSAL.md` §8.5'te cevaplandı: belgelenmiş sebep yok, öncelik kayması görünüyor. Ahmet yalnızca teyit edecek. | kolay |
| **K3** | FAZ-3-E1'in 5 insan kriterini onaylıyor musun? (§5) | orta |
| **K4** | E1-S4 telefon teyidi doğru mu? `HUMAN_NEEDED.md`'yi Resolved'a taşıyayım mı? (§3) | kolay |
| **K5** | Letta maddesi kapatılsın mı? (§2 — çelişki yok, yalnız ifade düzeltmesi) | kolay |
| **K6** | FAZ-4+ adımları hangi kaynaktan üretilsin: `JARVIS_BACKLOG.md` mi, `REALITY_OS_ROADMAP.md` mi, ikisi mi? (§7) | **büyük** |

---

## 9. FAZ 2 — SIRADAKİ DENETİM (henüz yapılmadı)

1. `AUTONOMY_RULES.md` + TASK dosyaları → **orchestrator neden parklandı**
2. `scripts/orchestrator.py` gövdesi → mantık hatası / bug denetimi
3. `agents/` (~40 modül) → bug, sınır koşulu, Türkçe fold, sessiz hata yutma
4. Test paketi → testler **iddia ettikleri şeyi** gerçekten ölçüyor mu
5. 50+ `TASK_*.md` → hangileri güncel, hangileri tarihsel çöp
6. FAZ-4+ adım taslakları (K6'nın cevabına göre)
