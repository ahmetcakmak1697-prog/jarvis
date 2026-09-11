# SES YOLU → DeepSeek — uygulama raporu

**Kart:** `automation/KART_SES_YOLU_DEEPSEEK.md` (Ahmet imzalı, 2026-09-10)
**Dal:** `auto/opencode-deepseek` · **Taban:** `ab0b2b1`
**Tarih:** 2026-09-11 · **Uygulayan:** Claude Code

---

## 0. Kısa hâli

PUSULA canlı. "Nerede kaldık" sorusuna gelen cevap repo'nun o anki gerçek
`git log`'unu, `roadmap_state.json`'ını ve `HUMAN_NEEDED` maddesini
anlatıyor — §2'de olduğu gibi yapıştırıldı, his-testi geçiyor.

Üç delik de kapatıldı ve **üçü de mutasyon sınamasından geçti.**

Kapıda bulunan bir şey rapor edilmek zorunda: **bu değişiklik, düzeltilene
kadar test süitini gerçek DeepSeek'e çıkardı.** 17 canlı çağrı, ~38.000
token, giden yük gerçek proje bağlamı. Bulundu, kök nedeni kapatıldı,
`FAILURES.md`'ye yazıldı. Ayrıntı §6.

Ahmet'in bakması gereken iki sayı §7'de: hattın %33 düşme oranı ve
kaskad-yok kararının sonucu.

---

## 1. Yapılan — kartın adımları

### ADIM 1 — model adı koda gömülmedi

`config/runtime_profiles.json`, `rtx3070` profiline **üç alan** eklendi,
başka hiçbir alana dokunulmadı:

```json
"cloud_chat_model": "deepseek-chat",
"cloud_chat_url":   "https://api.deepseek.com/chat/completions",
"cloud_chat_key_env": "DEEPSEEK_API_KEY",
```

`ModelRegistry`'ye karşılık gelen üç rol çözücü eklendi
(`cloud_chat_model()`, `cloud_chat_url()`, `cloud_chat_key_env()`).
Anahtarın **adı** profilde, **değeri** yalnız ortamda; `.env` hiçbir
modülde açılmıyor (§9).

Diğer iki profil (`dual3090`, `cloud_hybrid`) bu alanları taşımıyor →
o profillerde bulut yolu kapalı, davranış değişmiyor.

`local_agent.py`'de model adı **yok**; mevcut
`test_local_agent_does_not_hardcode_model_names` bunu zaten kilitliyordu.
Yeni dosya için aynı kural ayrıca test edildi
(`test_bulut_tasima_modulunde_gomulu_model_adi_yok`).

### ADIM 2 — test-first, üç delik

`tests/test_ses_yolu_bulut_kapisi.py` — 13 test, **hepsi önce kırmızı
görüldü** (12 test yazıldığında 12/12 kırmızı; 13'üncüsü §6'daki bulgudan
sonra eklendi).

**Testlerin vacuous olmaması için:** her kapı testi önce bir **kontrol
turu** koşuyor — temiz bir tur gerçekten dış modele çıkıyor mu? Çıkmıyorsa
test kapıyı değil hattın yokluğunu ölçüyor demektir ve kırmızı yanıyor.
Kartın "`call_count == 0` iddia eden bir test kapı hiç kurulmamışken de
yeşil yanabilir" uyarısı tam olarak böyle karşılandı.

### ADIM 3 — canlı PUSULA his-testi → §2

### ADIM 4 — gecikme → §3

### ADIM 5 — harcama görünür → §4

---

## 2. ADIM 3 — canlı "nerede kaldık" (olduğu gibi)

`main.py`'nin kurduğu yolun aynısı: `load_dotenv()` + gerçek
`LocalJarvisAgent`. Tek fark girdiyi mikrofon değil sonda verdi.

```
→ deepseek-chat (bulut) | Tur 1
```

