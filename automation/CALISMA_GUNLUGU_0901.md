# Çalışma Günlüğü — 2026-09-01 (gözetimsiz oturum)

Taban çizgisi girişte: 1570 test / ruff 295. Çıkışta: **1570 / 295** — değişmedi
(bu oturumda kod değişmedi, yalnız ölçüm ve rapor üretildi).

---

- **ADIM B commit'lendi** → `ccce9b21e`. 7 isimli dosya (`git add -A` yok):
  `agent/local_agent.py`, `voice/stt.py`, `agents/data_classifier.py`,
  `memory/entity_extractor.py`, `scripts/j0_mic_check.py` + 2 test dosyası.

- **SkillSpector kuruldu** (`uv tool install`, NVIDIA/SkillSpector, Apache-2.0).
  5 hedef `--no-llm` ile tarandı; LLM analizörleri API anahtarı istediği için
  bilerek atlandı. 152 bulgu → `automation/SKILLSPECTOR_RAPORU.md`.
  **Hiçbiri düzeltilmedi.** Kritik ayrım: 84 HIGH bulgunun tamamı
  `__pycache__` — gitignore'da ve 0 dosya izleniyor, yani depoya hiç girmiyor.
  Gerçek ilgi çeken ~10 HIGH: `tools.py` içindeki `exec()`/`eval()`,
  graphify skill'indeki `rm -f` ve "anti-refusal" metni.

- **ADIM C model kıyası koşuldu** → `automation/MODEL_KIYASI_0901.md`.
  3 kurulu model × 7 Türkçe soru × aynı persona prompt'u.
  **Kartın VRAM hipotezi doğrulandı:** mistral-nemo tepe **6880 MB**, 8 GB
  kartta belgelenmiş ~6 GB tavanın üstünde; sonucu **3 kat yavaş**
  (25,8 vs 78,2 tok/s) ve ilk token 3,5 kat geç. qwen2.5:7b 5386 MB,
  llama3.1 5878 MB — ikisi de sığıyor.
  Kazanan **ilan edilmedi**, `runtime_profiles.json`'a **dokunulmadı**.

- **Whisper small vs medium ölçüldü** (aynı rapora ek).
  `medium` 2,7 kat yavaş ve benzerlik biraz **düşük** (0,974 vs 0,982).
  **Varsayılan değiştirilmedi**; öneri: `small` kalsın.

- **FAILURES.md**'ye bu gecenin dersi işlendi: *"açılan akış çalışan akış
  demek değildir"* — üç parçalı kural (açılış ≠ veri; sessiz başarısızlık
  en pahalısı; aygıt indeksi kalıcı kimlik değildir).

- **4 karar Ahmet'e bırakıldı** → `automation/AHMET_ONAYI_BEKLEYENLER.md`:
  A1 Turkish-Gemma indirme, A2 `runtime_profiles.json` değişikliği,
  A3 SkillSpector bulguları (4 madde), A4 `_load_project_context()` eskimiş
  durum bloğu + testteki replika kusuru.

- **Kapı:** `pytest tests` 1570 passed (alfabetik **ve** ters sıra),
  `ruff check .` 295, import döngüsü yok. `graphify update .` →
  5203 düğüm / 10040 kenar.

---

## Commit'lenmeyenler (Ahmet onayı bekliyor)

Bu oturumda üretilen dosyalar **commit edilmedi** — hepsi rapor/karar
niteliğinde:

```
automation/SKILLSPECTOR_RAPORU.md
automation/MODEL_KIYASI_0901.md
automation/AHMET_ONAYI_BEKLEYENLER.md
automation/CALISMA_GUNLUGU_0901.md
FAILURES.md                      (değişiklik)
automation/_ss_raw/              (ham tarama JSON'ları)
automation/_model_bench_raw.json
automation/_whisper_bench_raw.json
```
