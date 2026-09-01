# JARVIS — DURUM PANOSU

> **Bu dosya "nerede kaldık" sorusunun TEK cevabıdır.**
> Dağınık roadmap dosyalarından (REALITY_OS, BACKLOG, roadmap_state.json,
> BLACKBOX, AUTONOMY_LOG) derlenmiştir. Her satır kaynağıyla birlikte.
>
> **Oluşturma:** 2026-08-26 · Kaynak taraması: 5 roadmap dosyası + git geçmişi + BLACKBOX

---

## 🔴 EN ÖNEMLİ: EYLÜL TARİHİ ROADMAP'İ ÇAKIŞTIRIYOR

Ahmet **eylülün 1-2. haftası** akıllı ev komponentlerini alacak (ABD'den sipariş verildi).

Ama `JARVIS_BACKLOG.md`'nin kendi sıralaması şöyle:

```
J0B (ses) → J1 (hafıza) → J2/J5 (EV OTOMASYONU) → J4 → J6
             ↑                    ↑
        şu an buradayız      komponentler buraya ait
```

**J2/J5'in giriş kapısı: "J1 complete".** Yani kâğıt üzerinde ev otomasyonu
**iki sprint uzakta** ve donanım 1-2 hafta içinde geliyor.

Üstelik J2/J5'in yazılı bir donanım şartı var:
> *"HA dedicated box provisioned (**NOT this Windows PC**)"* — ayrı bir Linux kutusu.

**Bu bir çelişki ve Ahmet'in karar vermesi gereken ilk şey bu.** Seçenekler §6'da.

---

## 1. NEREDE OLDUĞUMUZ — TEK BAKIŞTA

| Sprint | Konu | Durum | Kanıt |
|---|---|---|---|
| **J0A** | Ses adaptör iskeleti (default-off) | ✅ BİTTİ | Codex PASS, `591ded854`+ |
| **BLACKBOX-0** | Append-only denetim kaydı | ✅ BİTTİ | `fa204fc41` "feature frozen" |
| **LOOP-0A…0E** | Makine kapısı + Piper Faz A | ✅ BİTTİ | BLACKBOX `sequence=6` PASS |
| **J0B** | Gerçek TTS + Piper subprocess | 🟡 **YARIM** | Faz A bitti, **Faz B hiç koşmadı** |
| **J1** | Hafıza yükseltme (BGE-M3 + MemPalace) | ⬜ BAŞLAMADI | giriş kapısı: J0B bitmeli |
| **J2/J5** | **Ev otomasyonu + ESP32 uydular** | ⬜ BAŞLAMADI | ⚠️ **komponentler eylülde** |
| **J4** | Gözlemlenebilirlik + HUD | ⬜ BAŞLAMADI | |
| **J6** | LLM taşıma, maliyet, PII | ⬜ BAŞLAMADI | |
| **J7** | OpenHands | ⛔ PARK | bilinçli |

### Eski faz sistemi (roadmap_state.json — 14 adım)
13 `done`, 1 `in_progress`. **`pending` adım YOK.**

| # | Adım | Durum |
|---|---|---|
| 1-6 | FAZ-0, DEVOPS-verifier, FAZ-1B.13H/audit/13I, FAZ-2-D2 | ✅ |
| **7** | **FAZ-3-E1** Proaktif motor | 🟡 **imza bekliyor** (makine işi bitti) |
| 8-12 | E1-S6A…E (runner, delivery, scheduler şablonu, guard, throttle) | ✅ Codex imzalı |
| 13-14 | FAZ-T1 (Türkçe kalite), FAZ-PHASE2-integration | ✅ |

> ⚠️ **Döngünün yakıtı yok:** `pending` adım olmadığı için otonom sistem
> silahlansa bile **ilk turda durur**. FAZ-4+ adımları yazılmadan otonomi anlamsız.

---

## 2. STRATEJİK HATLAR — kaç ana başlık kaldı

`REALITY_OS_ROADMAP.md` §6'daki hatlar. **Sekiz hattın altısı hiç açılmamış.**

| Hat | Konu | Durum | Vizyondaki karşılığı |
|---|---|---|---|
| **A, B, C1-C4, H, M0** | Çekirdek, güvenlik, hafıza, organ sözleşmesi, dünya modeli | ✅ ~%90 | altyapı |
| **Y** | Local-First Router | 🟡 ~%15 | "önce yerelde çöz" |
| **V** | **Ses** (wake word → STT → butler TTS → barge-in) | 🟡 ~%20 | *motorda konuşmak* |
| **Z** | **Karakter & Varlık** (SOUL.md, presence, anti-tekrar) | ⬜ ~%10 | ***filmdeki JARVIS hissi*** |
| **M** | Dünya + Maker Lab (HA köprüsü, proje zekâsı) | ⬜ ~%25 | *evi yönetmek, atölye* |
| **W** | ESHOT iş zekâsı | ⬜ ~%30 | iş tarafı |
| **D** | Derin araştırma orkestrasyonu | ⬜ ~%40 | *"kuantum çalış"* |
| **G1** | Model Benchmark Lab | ⬜ %0 | *hangi model neyi yapsın* |
| **C4+** | Gözlemlenebilirlik / kara kutu | ⬜ | |
| **I** | Görüş / algı | ⚪ ertelendi | *kapıdaki kişi* |

**Genel olgunluk (roadmap'in kendi tahmini):** çalışan-MVP ~%70 · tam "Reality OS" hayali ~%38

### Vizyon backlog'undaki YENİ hatlar (roadmap'te yoktu, 23.08'de eklendi)
| Hat | Konu | Durum |
|---|---|---|
| **P** | Kapı/kişi farkındalığı (yüz tanıma, karşılama) | ⬜ yeni |
| **S** | Sentinel — ağ güvenliği, sızma tespiti | ⬜ yeni |
| **R** | Uzaktan erişim + kask modu | 🟡 R0 (Tailscale) **zaten var** |

---

## 3. TEK SIRADAKİ ADIM — J0B Faz B

**Ne:** Piper'ın gerçek komutunun **elle** çalıştırılması, ilk sesin ölçülmesi.

**Neden duruyor:** `human_required`. Ahmet'in ayrı, açık onayı gerekiyor.
Faz A (komut planlayıcı) bitti ve Codex PASS aldı (BLACKBOX `sequence=6`),
ama **gerçek Piper hiç çalıştırılmadı**, gerçek `.wav` hiç üretilmedi.

**Ahmet'in yapması gerekenler** (`JARVIS_BACKLOG.md` J0B insan kapısı):
1. `requirements-voice.txt`'i sabitle (`pip show` ile sürümleri oku)
2. `pip install -r requirements-voice.txt` çalıştır
3. Model indirmelerini onayla
4. `py -3.11 scripts/j0_voice_loop.py --real-mic` çalıştır, ilk ses gecikmesini raporla

> **Bu adım atılmadan J1 başlamaz, J1 başlamadan J2/J5 (ev otomasyonu) başlamaz.**
> Eylül tarihi düşünülünce bu zincirin en kritik halkası.

---

## 4. AÇIK KARARLAR — Ahmet'in vermesi gerekenler

### Otonomi sözleşmesi (`AUTONOMY_CHARTER_PROPOSAL.md`)
| Madde | Durum |
|---|---|
| §1.1 Sınırlı zincir | ✅ seçildi (23.08) |
| §6 Ayrı çöp Gmail | ✅ seçildi — ⏸ hesap **henüz açılmadı** |
| §2 Roadmap denetimi | ✅ yapıldı |
| §1.2 Auto-fix retry (3 deneme) | ⏸ imza bekliyor |
| §5 Codex review metni | ✅ **onaylandı (26.08)** — `CODEX_REVIEW_TALIMATI.md` |
| §8.5 Orchestrator parklanma sebebi | ⏸ Ahmet hatırlıyor mu? |

### Roadmap denetimi (`ROADMAP_AUDIT.md` §8)
| # | Karar | Öneri |
|---|---|---|
| K1 | Mevcut `orchestrator.py` yeniden kullanılsın mı? | **Evet** — 581 satır, güvenlik varsayılanları sözleşmeyle uyumlu; sadece maker'ı Claude+Codex yap |
| K2 | Parklanma sebebi | ✅ **Claude araştırdı** — belgelenmiş sebep yok, öncelik kayması görünüyor |
| K3 | FAZ-3-E1'in 5 insan kriteri onaylansın mı? | makine işi bitti, imza eksik |
| K4 | E1-S4 → `HUMAN_NEEDED.md` Resolved'a taşınsın mı? | **Evet** — roadmap 3 gün daha yeni ve ayrıntılı |
| K5 | Letta maddesi kapatılsın mı? | **Evet** — çelişki yok, ifade düzeltmesi |
| K6 | **FAZ-4+ adımları hangi kaynaktan?** | **en büyük kalem** |

---

## 5. BİLİNEN ÇELİŞKİLER (yönetişim)

| # | Çelişki | Durum |
|---|---|---|
| 1 | **Letta**: HARVEST_MAP "runtime reddedildi" vs REALITY_OS "adopt candidate" | ✅ **çelişki değil** — biri runtime'ı reddediyor, diğeri deseni ödünç alıyor. İfade düzeltmesi yeter |
| 2 | **HUMAN_NEEDED ↔ roadmap_state** (E1-S4) | ✅ çözüldü — roadmap 3 gün daha yeni, imzalı, ayrıntılı |
| 3 | **Auto-fix retry**: `AUTONOMY_RULES.md` §4 "3 denemeye kadar" vs `CLAUDE.md` §9 "NOT APPROVED" | ⏸ **yeni bulundu** — iki dosya zıt, imzadan sonra hizalanmalı |
| 4 | `roadmap_state.json` "2 aydır güncellenmemiş" iddiası | ✅ **yanlıştı** — `updated` alanı bayat, içerik 06-28'e kadar canlı |
| 5 | **HA/Wyoming**: `wyoming-satellite` arşivlendi, halefi ESPHome protokolüne geçti | ⏸ J2/J5 kararını etkiler |
| 6 | **Piper GPL-3.0** — subprocess temiz, in-process linkleme değil | ⏸ J0B öncesi netleşmeli |
| 7 | **`codex_denetle.ps1` verdict kapısı** — yankilanan talimattaki "BLOCKER" kelimesi her denetimi BLOCKER gösteriyordu | ✅ **düzeltildi (27.08)** — `codex_verdict.ps1` + `tests/test_codex_verdict.py` (10 test) |

---

## 6. 🔴 EYLÜL ÇAKIŞMASI — seçenekler

**Sorun:** donanım 1-2 hafta içinde geliyor; roadmap ev otomasyonunu iki sprint
sonraya koyuyor ve ayrı bir Linux kutusu şart koşuyor.

| Seçenek | Ne demek | Bedeli |
|---|---|---|
| **A — Sırayı koru** | J0B Faz B → J1 → J2/J5. Komponentler kutuda bekler. | Donanım 1-2 ay atıl kalır |
| **B — J2/J5'i öne al** | Ev otomasyonunu J1'den önce yap. Ses ve hafıza sonra. | Roadmap'in kendi sıralaması bozulur; ama donanım gelince hazır oluruz |
| **C — Paralel** | J0B Faz B + J2/J5 hazırlığı birlikte. J1'i J2/J5 sonrasına al. | En hızlısı; iki cephe aynı anda, dikkat bölünür |

**Claude'un önerisi: B.** Gerekçe: donanımın geliş tarihi **bizim kontrolümüzde
değil**, ama J1 (hafıza yükseltmesi) her zaman yapılabilir. Kontrol edemediğin
kısıta göre planlanır. Ayrıca J2/J5 zaten Airfel klimalarıyla **kısmen çalışıyor**
— iki ünite ESPHome üzerinden okunuyor ve kumanda ediliyor, panel ayakta.
Yani sıfırdan başlamıyoruz.

**Ama önce cevaplanması gereken:** HA için ayrı Linux kutusu var mı? Yoksa
alınacak mı? (Raspberry Pi 4/5 yeterli.) Bu, B seçeneğinin ön koşulu.

---

## 7. ELDEKİ ÇALIŞAN VARLIKLAR (sıfırdan başlamıyoruz)

| Varlık | Durum |
|---|---|
| `scripts/orchestrator.py` (581 satır) | otonom döngü **yazılmış**, güvenlik varsayılanları sözleşmeyle uyumlu |
| `scripts/verifier_runner.py`, `escalation_policy.py`, `mutation_gate.py` | destek katmanı hazır |
| `agents/` (~40 modül) | cascade, cost-ledger, memory katmanları, proactive motor |
| **Airfel klima hattı** | 2 ünite fiber'de, 18/18 kontrol, bakım teşhisi sensörleri, panel + geçmiş |
| **Tailscale** | uzaktan erişim **zaten çalışıyor** (R0 tamam) |
| **Codex CLI** | 0.150.0, giriş **doğrulandı** (27.08, gerçek `codex exec` çağrısıyla). `codex review` uçtan uca **henüz tamamlanmadı** — ilk iki deneme sarmalayıcı hatasından öldü |
| BLACKBOX-0 | append-only denetim kaydı, 6 event |

---

## 8. KAYNAK DOSYALAR

| Dosya | Ne için |
|---|---|
| `docs/JARVIS_BACKLOG.md` | J-serisi sprint sıralaması (**güncel operasyonel plan**) |
| `docs/strategy/JARVIS_v5_REALITY_OS_ROADMAP.md` | stratejik hatlar, OSS harvest map, frenler |
| `roadmap_state.json` | makine-okunur adım durumu (orchestrator bunu okur) |
| `automation/ROADMAP_AUDIT.md` | 23.08 denetimi, 6 karar |
| `automation/AUTONOMY_CHARTER_PROPOSAL.md` | otonomi sözleşmesi (imzasız) |
| `docs/JARVIS_VISION_BACKLOG.md` | P/S/R yeni hatları |
| `docs/OSS_HARVEST_REPORT_2026-08.md` | 10 proje derin analizi |
| `docs/HARDWARE_AND_LOCAL_LLM_RESEARCH.md` | donanım kararı, model seçimi |
| `automation/BLACKBOX.jsonl` | append-only sprint denetimi |