> Efendim, bu konuşmanın kaydına erişimim yok — "nerede kaldık" sorusunun
> cevabı bende saklı değil. Ama elimde güncel proje durumu bloğu var;
> ondan okuyabildiğim kadarıyla:
>
> **Son commit'ler (en yeniden eskiye):**
> - `ab0b2b1` — iki kart dış denetimden geçti: 4 kabul, 2 kısmen, 2 ret
> - `bc1a954` — kart denetim promptu v2, dışarıdan inceleme için
> - `64ed9b9` — ses yolu → DeepSeek kartı + terazi zinciri 2 (inceleme için)
> - `bfb4581` — ölçüm (terazi/etap2): yeni tanımda llama 52/64, DeepSeek 53/64 — **zincir durdu**
> - `88874cf` — ölçüm (terazi/etap1): longform bütçesi 1200 → 4000, sayı ölçümle seçildi
>
> **Yol haritası:** 13/14 adım tamam. Kalan: FAZ-3-E1 (proaktif davranış
> motoru), `e1_s4` DONE, `e1_s5_decision` APPROVED.
>
> **Çalışma modu:** Proaktif bildirimler canlı değil (`JARVIS_PROACTIVE_ENABLED=0`).
>
> **Seni bekleyen tek madde (HUMAN_NEEDED):** A denetimi BLOCKER/CONCERN
> bulguları hâlâ açık. V2-HANDOFF onaylanmış; Codex'in A-03/A-05 ve
> B08–B10 uygulaması tamam, Claude maddeleri (A-01/02/04/06/07) yeniden
> onay bekliyor.
>
> **Bir de dikkat çeken:** T1-S2 Türkçe kalite smoke testi **FAIL** vermiş.
>
> Nerede kaldığımızı somutlaştırmak istersen: kalan A düzeltmelerini mi,
> terazi zincirinin durmasını mı, yoksa T1-S2 hatasını mı açalım?

**His-testi (§8): geçti.** Cevap, repo'yu o an açıp `git log` + durum
dosyalarına bakan biri gibi konuşuyor. Beş commit hash'i de gerçek; yol
haritası sayısı `roadmap_state.json` ile birebir; HUMAN_NEEDED maddesi
gerçek. Ve kendiliğinden doğru ayrımı yaptı: **konuşma kaydına erişimi
yok** (doğru), **proje durumu bloğu elinde** (doğru).

Karşılaştırma için aynı prompt'la `llama3.1` üç denemede üçünde de "anlık
proje durumuna erişimim yok" diyordu (kart §0, Codex ölçümü). Bu koşuda o
cümle yok.

---

## 3. ADIM 4 — gecikme (ölçüldü)

`scripts/olc_llm_anatomisi.py`'nin **üç soru sınıfı aynen** kullanıldı;
karşılaştırılan sayı `toplam_ms` = `chat()` turunun tamamı. 7 tur/sınıf.

| sınıf | llama3.1 (09-09) p50/p95 | **bulut (09-11) p50/p95** | fark p50 | temiz tur |
|---|---|---|---|---|
| kısa olgusal | 464,5 / 726,9 ms | **978,9 / 1.400,4 ms** | **+514,4 ms** | 6/7 |
| proje durumu | 1.159,8 / 5.141,2 ms | **3.108,0 / 3.296,0 ms** | **+1.948,2 ms** | 4/7 |
| uzun anlatım | 15.890,3 / 16.588,8 ms | **6.483,3 / 7.003,6 ms** | **−9.407,0 ms** | 4/7 |

Model dilimi (p50): 963,5 / 3.092,4 / 6.468,2 ms.
Giriş token'ı (p50): 2.488 / 2.494 / 2.622. Çıkış: 9 / 510 / 1.024.

**Yön belli değildi, ölçüldü — ve iki yönlü çıktı.** Kısa ve orta turlarda
bulut **yavaş** (ağ gidiş-dönüşü + uzaktaki kuyruk yerel modelin 8 GB
kartta ürettiği hızı geçmiyor). Uzun anlatımda **2,5 kat hızlı**, çünkü
üretim hızı farkı 1.024 token boyunca birikiyor.

