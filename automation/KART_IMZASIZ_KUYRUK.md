# KART — İmzasız iş kuyruğu: önce listele, sonra sırayla bitir

**Kime:** Claude Code (VS Code) · **Veren:** Ahmet, 2026-09-08

Ahmet'in derdi net: her turda "sıradaki iş ne" diye düşünmek zorunda kalmak
istemiyor. Çözüm otonomi değil, **yazılı kuyruk** — o zaman devam etmek tek
satır yapıştırmaktan ibaret olur.

> **Otomatik zincirleme YOK** (CLAUDE.md §9). Her madde bitince durursun.
> Ama sıradaki madde zaten yazılı olduğu için Ahmet'in düşünmesi gerekmez.
> Tam otonomi `automation/AUTONOMY_CHARTER_PROPOSAL.md`'nin konusu ve o belge
> **imzasız**; imzalanana kadar bu kart onun yerine geçmez.

---

## ADIM 1 — Kuyruğu üret (ilk teslimat)

`automation/IMZASIZ_IS_KUYRUGU.md` yaz. İçinde **yalnız Ahmet'in kararını
GEREKTİRMEYEN** işler olacak, her biri için "neden imza gerekmiyor" kanıtıyla.

Kaynakları tara ve maddeleri **oradan çıkar**, uydurma:

- `docs/JARVIS_ENVANTER.md` — 13 yetim modül, 24 yalnız-test modülü,
  "ölçülemedi" bölümü, çelişki listesi
- `automation/CODEX_DENETIM_2026-09-06.md` ve
  `automation/CODEX_A_DOGRULAMA_2026-09-06.md` — kapanmamış CONCERN'ler
- `FAILURES.md`, `automation/HUMAN_NEEDED.md`
- Bugünün commit mesajlarında **"KAPSAM DIŞI"** / **"düzeltilmedi"** diye
  bilerek bırakılmış her şey — bunlar zaten bilinen, adı konmuş borçlar

**İmza gerektiren nedir** (bunları kuyruğa ALMA, `AHMET_ONAYI_BEKLEYENLER.md`'ye
yaz):
- Bir şeyi **silmek** (§3: gör, söyle, silme)
- `config/runtime_profiles.json`, `.env`, gerçek yapılandırma dosyaları
- Park edilmiş cepheler ve komşuları (`jarvis_server.py`, `auto_runner.py`,
  orchestrator, scheduler, Telegram auto-send)
- Ölçüm tanımını değiştirmek (kalite tabanını oynatan her şey)
- Yeni bağımlılık, yeni sağlayıcı, yeni teknoloji
- Mimari yön değişikliği (ör. iki hattı birleştirmek)

**Bildiğim başlangıç adayları** — kuyruğu bunlarla sınırlama, ama atlama da:

| İş | Neden imza gerekmiyor |
|---|---|
| `_detect_tool` sorguyu bozuyor: "son haberler nedir" → "son ler nedir" arama motoruna gidiyor | Düpedüz hata; doğru davranış tartışmalı değil |
| `LocalJarvisAgent.__init__` `self.memory`'yi iki kez atıyor (biri ölü) | Ölü atama, davranış değişmez |
| `agents/api_executor.py`, `tests/conftest.py`, `tests/test_api_executor.py` **BOM (U+FEFF)** taşıyor — AST tarayıcısı okuyamıyor | CLAUDE.md §5'in adını koyduğu tuzak; Python dosyası BOM taşımaz |
| `ruff` borcu 283 | Taban "artmasın" diyor; **azaltmak ayrı bir kart** olarak zaten yazılı |
| `test_mutation_gate.py::test_weak_tests_leave_survivor` yanıp sönüyor | Kapı testinin güvenilirliği; kök neden bulunmalı |
| Envanterdeki 13 yetim modülün **neden** yetim olduğunu araştır | Araştırma imza gerektirmez; **silmek** gerektirir |

Her madde şunları taşısın: **dosya:satır** · neden imzasız · kabul ölçütü ·
tahmini büyüklük (küçük/orta/büyük).

Kuyruğu **etki sırasına** diz, kolaylık sırasına değil.

## ADIM 2 — Kuyruğu sırayla bitir

Kuyruk yazıldıktan sonra **en üstteki maddeden başla** ve şu döngüyü uygula:

1. Maddeyi oku, kapsamını daralt.
2. **Önce düşen testi yaz, kırmızı olduğunu GÖR.**
3. Kaynağı düzelt.
4. Kapı: `pytest tests -q` **iki sırada**, `ruff check .` **≤ 283**,
   taban testi **49**.
5. Commit — yalnız isimli dosya, mesajda ne ölçüldüğü yazılı.
6. Kuyrukta o maddeyi **✅ kapandı + commit hash** diye işaretle.
7. **DUR.** Sıradakine geçme.

Ahmet döndüğünde tek satır yazacak: *"kuyruktan devam et"*. Sıradaki madde
zaten yazılı olduğu için düşünmesi gerekmeyecek.

---

## Sınırlar

**Codex şu an `tools/`, `memory/`, `agents/`, `agent/jarvis_agent.py`
içinde** (B09 düzeltmesi + B10). O bitene kadar oralara dokunma; kuyruğa
alabilirsin ama "Codex'te — beklemede" diye işaretle.

Bir madde başladıktan sonra imza gerektirdiği anlaşılırsa: **dur**, maddeyi
`AHMET_ONAYI_BEKLEYENLER.md`'ye taşı, kuyrukta sebebini yaz, sıradakine geç
**değil** — dur ve söyle.

Auto-fix retry yok: bir kontrol BLOCKER/CONCERN verirse kendi başına
düzeltip tekrar deneme, yaz ve dur (§9).

Push yok.

## Bitti sayılma ölçütü (ADIM 1 için)

- `automation/IMZASIZ_IS_KUYRUGU.md` var; her madde kanıtlı ve
  kabul ölçütlü.
- İmza gerektiren hiçbir iş kuyrukta **değil**.
- Kuyruk etki sırasına dizili.
- Kuyruk commit'lendi, sonra **ilk maddeye** geçildi.
