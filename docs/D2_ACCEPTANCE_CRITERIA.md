# D2 — Web Research Kullanım ve Kalite: Kabul Kriterleri
*Versiyon: 1.0 — P0.2 ile oluşturuldu*

---

## Hedef

D1'de kurulan web research altyapısını (WebResearchPolicy, SourceScorer, MemoryCandidateQueue, AuditLogger) **kullanıma açmak ve kalite standartlarını ölçülebilir hale getirmek.**  
Demo noktası: Telegram'dan `/web <soru>` komutu, kaynaklı + candidate queue'ya düşen + audit'e yazılan cevap döndürür.

---

## D2.1 — Telegram /web komutu

| # | Koşul | Ölçüm |
|---|-------|-------|
| 1 | `/web <soru>` komutu sadece izinli `user_id`'den çalışır | Yetkisiz ID'den gönderilince "yetkisiz" yanıtı döner |
| 2 | Komut tetiklenince `web_research_policy.py` karar verir | Audit log'da `web_policy_decision` eventi görünür |
| 3 | Sonuç `memory_candidates.json`'a `pending_review` olarak düşer | `memory_candidates.json`'da `status: "pending_review"` kayıt var |
| 4 | Audit log'a `web_candidate_queued` yazılır | `audit_log.jsonl`'in son satırında ilgili event |
| 5 | Cevap Telegram'a en az 1 kaynak adıyla döner | Mesaj içinde `Kaynak:` veya `[1]` ibaresi var |

---

## D2.2 — Policy + Sanitizer

| # | Koşul | Ölçüm |
|---|-------|-------|
| 1 | Yerel dosya/kod sorular? web'e ??kmaz | local_block senaryolar?n?n 5/5'i bloklan?r |
| 2 | G?ncel bilgi isteyen sorular web'e gider | web_allow senaryolar?n?n en az 9/10'u izin al?r |
| 3 | `.env`, şifre, token içeren query web'e gönderilmez | `eval/d2_web_research_cases.json`'daki hassas veri senaryoları %100 bloklanır |
| 4 | Hassas anahtar kelimeler sanitize edilir | `TELEGRAM_BOT_TOKEN`, `JARVIS_PASSWORD_HASH` web sorgusuna girmez |

---

## D2.3 — Candidate Queue (mevcut altyapı üstüne)

| # | Koşul | Ölçüm |
|---|-------|-------|
| 1 | Web sonucu otomatik hafızaya **yazılmaz** | Cevap sonrası `conversations.json`'da yeni `allow_vector: true` kayıt yok |
| 2 | Candidate `pending_review` olarak oluşur | `memory_candidates.json` count +1 |
| 3 | `/mem_approve <id>` ile onaylanınca vector memory'e gider | Approve sonrası `audit_log.jsonl`'de `memory_candidate_stored` |
| 4 | `/mem_reject <id>` ile reddedilince silinir / `rejected` kalır | `status: "rejected"` güncellenir |

---

## D2.4 — Rate limit + Cache

| # | Koşul | Ölçüm |
|---|-------|-------|
| 1 | Aynı sorgu 5 dakika içinde tekrar edilirse cache'den döner | `audit_log.jsonl`'de `web_cache_hit` eventi |
| 2 | Dakikada N'den fazla web isteği bloklanır | (N değeri `.env`'de `WEB_RATE_LIMIT`, varsayılan 10) |
| 3 | Günlük limit aşılınca "kredi bitti" mesajı döner | `memory/search_credits.json` kontrolü |

---

## D2.8 — Citation enforcement

| # | Koşul | Ölçüm |
|---|-------|-------|
| 1 | En az 2 bağımsız güvenilir kaynak varsa `[VERIFIED]` etiketi | Cevap başında veya sonunda görünür |
| 2 | Tek kaynaklı cevaplarda `[TEK KAYNAK]` uyarısı | Mesajda açıkça belirtilir |
| 3 | Kaynak yoksa "araştırma sonucu bulunamadı" döner | Uydurma olmaz |

---

## D2.9 — Cross-source verification

| # | Koşul | Ölçüm |
|---|-------|-------|
| 1 | İki kaynak çelişiyorsa "kaynaklar çelişiyor" uyarısı | Cevap içinde açık uyarı |
| 2 | Yüksek güvenilirlik skorlu kaynaklar önce gelir | `source_scores` sıralaması SourceScorer'a uygun |

---

## D2.10 — Research modları

| Mod | Tetikleyici | Davranış |
|-----|------------|----------|
| Quick | `/web` | 1 kaynak, hızlı |
| Standard | `/webx` veya varsayılan | 2-3 kaynak |
| Deep | `/webd` | 4+ kaynak, çapraz doğrulama |

---

## Regression (D2 sonrası mevcut testler hâlâ geçmeli)

```powershell
python .\tests\run_smoke_suite.py
```

Beklenen çıktı (değişmemeli):
```
A1 smoke OK
A5 smoke OK
Efendim, temel sistem bütünlüğü doğrulandı.
```

---

## Demo senaryosu (D2 tamamlandı sayılır)

1. Telegram'dan `/web 2026 İzmir hava durumu bugün` yaz
2. Cevap gelir: en az 1 kaynak adı var, `[VERIFIED]` veya `[TEK KAYNAK]` etiketi var
3. `memory_candidates.json`'da yeni `pending_review` kayıt görünür
4. `audit_log.jsonl`'in son satırında `web_candidate_queued` var
5. `/mem_candidates` ile listele, ID'yi al, `/mem_approve <id>` ile onayla
6. Audit log'da `memory_candidate_stored` görünür
7. Smoke suite hâlâ yeşil

Bu 7 adımın hepsi geçerse D2 kapanır.

---

## Kabul edilmez durumlar

- Web sonucu onay almadan `allow_vector: true` ile hafızaya yazılırsa → D2 AÇIK
- Hassas veri (token, şifre) web sorgusuna girerse → D2 AÇIK
- Yetkisiz kullanıcı `/web` çalıştırabilirse → D2 AÇIK
- Smoke suite kırılırsa → D2 AÇIK (önce regression düzeltilir)
