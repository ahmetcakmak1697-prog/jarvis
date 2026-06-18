# Orchestrator <-> Verifier ArayÃ¼z SÃ¶zleÅŸmesi

Bu dosya, kÃ¶rlemesine tahmini bitirir. `orchestrator.py` ile gerÃ§ek
`scripts/verifier_runner.py`'nin ÃœZERÄ°NDE ANLAÅMASI gereken iki ÅŸeyi tanÄ±mlar:
(1) active contract ÅŸemasÄ±, (2) verifier rapor formatÄ±. OpenCode hardening
task'Ä±nda hizalama hedefi BUDUR. Ä°kisi bu sÃ¶zleÅŸmeye uyarsa entegrasyon kapanÄ±r.

> Not: Bu sÃ¶zleÅŸmeyi gerÃ§ek `verifier_runner.py`'ye gÃ¶re kim doÄŸrularsa (OpenCode,
> dosyayÄ± gÃ¶rebilen taraf) son sÃ¶zÃ¼ o sÃ¶yler. Burada GPT'nin bildirdiÄŸi alan
> listesi + orchestrator'Ä±n Ã¼rettikleri uzlaÅŸtÄ±rÄ±lmÄ±ÅŸtÄ±r.

---

## 1. Active contract ÅŸemasÄ± (`outcome_contract.active.json`)

Orchestrator bunu YAZAR, verifier OKUR. Kanonik alanlar:

```jsonc
{
  "schema_version": 1,
  "task_id": "FAZ-1B.13I-api-executor-routing",
  "goal": "ProviderSelector privacy bridge ...",

  "allowed_paths":  ["jarvis/executors/assistant_executor.py", "jarvis/executors/executor_registry.py"],
  "forbidden_paths": [".env", ".env.*", "**/.env", "**/secrets/**", "**/*.pem", "memory/**"],

  // verifier'Ä±n KOÅACAÄI deterministik komutlar (acceptance_criteria_machine'den tÃ¼retilir)
  "required_commands": [
    "py -3.11 -m pytest tests/test_assistant_executor.py -q",
    "py -3.11 -m pytest tests/test_executor_registry.py -q"
  ],

  // test-sayÄ±sÄ± guard'Ä±: bu sayÄ±nÄ±n ALTINA dÃ¼ÅŸerse FAIL (test silme/zayÄ±flatma korumasÄ±)
  "minimum_pytest_collected": 682,

  // matematiksel/istatistiksel kritik adÄ±mlar iÃ§in (opsiyonel ama Ã¶nerilen)
  "mutation_gate": { "source": "jarvis/stats/metrics.py",
                     "test_cmd": "py -3.11 -m pytest tests/test_metrics.py -q",
                     "threshold": 0.8 },

  "human_review_required": false,

  // makinece DOÄRULANAMAYAN (insan) kriterler -> yalnÄ±zca bilgi; "koÅŸtum" denmez
  "notes": "TÃ¼rkÃ§e kalite subjektif; deterministik kapÄ± yalnÄ±zca regresyonu tutar. ..."
}
```

Karar (madde 3 Ã§Ã¶zÃ¼mÃ¼): orchestrator `_gen_contract()` bu ÅŸemayÄ± Ã¼retmeli.
- `acceptance_criteria_machine` -> `required_commands` (Ã§alÄ±ÅŸtÄ±rÄ±labilir hale getir).
- AdÄ±mÄ±n `min_pytest_collected` alanÄ± varsa -> `minimum_pytest_collected`.
- `acceptance_criteria_human` -> `notes` (asla "Ã§alÄ±ÅŸtÄ±rÄ±ldÄ±" gibi davranma).
- `required_checks`/`acceptance_criteria` gibi verifier'Ä±n TANIMADIÄI alanlara gÃ¼venme.

## 2. Kalite kademeleri (quality tiers)

Ä°ki ayrÄ± kalite kapÄ±sÄ± tanÄ±mlanmÄ±ÅŸtÄ±r:

### A. Normal mÃ¼hendislik kapÄ±sÄ± (Normal engineering gate)

VarsayÄ±lan kademe. Verifier PASS + deterministik kontroller temizse otonom
(PROCEED_COMMIT) geÃ§er. Ä°nsan imzasÄ± yalnÄ±zca `judgment_kinds`, `human_required`,
hassas alan, API yÃ¼zeyi, test deÄŸiÅŸikliÄŸi, geniÅŸ blast radius, dosya silme gibi
Ã¶zel tetikleyiciler varken gerekir.

### B. DoÄŸruluk-kritik kapÄ± (Correctness-critical gate)

AdÄ±m `correctness_critical: true` ile iÅŸaretlendiÄŸinde etkinleÅŸir. Verifier PASS
olsa ve hiÃ§bir normal tetikleyici ateÅŸlenmese bile `escalation_policy.py` HUMAN_GATE
dÃ¶ndÃ¼rÃ¼r. GerekÃ§e: sayÄ±sal/istatistiksel modÃ¼llerde testler de yanlÄ±ÅŸ olabilir;
insan imzasÄ± zorunludur.

Correctness-critical adÄ±mlar ÅŸunlarÄ± Ä°Ã‡ERMELÄ°DÄ°R:

