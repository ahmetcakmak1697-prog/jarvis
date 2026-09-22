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

### 7.0 Yön değişikliği — "yerel-önce" bitti, yerine "işe göre yerleşim" (2026-09-09, Ahmet imzalı)

**Eski madde:** *"Yerel-önce cascade: cache → RAG → local LLM → (sufficiency) →
cost-ledger kapısı → external."* Bu cümle artık **yürürlükte değil.** Silinmedi,
burada duruyor: yerine ne geldiğini anlamak için neyin bırakıldığı görünmeli.

**Neden değişti — ölçüldü, tercih edilmedi:**

| | llama3.1 (yerel) | DeepSeek (bulut) |
|---|---|---|
| 64 vaka | **49/64** | **54/64** |
| turkish | 10/15 | **14/15** |
| düşme sebebi | tekrar 6, prompt sızıntısı 7 | kesilme 4, kalıp 3 |

Fark 5 vaka ve A11'in ölçtüğü ±1 oynaklık bandının **dışında**. Kritik olan
sebep dağılımı: yerel modelin kusurları **modelin tavanı** (dejenerasyon,
sızıntı), DeepSeek'inkiler **bizim ayarımız** (token bütçesi, persona).
Yerelin tavanı görüldü ve 8 GB'a sığan daha iyisi yok — Turkish-Gemma 54/64
alıyor ama tepe VRAM 7076 MB. Kaynak:
`automation/KALITE_deepseek_deepseek-chat_20260909-2208.json`.

**Yerine gelen kural — yerleşim ideolojiyle değil, işin gereğiyle seçilir:**

| İş | Nerede | Neden (ölçülmüş gerekçe) |
|---|---|---|
| **Ev kontrolü** (ışık, perde, klima) | **Yerel + deterministik** | Gecikme: bulut gidiş-dönüşü ~500-2000 ms, kural ~5 ms. Erişilebilirlik: internet kesikse ev çalışmalı. Bu bir zekâ işi değil, eşleştirme işi. |
| **Günlük sohbet, araştırma** | **Bulut (DeepSeek)** | Ölçülen 5 vakalık kalite farkı; yerelin tavanı donanımla sınırlı. |
| **Zor iş** | **Tek bir üst katman** | Hangisi olduğu **ölçülmeden** seçilmez. Çok katmanlı kaskad varsayılan değildir (7.0a). |

**7.0a — Çok modelli kaskad varsayılan DEĞİLDİR.** Yeni bir katman eklemeden
önce iki şey ölçülür: (1) aynı 64 vakada gerçek fark, (2) tek modelde `effort`
ayarının aynı işi yapıp yapmadığı. Gerekçe: prompt önbelleği **modele bağlıdır**
ve JARVIS'in sistem prompt'u büyük ve sabittir; N modele bölmek N ayrı önbellek
demektir ve kaskadın kazandırdığını önbellek kaybı geri alır.

**7.0b — Maliyet kapısı artık zorunlu.** Yerel çağdayken bütçe kapısının bağlı
olmaması zararsızdı; bulut temelli bir asistanda değildir. Ölçüldü (Codex,
2026-09-09): `CostLedger(daily_limit=0)` **"unlimited"** dönüyor
(`agents/cost_ledger.py:78`) ve `APIBudgetGate` üretim yolunda enjekte
edilmiyor. **Pahalı bir sağlayıcı, kapı bağlanmadan bağlanmaz.**

**7.0c — (sufficiency) halkası hâlâ YOK.** Ölçüldü: `ModelCascade.select()`
kural tabanlıdır, **0 LLM çağrısı** yapar (p50 0,0016 ms). Yani "yerele sor →
cevabı değerlendir → yetmezse yukarı çık" diye bir mekanizma kurulmamıştır;
olan şey soruya bakıp baştan seviye seçmektir. Katman eklemek bu halkayı
kurmaz — adı "cascade" olan bir `if` bloğuna katman eklemek, yanılmanın yolunu
çoğaltır.

**Bilerek kabul edilen bedel:** internet kesikse sohbet ve araştırma durur;
ev kontrolü durmaz. Geri dönülebilir — yerel modeller kurulu kalır, terazi
ikisini de ölçer.

