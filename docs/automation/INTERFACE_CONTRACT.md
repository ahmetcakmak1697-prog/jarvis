# Orchestrator <-> Verifier Arayüz Sözleşmesi

Bu dosya, körlemesine tahmini bitirir. `orchestrator.py` ile gerçek
`scripts/verifier_runner.py`'nin ÜZERİNDE ANLAŞMASI gereken iki şeyi tanımlar:
(1) active contract şeması, (2) verifier rapor formatı. OpenCode hardening
task'ında hizalama hedefi BUDUR. İkisi bu sözleşmeye uyarsa entegrasyon kapanır.

> Not: Bu sözleşmeyi gerçek `verifier_runner.py`'ye göre kim doğrularsa (OpenCode,
> dosyayı görebilen taraf) son sözü o söyler. Burada GPT'nin bildirdiği alan
> listesi + orchestrator'ın ürettikleri uzlaştırılmıştır.

---

## 1. Active contract şeması (`outcome_contract.active.json`)

Orchestrator bunu YAZAR, verifier OKUR. Kanonik alanlar:

```jsonc
{
  "schema_version": 1,
  "task_id": "FAZ-1B.13I-api-executor-routing",
  "goal": "ProviderSelector privacy bridge ...",

  "allowed_paths":  ["jarvis/executors/assistant_executor.py", "jarvis/executors/executor_registry.py"],
  "forbidden_paths": [".env", ".env.*", "**/.env", "**/secrets/**", "**/*.pem", "memory/**"],

  // verifier'ın KOŞACAĞI deterministik komutlar (acceptance_criteria_machine'den türetilir)
  "required_commands": [
    "py -3.11 -m pytest tests/test_assistant_executor.py -q",
    "py -3.11 -m pytest tests/test_executor_registry.py -q"
  ],

  // test-sayısı guard'ı: bu sayının ALTINA düşerse FAIL (test silme/zayıflatma koruması)
  "minimum_pytest_collected": 682,

  // matematiksel/istatistiksel kritik adımlar için (opsiyonel ama önerilen)
  "mutation_gate": { "source": "jarvis/stats/metrics.py",
                     "test_cmd": "py -3.11 -m pytest tests/test_metrics.py -q",
                     "threshold": 0.8 },

  "human_review_required": false,

  // makinece DOĞRULANAMAYAN (insan) kriterler -> yalnızca bilgi; "koştum" denmez
  "notes": "Türkçe kalite subjektif; deterministik kapı yalnızca regresyonu tutar. ..."
}
```

Karar (madde 3 çözümü): orchestrator `_gen_contract()` bu şemayı üretmeli.
- `acceptance_criteria_machine` -> `required_commands` (çalıştırılabilir hale getir).
- Adımın `min_pytest_collected` alanı varsa -> `minimum_pytest_collected`.
- `acceptance_criteria_human` -> `notes` (asla "çalıştırıldı" gibi davranma).
- `required_checks`/`acceptance_criteria` gibi verifier'ın TANIMADIĞI alanlara güvenme.

## 2. Verifier rapor formatı (`.verifier/reports/`)

Verifier YAZAR, orchestrator OKUR. Orchestrator `_read_verdict()` artık esnek
(`{task_id}_*.json`, `verifier_report_{task_id}*.json`, `*{task_id}*.json` ve
`contract_id`/`task_id` anahtarı). Yine de tek bir standart belirleyin:

```jsonc
{
  "contract_id": "FAZ-1B.13I-api-executor-routing",   // veya "task_id"
  "verdict": "PASS",                                   // PASS | FAIL | NEEDS_HUMAN
  "checks": [ /* ... */ ],
  "timestamp": "2026-06-17T20:00:00+00:00"
}
```

Kurallar:
- Dosya adı task_id içermeli (orchestrator'ın doğru raporu eşlemesi için).
- `verdict` üç değerden biri olmalı.
- `contract_id` veya `task_id`, active contract'taki `task_id` ile AYNI olmalı.

## 3. Runner sözleşmesi (`jarvis_auto_task.ps1`)

- `-ContractPath <yol>` parametresi alır; verifier'ı bu contract ile koşar.
- ContractPath verildi ama dosya yoksa -> FAIL (sessiz default'a düşme).
- Orchestrator runner'ı `-AutoCommit` OLMADAN çağırır (commit kararı orchestrator'da).
- Repair runner'da (MaxRounds); orchestrator FAIL sonrası tekrar koşturmaz.

## 5. State kalıcılığı kararı (madde 7 çözümü)

**Karar: Option A.** `roadmap_state.json` izlenen (tracked) proje yönetim kaydıdır,
runtime çöp değil. Gerekçe: hangi commit'in hangi adımı tamamladığı denetlenebilir
olmalı; roadmap projenin tek doğruluk kaynağıdır.

- Koşum sırasında orchestrator `roadmap_state.json`'u günceller (uncommitted). Temiz-ağaç
  kontrolü bu dosyayı yok sayar, böylece çok-adımlı loop kilitlenmez.
- **İmza anında** (`checkpoint_summary.py --sign`) `roadmap_state.json` NİYETLİ olarak
  commit'lenir ve checkpoint marker'ı (`.verifier/state/last_checkpoint.json`) HEAD'e taşınır.
- Runtime/çöp dosyalar GITIGNORE: `.verifier/`, `outcome_contract.active.json`,
  `cost_ledger.json`, `TASK_*.md`. (Marker `.verifier/state/` altında olduğu için ignore edilir;
  istersen `.verifier/state/`'i ignore dışı tutup commit'leyebilirsin.)

Uzun `--arm` loop'u ancak bu kural net olduğunda açılır.

## 6. Çok-aileli imza incelemesi (factory/academy modeli)

Rigor, build loop'unda DAHA ÇOK LLM ile değil, deterministik kapılarla sağlanır
(pytest/ruff/mypy/mutation/property/reference). LLM çeşitliliği yalnızca **imza
kapısında** değerlidir: `checkpoint_summary.py` bir inceleme paketi üretir; bu paket
Claude + GPT + Gemini'ye AYRI AYRI verilir (farklı aileler -> korelasyonsuz hata);
üçü de "tamam" derse insan `--sign` atar. Build loop'unda kapı deterministiktir;
karar anında inceleme çok-ailelidir. İkisi karışmaz.
