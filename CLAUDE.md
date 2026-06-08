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