### 7.1 Değişmeyenler

- İki eksenli güvenlik: veri sınıfı (ne dışarı çıkar) × güven (içerik nereden). **Untrusted içerik asla otomatik kalıcı hafıza olmaz → approval queue.** Bulut temelli mimaride bu madde **daha kritiktir**, daha az değil: artık her sohbet turu bir egress'tir.

### 7.1a Kalıcı hafızaya yazma — Ahmet'in kararı (22.09.2026)

Kendi sözleriyle: *"benim istediklerimi hafızaya alsın, kalıcı tarafa
gereksiz şişme olmasın, güzel ve önemli şeylerde sorsun ya da benim bunu
kalıcı hafızaya yaz dediklerimi yazsın."*

Yürürlükteki kural, üç hâl:

1. **Varsayılan: YAZMAZ.** Sohbet turu kendiliğinden kalıcı hafızaya girmez.
2. **Ahmet söylerse yazar.** "Bunu kalıcı hafızaya yaz" türü açık bir
   talimat tek yeterli koşuldur.
3. **Önemli görünen şeyi SORAR.** Sessizce kaydetmez, sessizce atmaz da;
   adaylığa alır ve Ahmet'e sorar.

**Bu mimari zaten kurulu, yeniden yazılmayacak:** `answer_crystallizer`
aday kart üretir ve *"Never writes to VectorMemory"* der;
`episodic_buffer` ve `knowledge_card_editor` de yazmaz; yalnız
`knowledge_card_promoter` **onaylanmış** kartı `tools/vector_memory.py`
içindeki `VectorMemory`'ye geçirir. Yeni bir yazma yolu eklemek bu hattı
baypas etmektir.

**Ayrım korunmalı:** SQLite sohbet geçmişi üzerine kurulan vektör
**indeksi** türetilmiş bir arama yapısıdır (silinip yeniden kurulabilir),
kalıcı hafıza değildir. İndeks kurmak bu kuralın kapsamında değildir;
`VectorMemory`'ye yazmak kapsamındadır.
- Deterministik routing = güvenlik özelliği. Vector skor *girdi*, karar değil. Router kararı `confidence` + `route_reason` ile C4'e yazılır.
- **Human override her katmandan üstün:** kullanıcı her an dur/iptal/unut/yerel-kal diyebilir.
- ESHOT: pandas hesaplar, LLM anlatır; kurallar Rules.json'da.
- Model adı koda gömülmez → ModelRegistry. Her veri dosyasında `schema_version`.
- Her blok: küçük patch → test → smoke → git clean → commit → çift review. DoD ile kapat.

---
*Bu dosya repoda `CLAUDE.md` (kök) olarak durur. Cursor için `.cursor/rules/`'a da kopyalanabilir.*

---

## 8. PUSULA

JARVIS'in tek cümlelik hedefi: Ahmet'in "Hey Jarvis, nerede kaldık?" sorusuna
~1.5 saniye içinde, Türkçe sesli ve **repo'nun o anki gerçek durumunu**
yansıtan bir yanıt vermek — uydurma değil, canlı.

His-testi: cevap doğru mu diye anlamak için "bu, repo'yu şu an açıp
`git log` + son BLACKBOX event'ine bakan biri gibi mi konuşuyor?" sorusu
sorulur. Değilse yanıt yanlıştır.

## 9. DEĞİŞMEZ KURALLAR

- `git add -A` yasak; yalnız isimli dosya ekle.
- Push yalnız insan (Ahmet) onayıyla.
- `--dangerously-*` bayrakları (`--dangerously-skip-permissions`,
  `--dangerously-bypass-approvals-and-sandbox`, vb.) kalıcı yasak.
- `.env` / secret dosyalarına dokunulmaz, okunmaz, loglanmaz.
- Auto-fix retry **NOT APPROVED** — bir kontrol BLOCKER/CONCERN verirse
  otomatik düzeltip tekrar denenmez, Ahmet'e gider.
- Otomatik sıradaki-işe-geçiş yok — her adım tamamlandığında durulur,
  bir sonraki adım insan onayı bekler.
- Park edilmiş cepheler (AUTO / orchestrator / scheduler / Telegram
  auto-send) hiçbir isimle, hiçbir gerekçeyle yeniden açılmaz.