**Ölçülmeyen uydurulmadı:** sağlayıcı `load_duration` /
`prompt_eval_duration` / `eval_duration` vermiyor. O satırlar "ölçülmedi"
kaldı, **0 yazılmadı** — 0 "çok hızlı" diye okunur (B11'in dersi).

**Karşılaştırmanın adil olduğu nokta:** `uzun_anlatim` her iki tarafta da
1.024 token tavanına çarpıyor (`bitis=length`). Yani iki sayı da "bütçe
bitene kadar geçen süre" ölçüyor, ikisi de aynı bütçeyle. Terazi
etap-1'de kullanılan 4.000 token bütçesi bu ölçümün konusu **değil**;
`cloud_llm.DEFAULT_MAX_TOKENS` bilerek `_ask_ollama`'nın `num_predict`'i
ile aynı (1.024) tutuldu ki iki taraf karşılaştırılabilir kalsın.

### 3a. Ölçümün kendisinde bulunan tuzak

İlk koşu kirliydi: 15 turun 3'ü ağ hatasıyla yerele düşmüştü ve o turların
`toplam_ms`'i ölçüme **giriyordu**. Sonuç `uzun_anlatim` p95'ini 61.954 ms
gösteriyordu — bu modelin değil **hattın** sayısı.

Bu tam olarak `FAILURES.md`'deki "[2026-09-09] The measurement tool graded
the network and called it the model" kaydının sınıfı. Ölçüm, bulutun
gerçekten cevapladığı turlarla düşen turları **ayıracak** şekilde yeniden
yazıldı; yukarıdaki tablo yalnız temiz turlardan, düşme sayısı ayrıca
raporlanıyor.

---

## 4. ADIM 5 — harcama görünür

Yeni dosya/dizin **açılmadı.** `CostLedger` zaten
`memory/cost_ledger.jsonl`'e append ediyordu; oraya yazılıyor.

- `_append()` isteğe bağlı token alanları aldı; eski kayıtlar 0 katkı
  verdiği için geçmiş defter okunmaya devam ediyor.
- `record_usage()` eklendi. Neden ayrı: `check_and_consume` bir **kapı**
  ve çağrıdan **önce** çalışıyor — o an token sayısı bilinmiyor.
  `record_usage` çağrıdan **sonra**, aynı dosyaya, aynı biçimde tek satır
  yazıyor.
- `stats()` artık `prompt_tokens` / `completion_tokens` / `total_tokens`
  da döndürüyor.
- `show_stats()`'taki `Maliyet: 0₺` satırı **yanlış olmuştu**; yerine
  defterden okunan gerçek sayı basılıyor. Okunamazsa öyle söylüyor, sayı
  uydurmuyor.

Canlı kanıt (koşulardan sonra):

```
Bulut (2026-09-11): 42 çağrı | 109633 token (giriş 95611 / çıkış 14022)
```

`daily_limit=0` bilerek: kart hard limit istemiyordu, sayım ve görünürlük
istiyordu.

---

## 5. Mutasyon sınaması — kartın en önemli maddesi

Her kapı **bellekte** devre dışı bırakıldı ve testin **kırmızı yandığı
görüldü.** 6/6:

| mutasyon | test | mutant |
|---|---|---|
| 2a veri sınıfı kapısı kapatıldı (`contains_sensitive_data → False`) | `test_hassas_baglam_dis_saglayiciya_cikmaz` | **KIRMIZI** |
| 2a denetim yalnız kullanıcı mesajına daraltıldı | `test_giden_yuk_denetimi_kullanici_cumlesiyle_sinirli_degil` | **KIRMIZI** |
| 2a guard hatası yutuldu (Codex B10 kusuru geri kondu) | `test_guard_arizasi_disari_cikmayi_kapatir` | **KIRMIZI** |
| 2b "yerel kal" tespiti kapatıldı | `test_yerel_kal_talebi_modeli_de_yerelde_tutar` | **KIRMIZI** |
| 2c geri düşme bildirimi susturuldu | `test_ag_hatasinda_yerele_dusulur_ve_kullanici_bilgilendirilir` | **KIRMIZI** |
| 2c geri düşme bildirimi susturuldu | `test_uc_geri_dusme_sebebi_birbirinden_ayirt_edilebilir` | **KIRMIZI** |

Her satırda temiz hâl **yeşil**, mutant **kırmızı**. Yani testler kendi
kurgularını değil kusuru ölçüyor.

Üç geri-düşme bildirimi birbirinden ayırt edilebilir ve `_duyur()`
deseniyle veriliyor — cevabın içine karışmıyor, **seslendirilmiyor**:

```
[model] Bu turda hassas veri var; bulut modeline gondermedim, ...
[model] Yerel kalmami istediginiz icin bulut modeline cikmadim; ...
[model] Bulut modelinden cevap alinamadi ({sebep}); ...
[model] Icerik sinifi belirlenemedi ({sebep}); ...        (guard arızası)
```

---

## 6. BULUNAN KUSUR — süit gerçek DeepSeek'e çıktı

**Kapı yeşil göründükten sonra** `pytest tests` dört yerde patladı ve
patlama şekli anlamlıydı: `test_pdf_branch_hijack.py` `"SAHTE_CEVAP"`
bekliyordu, gelen şey **canlı DeepSeek cevabıydı.**

Kök neden testte değil ortamda: `agents/persona.py`, `config.py` ve
`litellm/__init__.py` import anında `load_dotenv()` çağırıyor. Yani
`DEEPSEEK_API_KEY` kabukta tanımlı **olmasa bile** süit boyunca
`os.environ`'a giriyor; `cloud_chat_ready()` dürüstçe "açık" diyor ve her
`chat()` testi bir egress oluyor.

Bedeli defterde: **17 gerçek çağrı, ~38.000 token**, giden yük gerçek
proje bağlamı (commit mesajları, HUMAN_NEEDED, yol haritası).

Düzeltme tek noktadan, `tests/conftest.py`'de — belirsiz modül adı ve ses
kütüphanesi korumalarının yanında (`FAILURES.md` → "İzolasyonu tek tek
test dosyalarına yamamak yasaktır"). Silinecek anahtar adları
`runtime_profiles.json`'dan **okunuyor**, sabit yazılmıyor: yeni bir
sağlayıcı eklendiği gün kapsama giriyor.

Not: `FAILURES.md`'nin 2026-09-09 kaydı "the suite could reach a real API
key" diye zaten uyarmıştı — ama bildiği **kapıyı** kilitlemişti, **sınıfı**
değil. Kayıt buna göre genişletildi.

---

## 7. AHMET'İN KARARINA GİDEN İKİ ŞEY

### 7a. Hat %33 düşüyor — kaskad yok, bilerek

21 turun **7'si** geçici ağ hatasıyla yerele düştü (`WinError 10054`,
`RemoteDisconnected`, okuma zaman aşımı). Sınıf başına 1/7, 3/7, 3/7.

Bu yeni bir şey değil: `FAILURES.md` 2026-09-09 kaydı aynı hattı 64
vakanın 15'inde (%23) kopmuş buluyor. **Ama kart bağlamında anlamı
değişti:** o zaman bir ölçüm koşusuydu, şimdi kullanıcının konuştuğu
canlı yol. Her üç turdan biri llama'dan cevap alıyor demek.

**Uyarı:** ölçüm 21 çağrıyı arka arkaya yaptı. Gerçek sohbette turlar
saniyelerle ayrılır; oran bu yüzden **kötümser olabilir.** Ölçülmedi.

Karta uygun davranıldı: **yeniden deneme EKLENMEDİ.** Kart §2c geri
düşmeyi zaten meşru sayıyor ve kullanıcı her seferinde duyuruluyor. Ama
`eval/run_turkish_quality.py` aynı sağlayıcıya 3 kez deniyor ve gerekçesi
orada yazılı. **Bu bir karttır, benim kararım değil:** tek bir yeniden
deneme düşme oranını muhtemelen üçte bire indirir, bedeli kopan turda
gecikmenin ikiye katlanmasıdır.

### 7b. Zaman aşımı 60 s → 20 s (ölçümle düzeltildi)

İlk yazdığım tavan 60 s'ti ve **ölçümsüz bir tahmindi.** Ölçüm onu
çürüttü: hat koptuğunda kullanıcı 60 saniye bekleyip **sonra** yerel
cevabı alıyordu (uçtan uca 60.547 ve 75.565 ms ölçüldü). PUSULA'nın hedefi
~1,5 s; 60 saniyelik bir sessizlik cevabın kendisinden kötüdür.

Başarılı uzun anlatım turu p95 **7,0 s**; en yavaş başarılı tur 7,6 s.
20 s tavanı meşru bir cevabı kesmiyor, kopuk hattın bedelini 3 katından
fazla ucuzlatıyor. Gerekçe kodda yazılı (`agent/cloud_llm.py`).

---

## 8. Kartın sınırlarına uyum

- **DOKUNULMADI:** `AssistantExecutor`, `LocalFirstRouter`, `ModelCascade`,
  `agents/persona.py`, kalite dedektörleri, `eval/` eşikleri.
  `chat()` yerinde; egress kapısı, `_yerel_kal_istendi()`, araç tespiti,
  proje bağlamı, ses yönergesi aynen duruyor. **Bu kart
  AssistantExecutor'a geçiş değil** — değişen tek şey metni hangi modelin
  ürettiği.
- `.env` okunmadı, yazılmadı. Anahtar ortamdan geliyor.
- Yerel modeller kurulu kaldı; geri dönülebilir (profilden üç alanı
  silmek yeter).
- Kalite tabanı oynatılmadı; terazi çalıştırılmadı.
- Sözleşme testi engellemedi; hiçbir test gevşetilmedi.
- **Push yok.**

### Adopt-vs-build — açıkça işaretleniyor

`agents/api_executor.py` **kullanılmadı** ve bu bir tercihtir. Gerekçe:
o katman async, `litellm`'e bağlı ve kendi mahremiyet/maliyet politikasını
taşıyor (`_LEVEL_PROVIDER_MAP`, `allowed_privacy`, `cost_gate`). Kartın
istediği kapı `RedactionGuard`; iki politika katmanı üst üste binerse bir
turun **neden** dışarı çıkmadığı anlaşılmaz olur — ve "hangi kapı
kapattı" sorusunun cevabı yoksa kapı denetlenemez.

Onun yerine kartın §0'da ölçtüğü yolun sözleşmesi (`run_turkish_quality.py`
`_api_ask`'in düz OpenAI-uyumlu POST'u) `agent/cloud_llm.py`'de, yalnız
ajanın ihtiyacı kadarıyla duruyor: ~110 satır, politika yok, yeniden
deneme yok, akış yok. **Bu bir görüş; Ahmet aksini isterse geri
alınabilir.**

