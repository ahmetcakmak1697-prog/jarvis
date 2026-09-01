# JARVIS Engineering Standards
*Versiyon: 1.0 — P0.2 ile oluşturuldu*

---

## Temel felsefe

> "Çalışmayan şey üzerinde dream feature kuramazsın.  
> Plan kâğıt üstünde değil, kanıtlanmış kod üzerinde yürür."

Her adımda şu kontrol seti geçerlidir:

| Kontrol | Soru |
|---------|------|
| **Ne yaptık?** | Faz hedefi ve teslim edilen dosyalar |
| **Nasıl ölçeceğiz?** | Kabul kriterleri — eval/*.json veya smoke test |
| **Bozulursa ne olur?** | Geri dönüş yolu (ZIP + git checkout) |
| **Türkçe kalitesi?** | T1 paralel hattı |
| **3070 / 2×3090 davranışı?** | M0 runtime_profiles.json profil kontrolü |
| **Hangi log üretildi?** | audit_log.jsonl veya smoke çıktısı |
| **Geri dönüş var mı?** | Her commit öncesi checkpoint |

---

## Değişmez kurallar

### 1. Overwrite yok, patch var
`jarvis_brain.py` veya başka aktif dosyalar **asla komple overwrite** edilmez.  
Yeni satır eklenmesi gerekiyorsa byte-safe, idempotent, anchor-tabanlı patcher kullanılır.  
Patcher: fail-loud (anchor yoksa dokunmaz), `.bak` alır, `py_compile` ile doğrular.

### 2. Her büyük değişiklik öncesi checkpoint
```powershell
Compress-Archive -Path .\jarvis_brain.py,.\jarvis_server.py,.\tools,.\agents,.\memory `
  -DestinationPath .\jarvis_checkpoint_<FAZ>_<TARIH>.zip -Force
```
`.gitignore`'da `jarvis_checkpoint_*.zip` ve `*.bak` mevcut — commit'e girmiyor.

### 3. Git commit disiplini
Her fazın sonunda **temiz, spesifik commit:**
```
git add <sadece ilgili dosyalar>
git status --short   # commit'e yanlış dosya girmiyor mu?
git commit -m "<Faz kodu> <ne yapıldı>"
```
Commit mesajı formatı: `Add X`, `Fix Y`, `Add Z and update W`  
`git status --short` tamamen temiz olmadan sonraki faza geçilmez.

### 4. Test önce, özellik sonra
Her faz **önce** kendi smoke/eval testini geçer, **sonra** commit atılır.  
Test paketi: `python .\tests\run_smoke_suite.py`  
Yeni özelliğin testi de aynı suite içine eklenir (faz bitince).

### 5. Tek faz, tek hedef
Bir fazın içinde başka fazın özelliği açılmaz.  
P0 = iskelet + hijyen; P0 ≠ tüm L1 + N1 + benchmark.  
Faz genişlerse yeni faz açılır, mevcut faz şişirilmez.

### 6. Model adı kodda yazılmaz
`jarvis_brain.py` içinde `"mistral-nemo:latest"` gibi model adları hard-code edilemez.  
Tüm model referansları `ModelRegistry` üzerinden çözülür:
```python
from agents.model_registry import ModelRegistry
reg = ModelRegistry()
model = reg.local_main(fallback="mistral-nemo:latest")
```

### 7. Donanım kararı kanıtla verilir
`dual3090` profili — "benchmark ile doğrulanmadan varsayılan yapılmaz."  
`runtime_profiles.json`'da `placeholder` içeren hiçbir değer gerçek modele geçirilmez.

### 8. UI lab disiplini
`jarvis_server.py` içinde görsel deneme **yapılmaz.**  
Tüm UI denemeleri `ui_lab/` içinde yapılır; onaylanırsa entegre edilir.  
Kural: *ana server'a doğrudan büyük UI gömme.*

### 9. Secrets asla kodda bulunmaz
`.env` içinde: `JARVIS_PASSWORD_HASH`, `JARVIS_SESSION_SECRET`, API anahtarları.  
`.env` asla commit'e girmez (`.gitignore`'da). `.env.example` her zaman güncel tutulur.

### 10. Patcher ve geçici scriptler commit'e girmez
`patch_*.py` dosyaları `dev_patches/` altına taşınır.  
`dev_patches/` `.gitignore`'a **eklenmez** — arşiv olarak saklanır.  
Ama ana commit'e `git add dev_patches/` yapılmaz.

---

## Dosya yapısı standardı

```
jarvis/
├── agents/          # Ajan modülleri (model_registry, orchestrator, ...)
├── config/          # runtime_profiles.json, schema_version.txt (ileride)
├── dev_patches/     # Geçici patch scriptleri arşivi (git'te, commit'te değil)
├── docs/            # ENGINEERING_STANDARDS.md, faz kabul kriterleri
├── eval/            # Test senaryoları (*.json), benchmark scriptleri
├── memory/          # SQLite, chroma_db, conversations.json (git'te değil)
├── scripts/         # backup_memory.ps1, operasyon scriptleri
├── tests/           # run_smoke_suite.py, faz smoke testleri
├── tools/           # Tool modülleri
├── ui_lab/          # UI deney alanı (commit edilebilir, ama entegre edilmeden önce onay)
├── jarvis_brain.py  # Ana beyin — overwrite yok, patch var
└── jarvis_server.py # Ana server — UI embed değil (ui_lab disiplini)
```

---

## M0 — Donanım / Model Soyutlama

Mevcut: `RTX 3070, 8GB VRAM, Python 3.11.9`  
Hedef: `2× RTX 3090 NVLink, 48GB VRAM`

```
config/runtime_profiles.json
├── active_profile: "rtx3070"
├── profiles.rtx3070.local_main: "mistral-nemo:latest"   ← kanıtlanmış
└── profiles.dual3090.local_main: "70b-q4-placeholder"   ← benchmark bekleniyor
```

**Profil değiştirme prosedürü:**
1. Model benchmark ile doğrulanır (D-model fazı)
2. `local_main` değeri güncellenir (`placeholder` → gerçek model)
3. Smoke test geçer
4. `active_profile` değiştirilir
5. Commit atılır

Donanım yükseltmesi = mimari değişiklik değil, profil değişikliği.

---

## T1 — Türkçe Kalite Hattı (paralel standart)

Her fazda **paralel** yürütülür:

- `eval/turkish_quality_cases.json` — Türkçe akıcılık + JARVIS tonu test senaryoları
- Model değişikliğinde aynı set yeniden koşturulur
- Hedef: 50 senaryonun ≥ 45'i ton + tutarlılık geçer
- Persona: "efendim" hitabı, quiet competence, dry humor, pushback when right

---

## Kabul kriterleri formatı

Her faz için `docs/<FAZ>_ACCEPTANCE_CRITERIA.md` dosyası:

```markdown
## <FAZ_KODU> Kabul Kriterleri

### Özellik: <özellik adı>
- [ ] <somut, ölçülebilir koşul 1>
- [ ] <somut, ölçülebilir koşul 2>
- [ ] Regression: mevcut smoke suite hâlâ geçiyor
- [ ] Geri dönüş: git checkout ile önceki commit çalışıyor

### Demo noktası
<bu fazın tamamlandığını gösteren demo senaryosu>
```

---

## Hata durumu prosedürü

| Durum | Yapılacak |
|-------|-----------|
| `py_compile` hata | Commit atma, hatayı düzelt, tekrar test et |
| Smoke test kırıldı | Commit atma, `.bak`'tan geri yükle veya `git checkout` |
| Anchor bulunamadı | Patch'i uygulama, dosyanın ilgili satırını göster, anchor güncelle |
| Server başlamıyor | `git log` + `git diff` ile son değişikliği incele, revert et |
| Model yüklenmiyor | `agents.model_registry` çalıştır, profil ve fallback kontrol et |
