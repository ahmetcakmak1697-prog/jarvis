# SkillSpector Güvenlik Taraması — 2026-09-01

**Araç:** [NVIDIA/SkillSpector](https://github.com/NVIDIA/SkillSpector) (Apache-2.0,
Python, son güncelleme 2026-09-01) · `uv tool install` ile kuruldu
**Mod:** `--no-llm` — **yalnız statik analiz.** LLM tabanlı semantik analizörler
(`semantic_developer_intent`, `semantic_quality_policy`) API anahtarı istediği
için **bilerek çalıştırılmadı** (§9: `.env`/anahtar Ahmet'in).
**Taranan:** `.claude/skills/`, `.claude/CLAUDE.md`, `agents/`, `tools/`,
`.mcp.json.example`

> **Bu raporda hiçbir bulgu düzeltilmedi.** Sınıflandırma ve gerekçe var,
> karar Ahmet'in.

---

## Özet

| Şiddet | Ham sayı | Gerçek ilgi çeken |
|---|---|---|
| HIGH | 106 | **~10** |
| MEDIUM | 44 | ~14 |
| LOW | 2 | 0 |
| **Toplam** | **152** | — |

Ham sayı ile gerçek sayı arasındaki farkın tamamı tek bir desenden geliyor —
aşağıda ilk madde.

---

## G0 — GÜRÜLTÜ: 84 HIGH bulgunun tamamı `__pycache__` (İŞLEM GEREKMİYOR)

**Bulgu:** *"Skill ships Python bytecode (.pyc/.pyo) that normal analysis skips"*
— 82 adet; artı *"ships a `__pycache__` directory"* — 2 adet.

**Neden gürültü:** Bu uyarı **dağıtılan** bir skill için doğrudur: `.pyc`
kaynak analizinden kaçar, içine kod saklanabilir. Ama burada dosyalar
yerel derleme artığı:

```
__pycache__ gitignore'da  : EVET
__pycache__ git'te izlenen : 0 dosya
```

Yani hiçbiri depoya girmiyor, kimseye dağıtılmıyor. SkillSpector diski
tarıyor, git'i değil.

**Öneri:** İşlem yok. Taramayı tekrarlarken `--exclude __pycache__` benzeri
bir filtre kullanmak raporu okunur kılar.

---

## K1 — DÜZELTİLDİ: `exec()` / `eval()` — ilk değerlendirmem YANLIŞTI

> **2026-09-01 düzeltme.** Aşağıdaki ilk değerlendirmede *"`_detect_tool()`
> bunları kullanıcı cümlesinden tetikleyebiliyor"* yazmıştım. **Yanlış.**
> Ahmet doğruladı, ben de teyit ettim: `_detect_tool()` yalnızca
> `TOOL_TRIGGERS`'ta karşılığı olan **6** araca yol açıyor
> (`web_search`, `deep_research`, `calculate`, `get_datetime`, `get_notes`,
> `save_note`). `run_python_code` bunların hiçbirinde yok — yani mikrofondan
> ya da cümleden **erişilemiyordu**. Prompt injection yüzeyi yazdığımdan
> belirgin küçük.
>
> **Gerçek bulgu erişilebilirlik değil, ERİŞİLEMEZLİK:** `run_python_code`
> ajanın araç sözlüğüne yükleniyordu ama hiçbir yoldan çağrılamıyordu —
> değer üretmeden risk taşıyan ölü yüzey.
>
> **Yapılan:** `agent/local_agent.py::_load_tools()` sözlüğünden çıkarıldı.
> `tools/tools.py` **değiştirilmedi** (CLAUDE.md §3 — önceden var olan koda
> dokunulmaz). Kilit: `tests/test_local_agent_tool_surface.py`.
>
> **`calculate`'in `eval`'i bırakıldı** — kısıtlı (`{"__builtins__": {}}` +
> yalnız math ad alanı), ayrı ve düşük öncelikli kart.
>
> **Kalan:** `analyze_file` de aynı şekilde ulaşılamıyor ama `exec`/`eval`
> içermiyor; bu turda kapsam dışı bırakıldı → `AHMET_ONAYI_BEKLEYENLER` A5.

### İlk (hatalı) değerlendirme — kayıt için bırakıldı

| Bulgu | Konum | Şiddet |
|---|---|---|
| `exec() call detected` | `tools/tools.py:482` | HIGH |
| `eval() call detected` | `tools/tools.py:509` | HIGH |

```python
tools.py:482    exec(code, safe_globals)                              # run_python_code
tools.py:509    result = eval(expression, {"__builtins__": {}}, safe_dict)  # calculate
```

**Değerlendirme:** İkisi de **kasıtlı** — `run_python_code` ve `calculate`
araçlarının işi bu. `eval` tarafı `{"__builtins__": {}}` ile kısıtlanmış,
yani en yaygın kaçış yolu kapatılmış. `exec` tarafındaki `safe_globals`'ın
ne içerdiği bu taramada **incelenmedi**.

**Neden yine de kritik:** Bu iki araç `TOOL_REGISTRY`'de canlı ve
`_detect_tool()` bunları **kullanıcı cümlesinden** tetikleyebiliyor. Yani
saldırı yüzeyi "Ahmet bilerek kod çalıştırdı" değil, "modelin ürettiği bir
girdi araç çağırdı". Prompt injection ile birleşirse doğrudan kod yürütme
olur.

**Ahmet'e soru:** `run_python_code` gerçekten gerekli mi? Gerekliyse
`safe_globals` içeriği ayrı bir kartta denetlenmeli.

---

## K2 — `.env` referansları (13 HIGH, "Credential Access")

**Konum:** `.mcp.json.example` ve `agents/` içindeki çeşitli dosyalar.

**Değerlendirme:** `.mcp.json.example`'daki eşleşmeler **beklenen** —
o dosya zaten `${HA_TOKEN}` gibi ortam değişkeni *referansları* tutuyor,
sırrın kendisini değil; tasarım gereği böyle. Daha önceki denetimde
`.env.example`'ın yalnız placeholder içerdiği doğrulanmıştı ve `.env`
geçmişten kazınmıştı (commit `01e1bf04e`).

**Öneri:** İşlem yok, ama `agents/` tarafındaki 13 eşleşmenin hangi
dosyalarda olduğu **tek tek gözden geçirilmeli** — bu tarama dosya adı
düzeyinde raporlamadı.

---

## K3 — `subprocess` çağrıları (20 MEDIUM)

**Dosyalar:** `auto_updater.py`, `tools/jarvis_interpreter.py`,
`agents/project_intelligence.py` ve diğerleri.

**Değerlendirme:** Çoğu `git log` gibi salt-okunur komutlar (ör.
`_load_project_context()` içindeki `git log -5 --oneline`). Ama
`auto_updater.py` adı başlı başına dikkat çekiyor — **park edilmiş AUTO
cephesiyle** ilgili olabilir (§9).

**Ahmet'e soru:** `auto_updater.py` hâlâ çağrılıyor mu, yoksa ölü kod mu?

---

## K4 — Dış iletim (11 MEDIUM, "Data Exfiltration")

**Dosyalar:** `agents/daily_digest.py`, `agents/e1_s4_smoke_sender.py`,
`scripts/orchestrator.py`

**Değerlendirme:** Bunlar Telegram gönderim yolları. §9'a göre Telegram
auto-send **park edilmiş** bir cephe; kodun varlığı ihlal değil, ama
tarayıcının bunları "veri dışarı çıkışı" diye işaretlemesi doğru — çünkü
öyleler. Aynı şekilde 5 adet "Internal Network Request" (SSRF) bulgusu
`localhost:11434` (Ollama) çağrıları.

**Öneri:** İşlem yok; park durumu zaten koruyor.

---

## K5 — 3. TARAF SKILL BULGULARI (graphify)

| Bulgu | Konum | Şiddet |
|---|---|---|
| Tool Parameter Abuse (`rm -f ...`) | `graphify/references/update.md:198` + 6 yer | HIGH |
| Anti-Refusal Statement (*"without warning"*) | `graphify/SKILL.md:755` | HIGH |
| Unrestricted Tool Access | `graphify/SKILL.md` | MEDIUM |
| Autonomous Decision Making | `graphify/SKILL.md`, `references/add-watch.md` | MEDIUM |

**Değerlendirme:** Bunlar **bizim kodumuz değil** — kurulu 3. taraf skill.
`rm -f` çağrıları graphify'ın kendi ara dosyalarını temizliyor. "Anti-Refusal"
bulgusu, skill metninde modele "uyarmadan şunu yap" denmesi; SkillSpector
bunu prompt-injection sınıfında sayıyor ve **haklı** — bir skill metni
modelin davranışını değiştirir.

**Bağlam:** Daha önceki denetimde `superpowers`'ın her oturum başında
`<EXTREMELY_IMPORTANT>` çerçeveli metin enjekte ettiğini kaydetmiştim.
graphify de aynı sınıfta. **Kurulu her skill, denetlenmemiş bir davranış
yüzeyidir.**

**Ahmet'e soru:** graphify güncellendiğinde bu metin yeniden taranacak mı,
yoksa bir kereye mahsus mu güveniyoruz?

---

## K6 — Hafıza manipülasyonu (1 HIGH)

**Konum:** `agents/retrieval_priority.py:9` — desen: *"replace Memory"*

**Değerlendirme:** [EMİN DEĞİLİM] Muhtemelen bir docstring/yorum eşleşmesi,
gerçek bir hafıza zehirlenmesi değil. Ama hafıza katmanı bu hafta canlıya
alındığı için (`memory/life_graph.py`) **elle bakılmayı hak ediyor**.

---

## K7 — Kirli veri akışı (2 MEDIUM, "Tainted flow")

`agents/memory_scorer.py:113` ve `tools/tools.py:97` — dosyadan okunan
içerik doğrudan dosyaya yazılıyor. Kendi başına zafiyet değil, ama
`memory/` katmanında okunan içerik **konuşmadan** geliyorsa, doğrulanmadan
yazılan bir yol demektir.

---

## Ahmet'e karar listesi

1. **K1** — `run_python_code` aracı kalsın mı? Kalacaksa `safe_globals`
   denetlenmeli (ayrı kart).
2. **K3** — `auto_updater.py` canlı mı, ölü mü?
3. **K5** — Kurulu skill'ler (graphify, superpowers, impeccable) güncellendiğinde
   yeniden taranacak mı? Öneri: `graphify update` sonrası SkillSpector koşan
   bir kontrol.
4. **K6** — `retrieval_priority.py:9` elle bakılsın.

**Ham JSON raporları:** `automation/_ss_raw/` (5 dosya, git'e eklenmedi).