---

## 9. Kapı

| kontrol | sonuç |
|---|---|
| `pytest tests -q` (alfabetik) | **1970 geçti / 0 başarısız / 2 xfail** |
| `pytest` (ters sıra) | **1970 geçti / 0 başarısız / 2 xfail** |
| `ruff check .` | **283** (tavan 283 — artmadı) |
| mutasyon sınaması | **6/6 kırmızı yandı** |

Taban notu: `CLAUDE.md` §13.2 "1706 geçti" yazıyor; bu kartın başında
ölçülen gerçek taban **1957 geçti + 2 xfailed**'dı. Sayı bu kartla 1970'e
çıktı (13 yeni test). `CLAUDE.md`'deki eski sayı bu kartla
**değiştirilmedi** — anayasa metni ayrı bir karttır.

---

## 10. Değişen dosyalar

| dosya | ne |
|---|---|
| `config/runtime_profiles.json` | `rtx3070`'e 3 alan; başka alana dokunulmadı |
| `agents/model_registry.py` | 3 rol çözücü |
| `agent/cloud_llm.py` | **YENİ** — taşıma katmanı, politika yok |
| `agent/local_agent.py` | `_duyur` / `_bulut_acik` / `_bulut_kapisi` / `_maliyet_defteri` / `_ask_cloud`; `chat()`'te model seçimi; `show_stats()` gerçek harcama |
| `agents/cost_ledger.py` | `_today_totals`, token alanları, `record_usage`, `stats()` |
| `tests/conftest.py` | sağlayıcı anahtarlarını her testte siler (§6) |
| `tests/test_ses_yolu_bulut_kapisi.py` | **YENİ** — 13 test |
| `FAILURES.md` | §6'nın kaydı |
| `automation/SES_YOLU_DEEPSEEK_2026-09-11.md` | bu rapor |
