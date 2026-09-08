# JARVIS Öğrenilen Hatalar ve Mimari Tuzaklar

> Bu dosya bir hata *günlüğü* değil, bir **kural üreteci**dir.
> Amaç: aynı tuzağa iki kez düşmemek. Bir hata buraya yazılmadıysa
> çözülmüş sayılmaz (bkz. `CLAUDE.md` §13.4).

## Nasıl kayıt eklenir

- **Yalnız kritik olanı yaz.** Yazım hatası, tek satırlık typo, geçici
  ortam sorunu buraya girmez. Buraya giren: mimari yanlış varsayım,
  sessiz mantık hatası, tekrar edebilecek sınıf-düzeyi tuzak.
- **En yeni kayıt en üste** eklenir.
- Her kayıt üç parçadan oluşur ve üçü de zorunludur:
  **Tuzak** (ne oldu) → **Kök neden** (neden oldu) → **Kural** (bir daha
  düşmemek için ne yapılacak).
- **Kural satırı test edilebilir olmalı.** "Dikkatli ol" kural değildir;
  "X yazılmadan önce Y testi yazılır" kuraldır.
- Kayıt tarihlidir ve mümkünse kanıta (commit hash, test adı, BLACKBOX
  `sequence`) bağlanır.

## Kayıt şablonu

Yeni kayıtlar aşağıdaki şablonla, `## Kayıtlar` başlığının hemen altına
eklenir:

```markdown
### [YYYY-AA-GG] Kısa başlık — bir cümlelik özet

- **Alan:** (ör. bellek katmanı / J0 ses hattı / router / otomasyon kapısı)
- **Şiddet:** BLOCKER | CONCERN | NOTE
- **Tuzak:** Ne oldu? Gözlemlenen yanlış davranış, tek paragraf.
- **Kök neden:** Neden oldu? Yanlış olan varsayım/mekanizma.
  Semptom değil, sebep yazılır.
- **Kural:** Bir daha düşmemek için ne yapılacak? Emir kipinde, tek cümle,
  doğrulanabilir.
- **Kanıt:** commit hash / test adı / BLACKBOX sequence / dosya:satır
- **Regresyon testi:** Bu hatayı yeniden üretecek testin adı.
  (Yoksa `YOK — açık borç` yazılır, uydurulmaz.)
```

## DESEN — "YEŞİL" ile "ÖLÇÜLDÜ" aynı şey değildir

> Bu bölüm tek bir olayı değil, **bir aileyi** kaydeder. İlk üç tuzak aynı
> gün (2026-09-01/02) bulundu, dördüncüsü iki gün sonra; dördünde de aynı şey
> oldu: bir şey **başarılı görünüyordu ve aslında hiçbir şey ölçülmüyordu.**

| # | Nerede | "Yeşil" görünen şey | Gerçekte olan |
|---|---|---|---|
| 1 | `voice/stt.py` | Ses akışı açıldı, hata yok | Akış **sıfır** döndürüyordu; DirectSound'da 9600 örneğin 9600'ü tam sıfır |
| 2 | `tests/test_local_agent_grounding.py` | 4 test yeşil | Testler gerçek fonksiyonu değil, testin içine yazılmış **replikayı** ölçüyordu — gerçek fonksiyon silinse yeşil kalırlardı |
| 3 | `tests/test_j0_spike_b_latency_probe.py` | Test haftalardır yeşil | İddia bir `if` içindeydi, koşul hiç sağlanmıyordu; test **hiçbir şey kontrol etmiyordu** |
| 4 | `eval/quality_scorer.py` (2026-09-03) | Kalite koşusu **63/64** | 64 cevap elle okununca 15'i kusurluydu: model sistem prompt'unu geri okuyor, cümleyi yarıda kesiyor, aynı diziyi 4 kez yazıyor. Puanlayıcı bunların **hiçbirine bakmıyordu**; aynı cevaplar yeni dedektörlerle **49/64** |

**Ortak yapı:** üçünde de bir *başarı sinyali* vardı (akış açıldı / test geçti)
ve o sinyal, altındaki işin yapıldığını **kanıtlamıyordu**. Sinyal ile kanıt
arasındaki boşlukta hata sessizce bekledi.

**Ortak bedel:** üçü de ancak uzun bir arama sonucu görüldü. Mikrofon bir saat,
replika bir denetim turu, boş test bir tam süit soruşturması. Sessiz
başarısızlığın maliyeti bulunduğu anda değil, **bulunana kadar geçen sürede**
birikir.

**Ortak kural — bir sinyali kabul etmeden önce sor:**

1. **Bu sinyal ne kanıtlıyor?** "Açıldı" ≠ "veri geldi". "Geçti" ≠ "ölçtü".
2. **Ölçülen şey gerçek mi, kopyası mı?** Test, üretimdeki nesnenin ta
   kendisini mi çağırıyor, yoksa ona benzeyen bir şeyi mi?
3. **İddia her koşuda çalışıyor mu?** Koşula bağlıysa, koşulun sağlandığı da
   ayrıca iddia edilmeli.
4. **Ucuz karşı-kanıt var mı?** Dört vakada da vardı ve bakılmamıştı: tam-sıfır
   örnek sayısı, dosya süresi (8,7s → 0,9s), replikanın gerçek fonksiyondan
   *eksik* olduğu satırlar, ve raporun kendi satırı: 64 vakanın yalnız 14'ü
   beyan edilmiş bir iddia taşıyordu — yani 50 vaka için "geçti" demek
   "boş değildi" demekten fazlasını söylemiyordu.