- `correctness_critical: true` (adÄ±m tanÄ±mÄ±nda)
- Bilinen doÄŸru Ã¶rneklere / oracle'a karÅŸÄ± referans testleri (mÃ¼mkÃ¼nse)
- Property veya invariant testleri
- Mutation gate veya aÃ§Ä±k hata-enjeksiyon kontrolÃ¼
- Deterministik testler PASS olsa bile insan imzasÄ±

Ã–rnek adÄ±mlar:

- telemetri hesaplamalarÄ±
- yakÄ±t/boÅŸta/km/maliyet hesaplamalarÄ±
- scorecard'lar
- anomali tespiti
- percentil/IQR/aykÄ±rÄ± deÄŸer
- raporlama metrikleri
- ESHOT sayÄ±sal raporlarÄ±

## 2. Verifier rapor formatÄ± (`.verifier/reports/`)

Verifier YAZAR, orchestrator OKUR. Orchestrator `_read_verdict()` artÄ±k esnek
(`{task_id}_*.json`, `verifier_report_{task_id}*.json`, `*{task_id}*.json` ve
`contract_id`/`task_id` anahtarÄ±). Yine de tek bir standart belirleyin:

```jsonc
{
  "contract_id": "FAZ-1B.13I-api-executor-routing",   // veya "task_id"
  "verdict": "PASS",                                   // PASS | FAIL | NEEDS_HUMAN
  "checks": [ /* ... */ ],
  "timestamp": "2026-06-17T20:00:00+00:00"
}
```

Kurallar:
- Dosya adÄ± task_id iÃ§ermeli (orchestrator'Ä±n doÄŸru raporu eÅŸlemesi iÃ§in).
- `verdict` Ã¼Ã§ deÄŸerden biri olmalÄ±.
- `contract_id` veya `task_id`, active contract'taki `task_id` ile AYNI olmalÄ±.

## 3. Runner sÃ¶zleÅŸmesi (`jarvis_auto_task.ps1`)

- `-ContractPath <yol>` parametresi alÄ±r; verifier'Ä± bu contract ile koÅŸar.
- ContractPath verildi ama dosya yoksa -> FAIL (sessiz default'a dÃ¼ÅŸme).
- Orchestrator runner'Ä± `-AutoCommit` OLMADAN Ã§aÄŸÄ±rÄ±r (commit kararÄ± orchestrator'da).
- Repair runner'da (MaxRounds); orchestrator FAIL sonrasÄ± tekrar koÅŸturmaz.

## 5. State kalÄ±cÄ±lÄ±ÄŸÄ± kararÄ± (madde 7 Ã§Ã¶zÃ¼mÃ¼)

**Karar: Option A.** `roadmap_state.json` izlenen (tracked) proje yÃ¶netim kaydÄ±dÄ±r,
runtime Ã§Ã¶p deÄŸil. GerekÃ§e: hangi commit'in hangi adÄ±mÄ± tamamladÄ±ÄŸÄ± denetlenebilir
olmalÄ±; roadmap projenin tek doÄŸruluk kaynaÄŸÄ±dÄ±r.

- KoÅŸum sÄ±rasÄ±nda orchestrator `roadmap_state.json`'u gÃ¼nceller (uncommitted). Temiz-aÄŸaÃ§
  kontrolÃ¼ bu dosyayÄ± yok sayar, bÃ¶ylece Ã§ok-adÄ±mlÄ± loop kilitlenmez.
- **Ä°mza anÄ±nda** (`checkpoint_summary.py --sign`) `roadmap_state.json` NÄ°YETLÄ° olarak
  commit'lenir ve checkpoint marker'Ä± (`.verifier/state/last_checkpoint.json`) HEAD'e taÅŸÄ±nÄ±r.
- Runtime/Ã§Ã¶p dosyalar GITIGNORE: `.verifier/`, `outcome_contract.active.json`,
  `cost_ledger.json`, `TASK_*.md`. (Marker `.verifier/state/` altÄ±nda olduÄŸu iÃ§in ignore edilir;
  istersen `.verifier/state/`'i ignore dÄ±ÅŸÄ± tutup commit'leyebilirsin.)

Uzun `--arm` loop'u ancak bu kural net olduÄŸunda aÃ§Ä±lÄ±r.

## 6. Ã‡ok-aileli imza incelemesi (factory/academy modeli)

Rigor, build loop'unda DAHA Ã‡OK LLM ile deÄŸil, deterministik kapÄ±larla saÄŸlanÄ±r
(pytest/ruff/mypy/mutation/property/reference). LLM Ã§eÅŸitliliÄŸi yalnÄ±zca **imza
kapÄ±sÄ±nda** deÄŸerlidir: `checkpoint_summary.py` bir inceleme paketi Ã¼retir; bu paket
Claude + GPT + Gemini'ye AYRI AYRI verilir (farklÄ± aileler -> korelasyonsuz hata);
Ã¼Ã§Ã¼ de "tamam" derse insan `--sign` atar. Build loop'unda kapÄ± deterministiktir;
karar anÄ±nda inceleme Ã§ok-ailelidir. Ä°kisi karÄ±ÅŸmaz.

