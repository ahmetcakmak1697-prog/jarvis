# KART — İkinci anayasayı kapat

**Durum:** Açık · **Karar:** Ahmet, 2026-09-05 — seçenek (b) + (c)
**Bulgu:** `graphify install`, 2026-09-05 16:37:41'de üç şey üretti

Küçük iş, kod yok. Tek amacı: **anayasanın tek kopyası kalması.**

---

## Ne oldu

`graphify install` makinede bulduğu her ajan koşumuna kendini kurdu:

| Dosya | Ne | Karar |
|---|---|---|
| `.agents/skills/graphify/` | Graphify skill'i v0.9.52 (`.claude/skills/`'dekiyle aynı sürüm) | **gitignore** |
| `.codex/hooks.json` | Graphify `PreToolUse` kancaları | **gitignore** |
| `.codex/config.toml` | Telemetri kapatma | **gitignore** |
| `AGENTS.md` | **`CLAUDE.md`'nin kopyası** (Claude→Codex adları değişmiş, 5 satır fark) | **işaretçiye çevir, commit et** |

**Neden acele:** `AGENTS.md` anayasanın ikinci kopyası. Şu an aynılar ama bu
tesadüf — `CLAUDE.md` en son 15:52'de düzenlendi, `AGENTS.md` 16:37'de üretildi.
`CLAUDE.md` §13.2'deki taban sayısını neredeyse her turda güncelliyoruz; ilk
güncellemede kopya sessizce eskir.

Bu, `CLAUDE.md` §12'nin belgelediği hata sınıfının aynısı (Letta çelişkisi,
HUMAN_NEEDED ↔ roadmap_state, auto_runner). Farkı: bu sefer çelişecek olan
**anayasanın kendisi**.

---

## 1. `.gitignore` — üçüncü parti araç çıktısı

`.agents/` ve `.codex/` eklensin. Emsal dosyada zaten var: satır 123'te
`.claude/skills/` (commit `e6efc64`, "third-party skills"). Bu ikisi de
bugün tamamen araç tarafından üretildi, insan eliyle yazılmış içerik yok.

**Dosyanın kendi biçemine uy:** `.gitignore` girdilerinin çoğunda *neden*
ignore edildiğini anlatan bir yorum satırı var (bkz. satır 132-134). Aynısını
yap — bir sonraki oturum "bu neden ignore edilmiş" diye sormasın.

## 2. `AGENTS.md` — kopya değil işaretçi

16910 baytlık kopyanın yerine **kısa bir işaretçi** yaz. İçeriğinde şunlar
olsun, bu sırayla:

- Bu reponun anayasası **`CLAUDE.md`**'dir; kurallar orada, burada değil.
- Bu dosya bilerek kopya **değildir** — iki kopya kaçınılmaz olarak sapar
  ve anayasa sapamaz.
- **Uyarı, en önemli satır:** `graphify install` yeniden çalıştırılırsa bu
  dosyayı `CLAUDE.md`'nin tam kopyasıyla **tekrar üzerine yazar.** Öyle
  olursa doğru davranış onu yine işaretçiye indirmektir, kopyayı
  güncellemek değil.
- Tarih ve gerekçe kaydı: 2026-09-05, Ahmet kararı, bu kart.

**Dosya commit EDİLECEK** (ignore edilmeyecek). Sebebi şu ve kartın en ince
noktası: `AGENTS.md` takip edilirse, graphify onu bir daha üretiğinde
`git status` **büyük bir diff gösterir**. Yani sessiz sapma, gürültülü bir
uyarıya dönüşür. Ignore edilseydi kopya geri gelir ve kimse görmezdi.

---

## Yasaklar

1. **`CLAUDE.md`'ye dokunma.** Tek doğruluk kaynağı o; bu kart onu değiştirmez.
2. **Kod yok.** `eval/`, `agents/`, `agent/`, `tools/` — hiçbirine dokunma.
3. `.agents/` ve `.codex/` içeriğini **silme**, yalnız ignore et. Graphify'ın
   kancaları çalışıyor olabilir; dosyayı kaldırmak aracı bozar.
4. `.opencode/` ve `.claude/` **bu kartın konusu değil** — dokunma.

## Bitti sayılma ölçütü

- `git status` temiz: `.agents/`, `.codex/` artık görünmüyor.
- `AGENTS.md` takip ediliyor, kısa, ve içinde graphify uyarısı var.
- `AGENTS.md` ile `CLAUDE.md` arasında artık kural tekrarı **yok** —
  `diff` çıktısı "iki farklı belge" demeli, "aynı belgenin iki kopyası" değil.
- `pytest tests -q` yeşil (iki sırada), `ruff check .` ≤ 293, taban testi 49.
- Commit: yalnız isimli dosya. Push yok. **Bittiğinde dur.**