**Uygulama:** yeni bir "başarılı" yol yazarken, o yolun **başarısız olduğunda
nasıl görüneceği** de yazılır. İkisi ayırt edilemiyorsa sinyal işe yaramıyordur.

---

## Kayıtlar

### [2026-09-08] Mutation gate, koşmayan bir test komutuna "kusursuz" dedi

- **Alan:** `scripts/mutation_gate.py` — anti-test-gaming kapısı
- **Şiddet:** BLOCKER (kapının kendisi yanlış cevap veriyordu)
- **Tuzak:** `tests/test_mutation_gate.py::test_weak_tests_leave_survivor`
  yanıp sönüyordu: tam süitte `assert 1.0 < 0.8` ile düştü, tek başına
  5/5 geçti, sonraki koşuda yeşil geldi. Zayıf test verildiği hâlde skor
  1.0 çıkıyordu — yani "her mutant öldürüldü".
- **Kök neden — ölçüldü, tahmin edilmedi (2026-09-08):** Alt-sürecin
  çıkış kodu tek bir eşikle okunuyordu:

  ```python
  if cp.returncode != 0:
      killed += 1        # "testler bug'i yakaladi"
  ```

  Sıfırdan farklı **her** kod "yakalandı" sayılıyordu. Oysa pytest'te
  yalnız `1` "testler koştu ve başarısız" demek; `2` kesinti, `3` iç
  hata, `4` kullanım hatası, `5` hiç test toplanmadı. Son dördü mutantın
  yakalandığını değil, **test komutunun hiç çalışmadığını** söyler.
  Doğrudan ölçüldü:

  ```
  "pytest <olmayan dosya>" (exit 4) -> skor=1.0  survivors=0
  "sys.exit(2)" / "(3)" / "(5)"     -> skor=1.0  survivors=0
  ```

  Yani "kodu testten geçecek şekilde yazma" oyununu kırmak için var olan
  araç, test komutu tamamen bozukken **"testleriniz kusursuz"** diyordu.
  Yanıp sönme de buradan doğuyordu: alt-süreçteki pytest çevresel bir
  sebeple koşamadığında bütün mutantlar "öldürüldü" sayılıyordu.
- **Kural:** Bir alt-sürecin **başarısızlığı**, aradığın şeyin
  **kanıtı** değildir. Çıkış kodunu ikili (`!= 0`) okuma; hangi kodun
  "ölçüm yapıldı" hangisinin "ölçüm yapılamadı" demek olduğunu ayır.
  Ölçüm yapılamadıysa skor **basılmaz**, gürültülü hata verilir —
  `MutationGateError`. Bu, `FAILURES.md`'nin "YEŞİL ile ÖLÇÜLDÜ aynı
  şey değildir" deseninin doğrudan uygulanışıdır.
- **Kanıt:** `scripts/mutation_gate.py` → `_TESTLER_KOSTU_VE_BASARISIZ`
  ve `MutationGateError`. Ölçüm çıktısı yukarıda.
- **Regresyon testi:**
  `tests/test_mutation_gate_olcum_durustlugu.py` — 8 test; düzeltmeden
  önce 6'sı kırmızı görüldü. Mevcut `tests/test_mutation_gate.py`
  (timeout=öldürüldü sözleşmesi dahil) değiştirilmedi.