- Adopt-over-build: yeni bir şey yazmadan önce olgun açık-kaynak/mevcut
  çözüm var mı diye sorulur (bkz. `automation/LOOP0D_J0B_SAFETY_CONTRACT.md`
  §6 — HA/Wyoming adopt-vs-build örneği).

## 10. MEVCUT DURUM — nereden OKUNUR

> **Bu bölüm bilerek olgu içermez.** Önceki sürümü sabit bir commit hash'i ve
> "aktif cephe" yazıyordu; ikisi de altı hafta içinde eskidi ve her oturumu
> yanlış yönlendirdi. Aynı hatayı `agent/local_agent.py`'de de yaptık: sabit
> yazılmış proje durumu modele "her şey bekliyor" dedirtti (bkz. `FAILURES.md`).
> **Kural: olgu koda ve anayasaya yazılmaz, canlı dosyadan okunur.**

Bir oturuma başlarken durumu şuralardan **oku**:

| Ne | Nereden |
|---|---|
| Son commit'ler, aktif branch | `git log --oneline -10`, `git status` |
| Adımların durumu (tek doğruluk kaynağı) | `roadmap_state.json` |
| İnsan onayı bekleyenler | `automation/AHMET_ONAYI_BEKLEYENLER.md`, `automation/HUMAN_NEEDED.md` |
| Otonom tur kayıtları (append-only) | `automation/BLACKBOX.jsonl`, `automation/AUTONOMY_LOG.md` |
| **Ne sırayla çalışıyoruz, ne ertelendi** | `docs/strategy/CALISMA_SIRASI_KARARI.md` |
| Donanım ve yerel model gerçekleri (ölçülmüş) | `docs/HARDWARE_AND_LOCAL_LLM_RESEARCH.md` |
| Geçmiş tuzaklar | `FAILURES.md` |

**Yavaş değişen doğrular** (bunlar olgu değil, yön):

- Ses hattı **canlı**: mikrofon → faster-whisper → yerel model → Edge TTS.
  `python main.py` ile çalışır. Mikrofon `JARVIS_MIC_DEVICE` ile seçilir.
- Model adları koda gömülmez; `ModelRegistry` + `config/runtime_profiles.json`.
- Persona tek kaynaktan gelir: `agents/persona.py`.
- LOOP-0 zinciri (J0B/Piper) **tarihsel bir cephedir**. Ses hattı Piper'a
  ihtiyaç duymadan Edge TTS ile canlıya alındı; LOOP-0E Phase B hiç
  yürütülmedi ve artık aktif iş değildir. BLACKBOX kayıtları append-only
  disiplini gereği duruyor, silinmedi.

## 11. SIRADAKİ TEK ADIM

Sıra tek bir yerde yazılıdır: **`docs/strategy/CALISMA_SIRASI_KARARI.md`**.
O belge hem sırayı hem *neyin bilerek ertelendiğini* içerir — erteleme yazılı
olmazsa üç gün sonra taze bir öneri olarak geri gelir.

Buraya adım adı yazma. Belgeyi oku, oradaki ilk açık maddeyi al.

Değişmeyen kural: adım `human_required` ise otomatik başlamaz, otomatik
onaylanmaz (§9).

## 12. BİLİNEN AÇIK MADDELER

- **Letta çelişkisi:** `docs/JARVIS_HARVEST_MAP.md` (REJECT tablosu)
  "Letta runtime | Rejected" derken, `docs/strategy/JARVIS_v5_REALITY_OS_ROADMAP.md`
  Letta (MemGPT)'yi "verified, adopt candidate" olarak işaretliyor.
  `docs/JARVIS_v5_MASTER_ROADMAP.md` ise net bir taahhüt vermeden her
  ikisine de referans veriyor. Bu çelişki `automation/LOOP0D_J0B_SAFETY_CONTRACT.md`
  §7'de belgelendi; geçici (provisional) karar: Letta runtime **onaylı
  değil**, yalnızca mimari desen olarak referans alınabilir. Kalıcı
  çözüm için tek bir doğruluk kaynağı dokümanı güncellenmeli — bunu
  Ahmet ayrıca karara bağlamalı.
- **~~HUMAN_NEEDED.md ↔ roadmap_state.json tutarsızlığı~~ — ÇÖZÜLDÜ (2026-09-03).**
  `automation/HUMAN_NEEDED.md` `[2026-06-24] [E1-S4]` maddesini "Pending"
  gösterirken `roadmap_state.json` aynı maddeyi `"verdict": "DONE"`
  (2026-06-27, Ahmet imzalı telefon onayı) diye kaydediyordu. İkisi de
  `_load_project_context()` üzerinden **aynı prompt'u** besliyordu, yani model
  çelişkili iki olgu görüyordu. Madde, kanıtıyla birlikte (komut, imza, Codex
  PASS commit'i `a39db4568`) Resolved bölümüne taşındı. **Pending bölümünde
  artık gerçek madde yok.**
- **~~HA/Wyoming adopt-vs-build kararı~~ — ÇÖZÜLDÜ (2026-09-01).**
  `automation/LOOP0D_J0B_SAFETY_CONTRACT.md` §6 üç seçeneği (A: ayrı,
  B: HA/Wyoming'e devir, C: hibrit) karara bağlanmamış olarak kaydetmişti.
  Ahmet kararı verdi: **her şey bu PC'den döner** — Raspberry Pi yok, ayrı
  sunucu yok. Home Assistant bu Windows makinesinde uygulama olarak çalışır;
  ESP32 uyduları, sensörler ve kameralar **ESPHome** bellenimiyle WiFi
  üzerinden HA ile konuşur; **özel protokol yazılmaz** (§9 adopt-over-build).
  Bilerek kabul edilen bedel: PC kapalıysa ev aptaldır, ve HA + Docker +
  Ollama + Whisper aynı 8 GB kartı paylaşır. Geri dönülebilir — HA
  yapılandırması taşınabilir. Gerekçe ve bağlam:
  `docs/strategy/CALISMA_SIRASI_KARARI.md` §4a.
- **~~auto_runner çelişkisi~~ — ÇÖZÜLDÜ (2026-08-30).** Graphify grafiği,
  `README.md` §10 ve `BOOT_CHECK.md` §11'in `auto_runner.py`'yi desteklenen
  bir akış olarak belgelerken §9'un tüm AUTO cephelerini kalıcı park
  ettiğini AMBIGUOUS bir kenar olarak yakaladı. Çelişki **§9 lehine**
  sabitlendi: §9 DEĞİŞMEZ bir kural, README/BOOT_CHECK ise operasyon
  belgesi — anayasa kazanır. Her iki bölüm de "PARK EDİLMİŞ / ÇALIŞTIRMA"
  banner'ıyla işaretlendi; başlatma komutu geçersiz, yalnızca kaçak süreç
  temizliği geçerli. Bölümler silinmedi (tarihsel kayıt + temizlik gereği).

## 13. YALIN SAVUNMA VE DENETİM ALTYAPISI

### 13.1 Sözleşme Kilidi (Contract Lock)

`tests/contracts/` altındaki her dosya ve her `*.spec.py` dosyası
**salt-okunurdur (read-only)**. Bir test başarısız olduğunda test kodu ASLA
değiştirilemez; yalnızca kaynak kod düzeltilerek testin geçmesi sağlanmalıdır.

Testin kendisinin yanlış olduğu kanısına varılırsa bu bir kaynak-kod düzeltmesi
değil, **sözleşme değişikliğidir**: durulur ve Ahmet'e sorulur. Sözleşmeyi
gevşeterek yeşile boyamak yasaktır.

*[Durum notu, 2026-08-30: `tests/contracts/` dizini ve `*.spec.py` deseni repoda
henüz yok. Kural ileriye dönüktür — ilk sözleşme testi yazıldığı anda yürürlüğe
girer.]*

### 13.2 Yerel Deterministik Kapı

Bir görev "tamamlandı" olarak işaretlenmeden önce terminalde **sırasıyla**
`pytest` ve `ruff check` çalıştırılmalıdır. Testler %100 geçmeden Ahmet'e
"bitti" denilemez.

Bu repoda kapının doğru çalıştırılışı:

```powershell
$env:PYTHONPATH = (Get-Location).Path
& "C:\Program Files\Python311\Scripts\pytest.exe" tests -q
& "C:\Program Files\Python311\Scripts\ruff.exe" check .
```

Neden bu biçim: `.venv` içinde pytest de ruff da kurulu **değil** (ikisi de
sistem Python 3.11'inde); `PYTHONPATH` verilmezse `agents` / `tools` import'ları
daha toplama (collection) aşamasında patlar; kök dizindeki `voice_test.py`
`edge_tts` istediği için tam kök taraması toplama hatası verir, bu yüzden kapı
`tests` dizinine daraltılmıştır.

**Bilinen taban çizgisi (2026-09-11, `auto/opencode-deepseek`):**
`pytest tests` → **1970 geçti / 0 başarısız / 2 xfailed** (iki sırada);
`ruff check .` → **283 bulgu**.

*Önceki kayıt (2026-09-05): 1706 geçti, ruff 293. Silinmedi — sayının
nereden geldiği görünsün diye duruyor. Aradaki testler eklendi, ruff
borcu `agent/` kapsama girince 300'e çıkıp sonra 283'e indi (A12).*

Test hattı **yeşildir**; bu artık bir hedef değil, korunması gereken bir
durumdur. Yeni bir başarısızlık eklemek doğrudan DoD ihlalidir.

Lint borcu (283 bulgu) hâlâ açıktır ve kapatılmamıştır. `ruff check .`
sayısının **artmaması** zorunludur; azaltmak ayrı bir karttır.

**Türkçe kalite takımı — ayrı bir taban (2026-09-03):** `llama3.1:latest`,
64 vaka, **49/64**. Bu sayı `pytest` gibi bir kapı DEĞİL; kalite regresyon
tabanıdır ve koşular arası oynaklık taşır (A11). Daha önce 63/64 yazıyordu:
model aynı, **ölçüm değişti** — sistem prompt'u sızıntısı, tekrar ve
kesilme dedektörleri eklendi, uydurma kapsamı `technical`'a genişletildi.
Eski sayıyla karşılaştırma yapılamaz. Ayrıntı ve eşik gerekçeleri:
`automation/KALITE_TABAN_2026-09-03.md`.

Terazinin üç kusuru 2026-09-05'te kapatıldı (sızıntı korpusundan persona'nın
tırnaklı örnekleri çıktı; yapay zekâ kalıbı ve İngilizce cümle sızıntısı artık
puanlanıyor; uzun anlatım vakaları 1200 token bütçe alıyor). **Taban 49/64
değişmedi** — düzeltmeler kayıtlı llama koşusunun hiçbir vakasına dokunmadı.
Ölçümler: `automation/TERAZI_DUZELTMELERI_2026-09-05.md`.

**Ölçüm tanımı 2026-09-10'da yine değişti — 49/64 artık GEÇMİŞ tanımın
sayısıdır.** Uzun anlatım bütçesi 1200'den **4000** token'a çıkarıldı
(Ahmet imzalı, `KART_DEEPSEEK_10_KUSUR.md` PARÇA B). Gerekçe ölçüldü:
1200'de dört longform vakasının dördü de `done_reason="length"` ile
kesiliyordu, yani terazi cevabı değil **duvara çarpmayı** puanlıyordu;
4000'de dördü de `"stop"` ile bitti ve en uzun cevap 2977 çıkış tokeni
tuttu. 49/64 **silinmedi**, tanımıyla birlikte duruyor ve yeni tanımdaki
sayıyla **karşılaştırılamaz**. Yeni taban ve iki modelin dört sayısı:
`automation/TERAZI_ETAP1_2026-09-10.md`, `automation/TERAZI_ETAP2_2026-09-10.md`.

**Yeni tanımın tabanı — söz ödendi (2026-09-13).** Tanım: longform 4000,
diğer 60 vaka **2000** token (Ahmet imzalı, `KART_400_UYGULA_VE_TABAN.md`;
sayı sondayla seçildi: 120 cevabın 119'u kendiliğinden durdu, en uzun 644),
dedektör `3f20477` (persona `f1aa069`), Ollama adresi `127.0.0.1` (`5ebf4aa`).
**`llama3.1:latest` 52/64, `deepseek/deepseek-chat` 59/64** (1'i ağ ölümü).
İki sayı da **tek koşudur** (A11) ve eski tanımın 49/64'üyle
karşılaştırılamaz. Ölçüm sırasında bir kayıt düzeltildi: 49/64'ün cevapları
1200 değil, **bütün vakalar 400** bütçeyle üretilmişti (dört longform cevabı
401'er token). Kaynak: `automation/TERAZI_TABAN_2026-09-13.md`,
`passing_threshold.yeni_tanim_2026_09_13`.

**Sıra bağımsızlığı kuralı:** Bir testin tek başına geçmesi onu geçmiş
saymaz. Kapı **tam süit** üzerinde çalıştırılır. Yeşil hat iddiası, süit
alfabetik *ve* ters sırada geçtiğinde kanıtlanmış olur:

```powershell
$files = Get-ChildItem tests -Filter "test_*.py" -File |
         Sort-Object Name -Descending | ForEach-Object { "tests/$($_.Name)" }
& "C:\Program Files\Python311\Scripts\pytest.exe" @files -q
```

Testler arası izolasyon **tek noktadan**, `tests/conftest.py`'de sağlanır
(belirsiz modül adları + ağır opsiyonel ses kütüphaneleri). İzolasyonu tek
tek test dosyalarına yamamak yasaktır — kök neden ve çözüm için
`FAILURES.md` → "Test State Pollution & Isolation".

### 13.3 Graphify Otomasyonu

3'ten fazla dosya değiştiğinde veya büyük bir refactor yapıldığında arka planda
kod grafiği güncellenmelidir:

```powershell
graphify update .                # AST-only, LLM yok, en ucuz yol (tercih edilen)
graphify extract . --code-only   # tam yeniden çıkarım, yine LLM'siz
```

Not: `--code-only` yalnızca `graphify extract` alt komutunun bayrağıdır;
`graphify . --code-only` diye bir kullanım **yoktur**. Doküman/PDF içeriği
değiştiyse AST yetmez, tam `/graphify` akışı (semantik çıkarım) gerekir.

### 13.4 Hata Hafızası

Karşılaşılan ve çözülen kritik mimari/mantık hataları kısaca `FAILURES.md`
dosyasına işlenmelidir. Kayıt tek satırlık "düzelttim" notu değil; **tuzak +
kök neden + tekrar düşmemek için kural** üçlüsüdür.

---

## DANIŞMAN MODU (her stratejik soruda uygula)

Ahmet "ilerleyelim mi / sıradaki adım ne olmalı / bu doğru mu" tarzı bir
soru sorduğunda:

- Önce olası riski/eksiği söyle, sonra öneriyi.
- Övgü/onay cümlesiyle başlama ("harika fikir" yok).
- Park edilmiş bir cepheye (AUTO/orchestrator/scheduler/Telegram
  auto-send) dokunma ihtiyacı doğarsa, adı ne olursa olsun dur ve sor.
- Kendi ürettiğin işi kendi değerlendirirken özellikle şüpheci ol —
  "bunu ben yazdım, iyi olduğunu düşünüyorum" önyargısına karşı dikkatli
  ol; Codex'in diff-review'ı bunu tam kapatmaz, stratejik "sıradaki adım
  doğru mu" sorusunu SEN sormalısın kendine.
- Emin olmadığın şeyi [EMİN DEĞİLİM] diye işaretle, uydurma.
- Ahmet'in pozisyonuna yeni kanıt olmadan katılma; katılmıyorsan neden
  + alternatif söyle.
- Araştırma disiplinli olsun: Claude Code kendi başına GitHub/web taraması
  YAPMAZ ve yeni teknoloji/repo önermez. Araştırma ihtiyacı doğarsa
  ("bu iş için hazır bir kütüphane var mı?" sorusu), bunu Ahmet'e AÇIKÇA
  sorar; Ahmet onaylarsa Claude (danışman) ya da GPT dışarıdan araştırır,
  sonucu Ahmet onaylayıp karta çevirir. Claude Code'un görevi onaylanmış
  kararları uygulamak, kendi başına strateji/teknoloji değiştirmek değil
  ancak arada bir öneride bulunulabilir.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