- **Kapanmayan sınır (açık borç):** Windows kabuğu **bulunamayan komut**
  için de `1` döndürüyor ("is not recognized as an internal or external
  command"), yani "testler koştu ve başarısız" ile aynı kod. Bu vaka
  çıkış koduna bakarak ayrılamıyor ve hâlâ "öldürüldü" sayılıyor.
  Görünür tutuluyor:
  `test_BILINEN_SINIR_bulunamayan_komut_ayirt_edilemiyor`. Kapatmak
  stderr ayrıştırmayı ya da `shell=False`'a geçmeyi gerektirir; ikisi
  de `run_gate`'in sözleşmesini değiştirir.

### [2026-09-01] Bir worktree klasörünü kopyalamak yedek değildir

- **Alan:** yedekleme / git topolojisi
- **Şiddet:** BLOCKER (yanlış bir yedek, yedek olmadığını ancak ihtiyaç
  anında gösterir)
- **Tuzak:** `jarvis-agent-auto/` bağımsız bir depo sanıldı ve "bu klasörü
  kopyala/yedekle" tavsiyesi verildi. Klasör kopyalansaydı **hiçbir commit
  geçmişi taşınmazdı** — kopyalayan bunu ancak yeni makinede `git log`
  çalıştırdığında öğrenirdi, yani felaket anında.
- **Kök neden:** Bu dizin bir **git worktree**. Ölçüldü:

  ```
  .git            -> dizin DEĞİL, 80 baytlık dosya
  içerik          -> gitdir: .../Jarvis/jarvis/.git/worktrees/jarvis-agent-auto
  --git-common-dir-> C:/Users/Ahmedov/Desktop/Jarvis/jarvis/.git
  .git/objects    -> BURADA YOK
  ../jarvis/.git/objects -> 619 MB   <- gerçek geçmiş burada
  ```

  Yani klasördeki `.git`, başka bir yoldaki asıl depoya **işaret eden 80
  bayt**. O yol yeni makinede bulunmayacağı için kopya, geçmişi olmayan bir
  çalışma ağacından ibaret kalır.

- **Kural:**
  1. Bir klasörü yedek saymadan önce **`.git`'in dizin olduğunu doğrula.**
     Dosyaysa orası bir worktree ya da submodule'dür; geçmiş başka yerdedir.
     Tek satırlık kontrol: `git rev-parse --git-common-dir` — çıktı `.git`
     değilse, klasör kendi kendine yetmiyor.
  2. **Yedek, kopyalamayla değil `git clone`/`git bundle` ile alınır.**
     Bunlar nesneleri gerçekten taşır; dosya kopyası taşımaz.
  3. **Test edilmemiş yedek yedek değildir.** Yedek, geçici bir dizine
     klonlanıp içindeki kilit dosyalar ve `pytest` toplaması doğrulanarak
     kabul edilir.

- **Neden bu kayıt önemli:** Bu, `FAILURES.md`'deki *"açılan akış çalışan
  akış demek değildir"* dersiyle **aynı aileden**: görünüş ile gerçeğin
  ayrıldığı, ve hatanın sessizce beklediği bir durum. Ses hattında bedeli
  bir saatti; burada bedeli tüm proje geçmişi olurdu.

- **Kanıt:** `git rev-parse --git-common-dir` → `Jarvis/jarvis/.git`;
  `.git` dosya boyutu 80 bayt; `size-pack` 618,83 MiB ve geçmişte 69.184
  `venv/` nesnesi. Kayıt: `automation/AHMET_ONAYI_BEKLEYENLER.md` A10.

- **Regresyon testi:** YOK — bu bir süreç kuralı, kod değil. Kilit,
  yedeğin klondan doğrulanması adımıdır.

### [2026-09-01] Açılan akış çalışan akış demek değildir — sessiz başarısızlık

- **Alan:** J0 ses hattı (`voice/stt.py`), aygıt seçimi
- **Şiddet:** BLOCKER (ses hattı hiç çalışmadı, sebebi bir saat bulunamadı)
- **Tuzak:** JARVIS mikrofonu "açıyor", hata vermiyor, sonsuza kadar
  `no_speech_detected` diyordu. Ahmet bir saat boyunca mikrofon ayarlarıyla
  uğraştı; sorun mikrofonda değildi.
- **Kök neden — iki katman:**
  1. `sd.InputStream` + bloklayan `read()`, bazı Windows host API'lerinde
     **hata vermeden** sıfır döndürüyor. Ölçüldü: DirectSound aygıtında
     9600 örneğin **9600'ü tam sıfır**; aynı aygıtta geri-çağırma yolu
     rms 0.020 veriyor. `sd.rec` hep çalışmıştı çünkü içeride
     geri-çağırma kullanıyor.
  2. Aygıt indeksleri **kayıyor**. Kulaklık bağlantısı kesilince SoloCast
     2/9/17'den 1/7/15'e kaydı ve bir önceki oturumda önerilen "9" numarası
     bir **hoparlöre** (çıkış aygıtı) denk geldi. İsimle seçim de çalışmıyordu:
     `check_input_settings("SoloCast")` → *"Multiple input devices found"*.
- **Kural — üç parça:**
  1. **Bir kaynağın açılması, veri verdiği anlamına gelmez.** Açılıştan sonra
     *gerçekten sinyal geldiği* doğrulanmalı. Gerçek bir mikrofonun gürültü
     tabanı vardır; **yalnız dijital sessizlik tam sıfırdır** — bu ayrım
     ölü akışı sessiz odadan ayırmanın deterministik yoludur.
  2. **Sessiz başarısızlık en pahalı hata türüdür.** Çöken kod dakikada
     bulunur; "hiçbir şey olmuyor" saatler yer. Bir yol sessizce
     başarısız olabiliyorsa, o sessizliği **ölçüp adlandıran** bir tanı
     alanı eklenir (`RecordResult.diagnostic`) ve tanı, kullanıcının
     çalıştıracağı komutu söyler.
  3. **Aygıt indeksi kalıcı bir kimlik değildir.** Donanım listesi
     değişebilir; indeks yalnız o anki listede anlamlıdır. Seçim isimle
     yapılmalı ve isim **açılabilen bir giriş aygıtına** çözülmeli —
     çıkış aygıtları asla aday değildir.
- **Kanıt:** `tests/test_voice_capture_path.py` (16 test);
  ölçüm: aygıt 7 `read()` rms 0.000000 / `callback` rms 0.019981.
  Commit `ccce9b21e`.
- **Regresyon testi:** `test_default_capture_path_uses_callback_not_blocking_read`
  (AST ile kilitli — docstring koda sayılmaz),
  `test_all_zero_stream_is_flagged_as_dead`, `test_name_skips_output_devices`.

### [2026-08-31] Persona parçalanması — üç rakip kimlik, biri bozuk kodlamalı

- **Alan:** karakter katmanı (`config.py`, `agents/ollama_executor.py`, `agent/local_agent.py`)
- **Şiddet:** BLOCKER (JARVIS'in kim olduğu, hangi kapıdan girildiğine bağlıydı)
- **Tuzak:** Repoda birbirinden habersiz **üç** persona tanımı vardı.
  `config.py`'deki ~70 satırlık zengin sürüm yalnız `agent/jarvis_agent.py`'ye
  ulaşıyordu; kaskad (`AssistantExecutor` → `OllamaExecutor`) ise kendi
  satır-içi, ASCII'ye indirgenmiş sözlüğünü kullanıyordu. Dahası o sözlükteki
  L1 prompt'unda Türkçe harfler soru işaretine dönüşmüştü — model kendi dil
  kuralını okunamaz bir cümleden öğreniyordu. Aynı bozulma
  `world/people.json`, `world/devices.json` ve `jarvis_server.py`'nin CSS
  yorumlarında da vardı.
- **Kök neden:** Persona bir *metin* olarak üç yere kopyalanmıştı ve hiçbir
  test onu kilitlemiyordu. Kopyalar zamanla ayrıştı; biri de bir PowerShell
  aktarımında bozuldu (CLAUDE.md §5). Kopya varsa kayma kaçınılmazdır.
- **Kural:** Persona metni **yalnız** `agents/persona.py` içinde tanımlanır;
  `config.py` ve `agents/ollama_executor.py` onu türetir. SSOT modülü **saf**
  olmalıdır — `agents/` katmanı `config.py`'yi import edemez, çünkü `config.py`
  import anında `load_dotenv()` çağırıp `HF_*_OFFLINE` yazar (§9: `.env`'e
  dokunulmaz). Yeni bir persona metni yazmadan önce `tests/test_persona_ssot.py`
  okunur.
- **Kanıt:** `tests/test_persona_ssot.py` — 28 test. Kırmızı faz 21 başarısız,
  yeşil faz 28/28. Tam süit 1351 → **1379 passed**; `ruff check .` 295'te sabit.
  Canlı doğrulama: yakalayıcı istemci ile L1/L2/L3'ün üçünün de
  `Efendim` + `SADAKAT` + gevezelik yasağı taşıdığı görüldü.
- **Regresyon testi:** `tests/test_persona_ssot.py::test_ollama_executor_has_no_inline_persona`
  (satır-içi persona geri doğarsa kırılır) ve
  `test_live_files_have_no_corrupted_turkish` (kodlama bozulması geri gelirse kırılır).

**Ölçümle çürüttüğüm iki varsayım** — ikisi de tasarım sırasında "besbelli"
görünüyordu:

1. *"Zengin personayı L1'e koymak kısa turları yavaşlatır."* **Yanlış.**
   Sıcak L1: SSOT persona (596 token) **2.15s**, minimal prompt (12 token)
   **2.14s**. Fark ölçüm gürültüsü içinde. İlk gözlenen 14s tamamen soğuk
   başlangıçtı (model VRAM'e yükleniyor). Kural: yerel modelde prompt uzunluğu
   maliyetini **varsayma, ölç** — asıl maliyet soğuk başlangıçtır.
2. *"Prompt düzelince karakter düzelir."* **Yetersiz.** Prompt doğru gidiyor
   ama `llama3.2:latest` (L1 rolü) ona uymuyor: 3 denemede `Efendim` **0 kez**
   geçti, cevaplardan biri "Merhaba! Ben Ahmet." diyerek kullanıcıyla kendini
   karıştırdı. Persona yine de ölçülebilir fayda sağlıyor — yapay zekâ kalıbı
   SSOT ile 0/3, minimal prompt ile 1/3. Kural: karakter = prompt **×** model
   kapasitesi. Türkçe persona uyumu için L1 rol modeli ayrıca değerlendirilmeli
   (aday: `qwen2.5:7b`); bu **açık madde**, karara bağlanmadı.

**Ek (aynı gün, L1 model geçişi sonrası):** Benchmark koşuldu ve `local_small`
`llama3.2:latest` → `qwen2.5:7b` oldu (5 L1 sorusu, sıcak: qwen 2.40s /
Efendim 3-5; llama 2.52s / Efendim 0-5 **ve cevaplarda sistem prompt'u
sızıntısı**). Geçiş `config/runtime_profiles.json`'daki "benchmark olmadan
varsayılan değiştirilmez" kuralına uyularak yapıldı.

Geçiş **yeni bir kusur açığa çıkardı ve kusur benim yazdığım metindeydi:**
persona'daki somut örnek cümle ("%23 daha verimli") zayıf modele halüsinasyon
malzemesi oldu — qwen "Nerede kaldık?" sorusuna o sayıyı kullanarak **olmamış
bir konuşma** anlattı. **Kural: bir prompt'a konan her somut sayı/olay, model
tarafından anı olarak geri sunulabilir; örnekler açıkça "yalnızca üslup
örneği, içeriği gerçek değil" diye etiketlenir.** Ayrıca `_ZEMIN` (gerçeklik)
bloğu eklendi ve her seviyede gönderiliyor.

Sonuç kısmi: "Nerede kaldık?" düzeldi (artık "erişimim yok" diyor), ama
"Geçen hafta ne konuşmuştuk?" hâlâ uyduruyor ve selamlamada yapay zekâ kalıbı
sürüyor. **Prompt mühendisliği 7B bir modeli tam kısıtlayamaz** — kalıcı çözüm
modele gerçek kayıt beslemektir (Eşik 3). Bu **açık madde**.

### [2026-08-31] `orchestrator` ad çakışması — kök neden kaldırıldı (izolasyon yaması artık savunma katmanı)

- **Alan:** test altyapısı / import mimarisi
- **Şiddet:** CONCERN (belirti daha önce izole edilmişti, kök neden duruyordu)
- **Tuzak:** Repoda iki `orchestrator` modülü var: `scripts/orchestrator.py`
  (park edilmiş autocoder orchestrator'ı) ve `agents/orchestrator.py`
  (`LLMOrchestrator`, model merdiveni). 2026-08-30'da belirti
  `tests/conftest.py` ile izole edilmişti ama çakışmanın kendisi duruyordu.
- **Kök neden:** `agents/` bir **paket** (`__init__.py` var) ve repo
  konvansiyonu paket-nitelikli import (`from agents.proactive_runtime import ...`).
  `tests/test_blackbox_log.py` bu konvansiyonu bozup `agents/` dizinini **düz
  dizin** olarak `sys.path[0]`'a sokuyordu. Ad çakışması modüllerden değil, bu
  tek satırdan doğuyordu: `agents/` düz dizin olunca `agents/orchestrator.py`
  bare `import orchestrator` ile erişilebilir hale geliyor ve
  `scripts/orchestrator.py`'nin önüne geçiyordu.
- **Kural:** `agents/` ve `tools/` paket olarak import edilir
  (`from agents.X import ...`); bu dizinler **hiçbir zaman** `sys.path`'e düz
  dizin olarak eklenmez. Bir modülün adı iki dizinde birden geçiyorsa çözüm
  yeniden adlandırmak değil, **paket-nitelikli import kullanmaktır** — böylece
  ne parked koda ne de çalışan mimariye dokunulur.
- **Kanıt:** `tests/test_blackbox_log.py:41-47` → `from agents.blackbox_log import`.
  `agents/orchestrator.py`'nin tek tüketicisi `jarvis_brain.py:45` ve zaten
  paket-nitelikli import kullanıyor. Doğrulama: `pytest tests/test_blackbox_log.py
  tests/test_orchestrator.py` → 133 passed, conftest koruması devre dışıyken de
  geçiyor. `ruff check .` 296 → 295 (bir E402 gitti).
- **Regresyon testi:** YOK — açık borç. `tests/conftest.py`'deki
  `pytest_collectstart` koruması artık *savunma katmanı* olarak duruyor:
  kök neden gitti ama biri yeniden `sys.path`'e düz dizin eklerse yakalar.

### [2026-09-02] Boşuna geçen test, sahte alarm üretir — flake'in kök nedeni

- **Alan:** J0 ses hattı, `tests/test_j0_spike_b_latency_probe.py`
- **Şiddet:** BLOCKER (bir gün önceki CONCERN kaydının çözümü — aşağıda)
- **Tuzak:** `test_missing_sounddevice_early_return_has_t0_definition` yaklaşık
  10 koşuda 1 kez kalıyordu ve tekrar üretilemiyordu. Bir gün "flaky test"
  diye kaydedildi, kök neden `[EMİN DEĞİLİM]` bırakıldı.
- **Kök neden — test iddiasını hiç çalıştırmıyordu.** Test `sounddevice`'ı
  `sys.modules.pop()` ile "gizlemeye" çalışıyordu, ama paket bu makinede
  **kurulu**: `_real_probe` onu yeniden import ediyor, `ok=True` dönüyordu.
  İddia bir `if result.get("error") == "sounddevice_not_installed"` bloğunun
  içindeydi, o koşul hiç sağlanmıyordu. Ölçüldü: `error=None`, `ok=True`.

  Boş geçmenin bedeli sessiz değildi. İddia çalışmayınca `_real_probe`
  **gerçek ses donanımı yoluna** giriyor, zamanlamaya bağlı davranıyor ve
  ara sıra kalıyordu. Yani test hem ölçmesi gerekeni ölçmüyor, hem de
  ölçmediği şey yüzünden sahte alarm üretiyordu. Kanıt: düzeltmeden sonra
  dosya izole **8,71s → 0,85s** düştü — o 8 saniye gerçek ses yoluydu.

- **Kural:**
  1. **`if` içine saklanmış iddia, iddia değildir.** Bir testin gövdesi
     çalışma zamanı koşuluna bağlıysa, o koşulun **sağlandığı da ayrıca
     iddia edilmelidir** — yoksa test yeşil kalırken hiçbir şey ölçmez.
  2. **Bir bağımlılığı "gizlemek" için `sys.modules.pop()` yetmez;** paket
     kuruluysa yeniden import edilir. `sys.modules[ad] = None` yazılır —
     bu, import'un ImportError fırlatmasına yol açar (belgelenmiş davranış).
  3. **Testte "kurulu olabilir de olmayabilir de" dallanması varsa, o test
     iki makinede iki farklı şeyi ölçüyordur.** Bağımlılık enjekte edilir.
  4. Bir test beklenenden **uzun sürüyorsa** bunun sebebi aranır: süre,
     gizli bir donanım/ağ yolunun en ucuz göstergesidir.

- **Kanıt:** `error=None, ok=True` ölçümü; dosya süresi 8,71s → 0,92s;
  düzeltme sonrası 3 tam süit koşusu (2 alfabetik + 1 ters) yeşil.
  Yeni testler: iddianın **çalıştığını** doğrulayan `error` kontrolü,
  hiçbir ölçüm yapılmadığını doğrulayan `measurement_valid` kontrolü ve
  donanım yolunun geri gelmesini yakalayan süre eşiği.
- **Regresyon testi:** `test_missing_sounddevice_early_return_has_t0_definition`
  (artık gerçekten çalışıyor), `test_missing_sounddevice_case_measures_nothing`,
  `test_missing_sounddevice_case_is_fast`.

---

#### Kapatılan önceki kayıt — [2026-08-31] FLAKY (aynı test)

- **Alan:** J0 ses hattı, `tests/test_j0_spike_b_latency_probe.py:768`
- **Şiddet:** ~~CONCERN — açık~~ → **ÇÖZÜLDÜ 2026-09-02** (yukarıdaki kayıt)
- **Tuzak:** Tam süit **ters sırada** çalıştırıldığında bu test 5 koşunun
  1'inde başarısız oldu; sonraki 4 ters-sıra koşusunda ve her alfabetik
  koşuda geçti. Tek başına 48/48 geçiyor.
- **Kök neden:** [EMİN DEĞİLİM] Kesin neden tespit edilemedi. Gözlem:
  test `sys.modules`'ten `sounddevice`'ı çıkarıp `_real_probe()` çağırıyor.
  `sounddevice` bu makinede **gerçekten kurulu** (0.5.5), dolayısıyla
  `_real_probe` ImportError yerine gerçek ses cihazı yoluna girebiliyor.
  Gerçek donanıma dokunan bir yol, zamanlama/cihaz meşguliyeti nedeniyle
  nondeterministik olur. Hata izi yakalanamadı çünkü sonraki koşularda
  tekrarlamadı.
- **Kural:** Gerçek donanıma dokunan yol test içinde **koşula bağlı**
  çalıştırılmaz. Bir testin gövdesi "kütüphane kuruluysa şunu yap, değilse
  atla" diye dallanıyorsa, o test iki farklı makinede iki farklı şeyi test
  ediyor demektir — donanım `tests/mocks/mock_hardware.py` ile taklit edilir.
  Bu düzeltme henüz **yapılmadı**.
- **Kanıt:** ters-sıra koşu 1/5 → `1 failed, 1350 passed`; koşu 2-5 →
  `1351 passed`. Alfabetik koşuların hepsi → `1351 passed`.
- **Regresyon testi:** YOK. Flake yeniden üretilemediği için kilitlenemedi.

### [2026-08-30] Test State Pollution & Isolation — süit sıra bağımlıydı, 49 "hata" sahteydi

- **Alan:** test altyapısı (`tests/conftest.py`), orchestrator + J0 ses hattı
- **Şiddet:** BLOCKER (yeşil hattı imkânsız kılıyordu)
- **Tuzak:** `pytest tests` 51 başarısızlık veriyordu; ama aynı dosyalar tek
  başına çalıştırıldığında geçiyordu (`test_orchestrator.py` tek başına 42/42
  geçer, tam süitte 42/42 çökerdi). Yani süit **sıra bağımlıydı** ve
  başarısızlıkların 49'u gerçek kusur değildi. Bu, en tehlikeli hata sınıfıdır:
  gerçek 2 hatayı 49 sahte hatanın içinde gizliyordu.
- **Kök neden:** İki ayrı `sys.modules` sızıntısı vardı.
  1. **Belirsiz modül adı.** Repoda ayn ada sahip iki modül var:
     `scripts/orchestrator.py` ve `agents/orchestrator.py`. `import orchestrator`
     hangisine bağlanacağını `sys.path` sırasından öğreniyor.
     `tests/test_blackbox_log.py:45` modül düzeyinde `agents/` dizinini
     `sys.path[0]`'a sokuyor; alfabetik olarak sonra **toplanan**
     `test_orchestrator.py` ve `test_contractpath_schema_alignment.py` ise
     *scripts* sürümünü bekliyor → `AttributeError: module 'orchestrator' has
     no attribute '_read_verdict'`. Kritik ayrıntı: hasar **toplama
     (collection)** anında oluşuyor, çünkü `import orchestrator` modül
     düzeyinde. Bu yüzden bir fixture çok geç kalır.
  2. **Opsiyonel ses kütüphanesi sızıntısı.**
     `scripts/j0_spike_b_latency_probe.py` çalışma anında `sounddevice` import
     ediyor ve modül `sys.modules`'te kalıyor. `test_j0_voice_adapters.py` /
     `test_j0_voice_loop.py` ise "voice adapter'ı import etmek ağır ses
     kütüphanelerini yüklememeli" diye *import güvenliği* iddia ediyor; kirli
     `sys.modules` yüzünden çöküyorlardı.
- **Kural:** Testler arası izolasyon **tek noktadan**, `tests/conftest.py`'de
  sağlanır; hiçbir test dosyası bunun için değiştirilmez.
  (a) Birden fazla enjekte edilebilir dizinde aynı ada sahip modüller
  *hesaplanarak* bulunur (sabit liste değil) ve her toplama adımında
  `sys.modules`'ten atılır; `scripts/` her zaman `agents/`'ın önünde tutulur.
  (b) Modül düzeyinde import'un bozduğu şey fixture ile değil,
  `pytest_collectstart` kancasıyla onarılır — **fixture toplama anına
  yetişmez.**
  (c) Ağır opsiyonel ses kütüphaneleri her testin hem kurulumunda hem
  sökümünde `sys.modules`'ten atılır; böylece koruma test sırasından bağımsız
  olur.
  (d) Yeşil hat iddiası **tam süit** üzerinde kanıtlanır; ek olarak süit
  **ters sırada** da çalıştırılır. "Tek başına geçiyordu" bir kanıt değildir.
- **Kanıt:** `pytest tests` → 1351 passed (öncesi: 51 failed / 1300 passed).
  Ters sıra (126 dosya) → 1351 passed. Minimal tekrar-üreticiler:
  `test_blackbox_log.py + test_orchestrator.py` → 133 passed;
  `test_j0_spike_b_latency_probe.py + test_j0_voice_adapters.py` → 127 passed.
- **Regresyon testi:** YOK — açık borç. Sızıntının kendisini yakalayan
  bir test yok; koruma kaldırılırsa bunu ancak tam süit fark eder.
  Bu boşluk bilinçli olarak kaydedilmiştir.

### [2026-08-30] Bayat sözleşme iddiası — `assert result is True` DeliveryResult'a karşı

- **Alan:** proaktif teslimat hattı (E1-S6B)
- **Şiddet:** CONCERN
- **Tuzak:** `tests/test_proactive_telegram_adapter.py` içindeki 2 test
  `run_proactive_delivery(...)` çağrısının `is True` / `is False` döndürmesini
  bekliyordu; fonksiyon `DeliveryResult` dönüyor.
- **Kök neden:** E1-S6B, dönüş tipini bilinçli olarak `bool` → `DeliveryResult`
  yükseltti (`tests/test_e1_6b_delivery_result.py` docstring'i: "returns a
  structured DeliveryResult **instead of a bare bool**"). İki iddia bu
  geçişte güncellenmeden kaldı. Testlerin geri kalanı (`calls` iddiaları)
  zaten geçiyordu — yani davranış doğruydu, **iddia bayattı**.
- **Kural:** Bir dönüş tipi genişletildiğinde, o fonksiyonu çağıran **tüm**
  testler aynı commit'te taranır. `is True` / `is False` kimlik
  karşılaştırmasıdır: zenginleştirilmiş bir dönüş tipiyle **hiçbir kaynak
  düzeltmesi** onu geçiremez — bu yüzden böyle bir başarısızlık her zaman
  "kaynak mı bayat, test mi bayat" sorusunu zorunlu kılar; sessizce kaynağı
  bool'a geri döndürmek yanlış cevaptır.
- **Kanıt:** `agents/proactive_runtime.py:18` (`-> DeliveryResult`),
  `tests/test_e1_6b_delivery_result.py:1-7`
- **Regresyon testi:** `tests/test_e1_6b_delivery_result.py::test_delivery_result_is_dataclass`
  (sözleşmeyi zaten kilitliyor)

### [2026-09-06] `eval` sandbox'a kapatılamaz — boş `__builtins__` bir güvenlik sınırı değildir

- **Alan:** `tools/tools.py` → `calculate` (Codex denetimi B01)
- **Şiddet:** BLOCKER
- **Tuzak:** `eval(expression, {"__builtins__": {}}, safe_dict)` bir kum havuzu
  sanıldı. Boş `__builtins__` yalnız ADLARI gizler, **nesne grafiğini değil**:
  `().__class__.__base__.__subclasses__()` ile tüm sınıflara, oradan
  `catch_warnings.__init__.__globals__['__builtins__']` ile gerçek
  yerleşiklere dönülüyordu. Danışman canlı doğruladı — zincir `sum([20,22])`
  → **42** döndürdü; aynı yoldan `open` ve `__import__('os').system` de
  erişilebiliyordu.
- **Kök neden:** İki ayrı yanılgı. (a) Ad görünürlüğü ile yetenek sınırı
  karıştırıldı: Python'da her nesne kendi tip grafiğini taşır, adları saklamak
  erişimi kaldırmaz. (b) Yüzeyin `run_python_code` ajandan çıkarılınca
  kapandığı varsayıldı; oysa `calculate` "hesapla" tetikleyicisinden
  ulaşılabilen **ikinci** yoldu ve açık kaldı.
- **Kural:** Kullanıcı girdisi `eval`/`exec`'e hiçbir sarmalayıcıyla
  verilmez. Kara liste (dunder süzgeci, `getattr` yasağı) tarihsel olarak hep
  delindi; gereken beyaz listedir — `ast.parse(..., mode="eval")` + ele
  alınmayan her düğüm türünü reddeden bir yorumlayıcı. Kaynak tüketmesi de bir
  saldırıdır: `9**9**9` hesaplanmadan **önce** reddedilmeli.
- **Kanıt:** `tools/tools.py:545` (`_eval_node`, beyaz liste),
  `tools/tools.py:536` (`_guarded_pow`, üs sınırı).
  Test önce kırmızı görüldü: 12 başarısız, iddia metni
  `"... = 42"`; kaynak düzeltildikten sonra 26 geçti.
- **Regresyon testi:** `tests/test_calculate_sandbox.py` — istismarın kendisi,
  nesne grafiğinin her halkası ve kaynak sınırları, `LocalJarvisAgent`
  `_detect_tool` → `_run_tool` **tam yolundan** sınanır; fonksiyonu doğrudan
  çağırmak ajanın o fonksiyona giden yolunu kanıtlamaz.

---

## Kalıcı tuzak listesi (repo genelinde bilinen, tekrar eden sınıflar)

Bunlar tek bir olaya değil, bu repoda **tekrar tekrar** ortaya çıkan
hata sınıflarına karşılık gelir. Yeni kod yazarken önce buraya bakılır.

- **Türkçe `.lower()` tuzağı** — `"İ".lower()` combining-dot üretir,
  `"I".lower()` `'i'` verir (Türkçe'de `'ı'` olmalı). Düz `.lower()` ile
  keyword eşleştirme sessizce KAÇIRIR. Kural: eşleştirmede her iki tarafa
  da aynı ASCII-fold uygulanır (`_fold_tr`). Bkz. `CLAUDE.md` §6.
- **PowerShell paste'i Türkçe karakteri bozar** ve BOM ekler. Kural:
  patch `@' ... '@ | python` here-string ile verilir, içinde `"""`
  kullanılır, asla `'''`. Bkz. `CLAUDE.md` §5.
- **"Başarılı" demeden önce görmek** — patch sonrası `py_compile` +
  `git status`/`git diff` + import smoke çalıştırılmadan hiçbir iş
  tamamlandı sayılmaz. Bkz. `CLAUDE.md` §5.
- **Doküman ↔ durum dosyası kayması** — iki dosya aynı gerçeği farklı
  anlatabiliyor (ör. `HUMAN_NEEDED.md` "Pending" derken
  `roadmap_state.json` "DONE" diyor). Kural: bir gerçeğin tek bir
  doğruluk kaynağı olur; ikinci yer ona *referans verir*, kopyalamaz.
- **Kendi ürettiğini kendin doğrulama önyargısı** — "bunu ben yazdım,
  iyi olduğunu düşünüyorum". Kural: stratejik "sıradaki adım doğru mu"
  sorusu ayrıca sorulur; Codex diff-review'ı bunu kapatmaz.
  Bkz. `CLAUDE.md` DANIŞMAN MODU.


### [2026-09-07] A-03: math function results can escape numeric bounds

- Trap: allowing every math callable also allowed frexp/modf tuple results;
  tuple multiplication bypassed the exponent limit.
- Root cause: the AST validated syntax and selected expensive functions,
  but did not validate the type and size of every intermediate value.
- Rule: each AST result must be a finite numeric scalar; integer results
  stay within the existing 10000-bit ceiling before a parent operation runs.
  This is an arithmetic bound, not a general CPU/time sandbox guarantee.
- Evidence: eight new tests failed before the patch; all 34 calculator
  tests pass afterward. The billion-repeat regression replaces only the
  multiply primitive, so the test never allocates the dangerous tuple.


### [2026-09-07] A-05: deletion promises must name their storage scope

- Trap: SQL DELETE was described as forgetting without distinguishing
  logical row removal from irrecoverable physical erasure.
- Root cause: successful SELECT-after-DELETE tests cannot establish that
  database pages, journals/WAL, snapshots or backups contain no old bytes.
- Rule: this operation promises logical conversation removal only, retains
  profile/events, and tells the user that disk/backup secure erasure is not
  guaranteed. Physical recovery risk is disclosed, not claimed fixed.
- Evidence: two user-notice tests failed first; all ten memory tests pass,
  including the existing agent-to-storage clearing path. Full disk erasure
  remains outside the approved v2 card.


### [2026-09-07] B08: retire an unsupported entry instead of reviving it

- Trap: API credentials selected a legacy JarvisAgent entry that imported
  nonexistent MemoryManager; a simple alias would also revive unsafe tools.
- Root cause: automatic mode selection outlived the entry's memory contract.
- Rule: an explicitly retired entry must be removed from source, dispatch
  and active inventory; credential presence must not select it again. The
  supported AssistantExecutor/APIExecutor path is a separate implementation.
- Evidence: three retirement checks failed first; all four then passed,
  plus two existing local CLI checks. Explicit claude mode exits with a
  retirement message and code 2 before any agent is constructed.


### [2026-09-07] B09: tools need execution boundaries, not prompt promises

**B09 review finding corrected with Ahmet's explicit continuation approval
(2026-09-08).** Both git_diff branches now select exact changed file names
before requesting content; checking only the worktree type was insufficient
because an index directory can have become a worktree file. Directory,
missing-path and index-prefix regressions were each observed RED first;
67 boundary/calculator/local-surface checks pass, and independent rereview
returned PASS. Historical stop record: automation/CODEX_V2_UYGULAMA_2026-09-07.md.

- Trap: a retired caller did not retire the shared tool implementation;
  unverified TLS, unrestricted paths, shell interpolation and in-process
  Python execution still existed in tools/tools.py.
- Root cause: permission checks were attached to selected callers or tool
  names instead of shared I/O and execution boundaries.
- Rule: generic file tools accept non-secret project-relative paths and
  validate resolved junction/symlink targets; writes show content and ask
  the human. Helper commands use argv and literal git pathspecs, searches
  use filesystem APIs, and TLS validation stays enabled. Direct Python
  execution is retired. Explicit terminal commands still require human
  approval and have the permissions of that approved command.
- Evidence: 23 new boundary checks failed before the patch; 62 focused
  boundary/calculator/local-surface tests then passed. No live network,
  real secret files or user documents were used by these probes.
- Scope: filename/path policy is not content classification or an OS
  sandbox against concurrent hostile filesystem mutation. The existing
  explicit desktop PDF import workflow is separate and unchanged.


### [2026-09-08] B10: routing is not API execution

- Trap: local conversation consumed the external budget and stopped when it
  ran out; a cloud attempt could be counted by both router and executor.
  Redaction/web-policy exceptions also fell through to external execution.
- Root cause: ask_external describes missing local knowledge, not a chosen
  cloud provider. Cost consumption was placed before execution policy.
  Older tests encoded this bug by expecting the router to block all answers
  and permitting ask_external after a policy exception.
- Rule: only the existing APIBudgetGate at the actual API execution boundary
  consumes a unit. Local generation remains available after budget denial.
  Failed guards return a blocked decision; they cannot authorize external I/O.
  CostLedger counts admitted attempts, not tokens, currency or billing.
- Evidence: four new regressions failed before the source patch. Ahmet then
  explicitly authorized strengthening four obsolete tests: verify zero API
  calls AND an actual local answer for budget denial; blocked decision AND
  zero API/web calls for guard failure. Relevant five test files: 35 passed.
  All four strengthened legacy tests also fail against the old router
  loaded only in memory, without reverting working files. Full-suite results
  are recorded separately in the B10 completion report.
