# İmzasız iş kuyruğu

**Üretildi:** 2026-09-08 · **Kart:** `automation/KART_IMZASIZ_KUYRUK.md`

Buradaki her madde **Ahmet'in kararını gerektirmez**: doğru davranış
tartışmalı değil, ya ölçülmüş bir hata ya da yalnızca araştırma.

> **Otomatik zincirleme yok** (CLAUDE.md §9). Bir madde bitince durulur.
> Kuyruğun amacı otonomi değil, Ahmet'in "sıradaki iş ne" diye
> düşünmek zorunda kalmaması.

**Kuyruk etki sırasına dizildi, kolaylık sırasına değil.** K1 kullanıcının
her web aramasını bozuyor; K12 lint borcu.

**İmza gerektirenler burada DEĞİL** → `automation/AHMET_ONAYI_BEKLEYENLER.md`
(A16–A21). Bir madde başladıktan sonra imza gerektirdiği anlaşılırsa:
durulur, oraya taşınır, sebebi buraya yazılır.

**Codex sınırı:** Codex şu an `tools/`, `memory/`, `agents/`,
`agent/jarvis_agent.py` içinde (B09 açık CONCERN, B10 başlamadı —
`automation/CODEX_V2_UYGULAMA_2026-09-07.md`). O alanlara dokunan maddeler
**"Codex'te — beklemede"** işaretli; okumak serbest, yazmak değil.

---

## K1 — `_detect_tool` arama sorgusunu bozuyor

**Nerede:** `agent/local_agent.py:539-545`

**Ölçüldü (2026-09-08):**

```
"son haberler nedir"           -> query: "son ler nedir"
"yapay zeka haberleri arastir" -> query: "yapay zeka leri arastir"
```

Anahtar kelimeler ham `str.replace` ile siliniyor; "haber" kökü
"haberler" kelimesinin **ortasından** kesiliyor ve arama sağlayıcısına
anlamsız bir dize gidiyor.

**Neden imza gerekmiyor:** Düpedüz hata; doğru davranış tartışmalı değil.
İki ayrı commit mesajında zaten adı konmuş borç: `a39dca6`
("[AYRI KUSUR, DUZELTILMEDI] Bozuk sorgu arama sağlayıcısına o hâliyle
gidiyor") ve `be8faaf`. Dosya benim kümemde.

**Neden en üstte:** Kullanıcının yaptığı **her** web aramasını sessizce
bozuyor — ölçülen tek çıktı "bozuk sorgu" ve kullanıcı bunu göremiyor.
Ayrıca A-04 kırpmanın orijinalde olmayan **hassas** bir dize
üretebildiğini gösterdi (`"paara rola X son haberler"` →
`"parola X son ler"`); yani bu yalnız kalite değil, güvenlik kapısının
komşusu.

**Kabul ölçütü:** "son haberler nedir" sorgusu bozulmadan gidiyor;
kırpma yalnız kelime sınırında yapılıyor; A-04'ün ürettiği hassas dize
senaryosu hâlâ engelleniyor (mevcut testler yeşil kalıyor).

> **Bu ölçütün ikinci ve üçüncü maddesi birbiriyle ÇELİŞİYOR** — ADIM
> 1'de yazarken görülmedi. A-04 testi tam olarak kırpmanın kelime
> ortasından kesmesine dayanıyor (`"paara rola X"` → `"parola X"`);
> kelime sınırına geçmek o senaryoyu ortadan kaldırır. Madde bu yüzden
> ikiye bölündü.

**Büyüklük:** orta

### K1a — konu kelimesi artık kesilmiyor ✅ KAPANDI

**Commit:** `b91bf1b` · 11 test, 8'i kırmızı görüldü.

"haber" ve "ne oldu" kırpma listesinden çıkarıldı: ikisi de komut
değil, kullanıcının aradığı konu. Ölçülen sonuç:

```
"son haberler nedir"          -> "son haberler nedir"    (önce: "son ler nedir")
"deprem haberi var mi"        -> "deprem haberi var mi"  (önce: "deprem i var mi")
"yapay zeka hakkında araştır" -> "yapay zeka hakkında"   (komut hâlâ kırpılıyor)
```

Kapı: 1881 passed / 1 xfailed (iki sırada), ruff 283, taban 49.

### K1b — komut kalıpları kelime sınırına geçti ✅ KAPANDI

**Commit:** `1ffc7ce` · 4 test, hepsi kırmızı görüldü.
**Karar:** A22 — Ahmet "üçüncü yol: ikisi de yaşasın" dedi.

Ölçülen kusur ve sonucu:

```
"ankara haberleri"       -> "ankara haberleri"       (önce: "ankhaberleri")
"para araci haberleri"   -> "para araci haberleri"   (önce: "paraci haberleri")
"YAPAY ZEKA ... ARAŞTIR" -> "YAPAY ZEKA HAKKINDA"    (önce: hiç kırpılmıyordu)
```

Eşleştirme artık fold'lanmış metinde ve `\b` kelime sınırında; silme
orijinal metinden, büyük harf ve Türkçe karakter korunuyor.

**A-04 testinin girdisi değişti** (Ahmet onayı): `"paara rola X son
haberler"` → `"parola X son haberler"`. Eski girdinin gücü kırpma
kusuruna dayanıyordu; K1b onu kapattığı için o girdi artık meşru bir
sorgu. Yeni girdi gerçekten hassas ve `sensitive_blocked`.

**Kapsam kaybı kapatıldı:** yeni girdi orijinal cümlede zaten hassas
olduğu için kapı **ilk** katmanda (B03) kapanıyor ve A-04'ün eklediği
ikinci katmanı sınamıyordu. `test_orijinal_temizken_nihai_sorgu_yine_denetlenir`
eklendi — orijinal `allow=True`, nihai sorgu `sensitive_blocked`;
A-04 kapısı kaldırılırsa yalnız o test kırmızı yanar.

Kapı: 1891 passed / 1 xfailed (iki sırada), ruff 283, taban 49.

---

## K2 — `test_mutation_gate::test_weak_tests_leave_survivor` yanıp sönüyor ✅ KAPANDI

**Commit:** `c815ee8` · 8 test, 6'sı kırmızı görüldü.

**Kök neden ölçüldü, hipotez yanlış çıktı.** Aşağıda "en olası sebep"
diye yazdığım eşzamanlılık hikâyesi *tetikleyiciydi*, sebep değil.
Gerçek sebep `scripts/mutation_gate.py:119`'daydı:

```python
if cp.returncode != 0:
    killed += 1        # "testler bug'i yakaladi"
```

Sıfırdan farklı **her** çıkış kodu "mutant yakalandı" sayılıyordu.
Ölçülen sonuç: test komutu hiç çalışmadığında kapı **skor 1.0**
veriyordu — anti-test-gaming aracı, bozuk bir test komutuna
"testleriniz kusursuz" diyordu.

```
"pytest <olmayan dosya>" (exit 4) -> skor=1.0  survivors=0
"sys.exit(2)" / "(3)" / "(5)"     -> skor=1.0  survivors=0
```

Artık yalnız `exit 1` öldürüldü sayılıyor; ölçüm yapılamadığını
söyleyen kodlar `MutationGateError` ile gürültülü düşüyor.
`FAILURES.md` kaydı eklendi. Timeout=öldürüldü sözleşmesi değişmedi.

**Açık borç (görünür bırakıldı):** Windows kabuğu bulunamayan komut
için de `1` döndürüyor; o vaka çıkış koduna bakarak ayrılamıyor ve hâlâ
"öldürüldü" sayılıyor. `test_BILINEN_SINIR_bulunamayan_komut_ayirt_edilemiyor`
bunu kilitliyor.

Kapı: 1899 passed / 1 xfailed (iki sırada), ruff 283, taban 49.

*Aşağısı maddenin yazıldığı andaki kayıttır.*

**Nerede:** `tests/test_mutation_gate.py:50`

**Ölçüldü (2026-09-07):** Tam süitte `assert 1.0 < 0.8` ile düştü
(1792 passed / 1 failed); aynı dosya tek başına 5/5 geçti; hemen sonraki
tam süit koşusu yeşil geldi. Skorun 1.0 olması "her mutant öldü" demek —
zayıf test verildiği hâlde. En olası sebep: `run_gate` alt-süreçte
`pytest` çalıştırıyor ve eşzamanlı ikinci bir pytest koşusunda o
alt-süreçler kendi sebepleriyle düşüp mutantları "öldürülmüş" sayıyor.
**Bu bir hipotez, kanıtlanmadı.**

**Neden imza gerekmiyor:** Kapı testinin güvenilirliği. Yanıp sönen bir
kapı testi, her "1821 passed" iddiasını değersizleştirir; kök nedeni
bulmak kimsenin kararını gerektirmez.

**Neden bu sırada:** Projenin tüm disiplini "kapıyı geç, sonra bitti de"
üstüne kurulu. Kapının kendisi güvenilmezse K1'den sonraki her madde de
şüpheli olur.

**Kabul ölçütü:** Yanıp sönmenin kök nedeni **ölçülmüş** (tahmin değil);
test ya deterministik hâle getirilmiş ya da neden kaçınılmaz olduğu
`FAILURES.md`'ye yazılmış. Süit 20 ardışık koşuda aynı sonucu veriyor.

**Büyüklük:** orta

---

## K3 — Üç dosya BOM (U+FEFF) taşıyor ✅ İKİSİ KAPANDI, BİRİ CODEX'TE

**Commit:** `a21bd97` · 7 test, 4'ü kırmızı görüldü.

324 `.py` tarandı; BOM dışında ayrıştırma hatası yok.
`tests/conftest.py` ve `tests/test_api_executor.py` temizlendi —
bayt düzeyinde, gövde sha1 korunarak, her birinde tek satır diff.

`agents/api_executor.py` **dokunulmadı** (Codex `agents/` içinde).
Kusur silinmedi, strict xfail ile görünür bırakıldı; BOM kaldırıldığı
an kırmızı yanar.

İki yeni depo-geneli kilit eklendi: yeni BOM'lu dosya sessizce
eklenemez, ve her `.py` `ast.parse` ile ayrıştırılabilir olmalı.

Kapı: 1904 passed / 2 xfailed (iki sırada), uyarı sayısı 2'de kaldı,
ruff 283, taban 49.

*Aşağısı maddenin yazıldığı andaki kayıttır.*

### K3 (kayıt) — Üç dosya BOM (U+FEFF) taşıyor, AST hiçbiri okuyamıyor

**Nerede:** `agents/api_executor.py:1` · `tests/conftest.py:1` ·
`tests/test_api_executor.py:1`

**Ölçüldü (2026-09-08):** Üçünde de ilk üç bayt `EF BB BF`;
`ast.parse()` üçünde de `invalid non-printable character U+FEFF` veriyor.
Kaynak: `docs/JARVIS_ENVANTER.md` §I "Ayrıştırılamayan dosyalar".

**Neden imza gerekmiyor:** `CLAUDE.md` §5'in adını koyduğu tuzak
("PowerShell paste Türkçe karakteri bozar + BOM ekler"). Python dosyası
BOM taşımaz; bayt düzeyinde düzeltme, davranış değişmez.

**Neden önemli:** `tests/conftest.py` süitin **tek** izolasyon
garantisidir (`FAILURES.md` → "Test State Pollution & Isolation") ve
hiçbir statik denetim aracı onu okuyamıyor. Envanterin ve gelecek her
AST taramasının tam bu dosyada kör noktası var.

**Kabul ölçütü:** Üç dosya da `ast.parse` ile ayrıştırılıyor; süit iki
sırada yeşil; envanter yeniden üretildiğinde "ayrıştırılamayan" listesi
boş.

**Büyüklük:** küçük

**Durum:** `tests/` altındaki iki dosya serbest;
`agents/api_executor.py` **Codex'te — beklemede**. Üçü birden
kapanmadan envanter kör noktası tam kapanmaz.

---

## K4 — Envanterin otomatik bölümü bayat: `gui.py` hâlâ canlı giriş noktası

**Nerede:** `docs/JARVIS_ENVANTER.md` §B (giriş noktaları tablosu)

**Ölçüldü (2026-09-08):** Tablo `gui.py`'yi "buradan erişilen dosya
sayısı 15" diye listeliyor; `gui.py` B02'de (`1c0974a`) emekliye
ayrıldı ve diskte **yok**. `agent/jarvis_agent.py` de B08'de
(`61bdbf4`) kaldırıldı.

**Neden imza gerekmiyor:** `scripts/envanter_uret.py` zaten var ve
belgenin kendisi "Bu bölüm elle düzenlenmez" diyor. Var olan üreticiyi
çalıştırmak ölçüm **tanımını** değiştirmez, ölçümü tazeler.

**Neden önemli:** Envanter bu kuyruğun ve gelecek kararların girdisi.
Bayat bir envanter, olmayan bir dosyayı canlı gösterir — `CLAUDE.md`
§10'un "olgu koda ve anayasaya yazılmaz, canlı dosyadan okunur"
kuralının belge tarafındaki karşılığı.

**Kabul ölçütü:** `python scripts/envanter_uret.py` çalıştırıldı;
`gui.py` ve `agent/jarvis_agent.py` tablolardan düştü; işaretçinin
**üstündeki** elle yazılmış bölüm korundu; sayılar commit mesajında
öncesi/sonrası olarak yazılı.

**Büyüklük:** küçük

---

## K5 — Test izolasyon sızıntısının regresyon testi yok

**Nerede:** `FAILURES.md:256` ve `FAILURES.md:368` — ikisi de
"**Regresyon testi:** YOK — açık borç"

**Kayıtlı durum:** `tests/conftest.py`'deki `pytest_collectstart`
koruması "savunma katmanı olarak duruyor: kök neden gitti ama biri
yeniden `sys.path`'e düz dizin eklerse yakalar". Ve: "Sızıntının
kendisini yakalayan bir test yok; koruma kaldırılırsa bunu ancak tam
süit fark eder."

**Neden imza gerekmiyor:** Eksik bir test yazmak. Sözleşme
değişmiyor, kaynak davranışı değişmiyor.

**Kabul ölçütü:** conftest korumasını devre dışı bırakan bir test,
sızıntının **kendisini** yakalıyor (tam süit çalıştırmadan);
`FAILURES.md`'deki iki "açık borç" satırı test adıyla değiştirildi.

**Büyüklük:** orta

---

## K6 — `LocalJarvisAgent.__init__` `self.memory`'yi iki kez atıyor

**Nerede:** `agent/local_agent.py:244` (ölü) ve `:249` (gerçek)

```python
244:  self.memory = self._load_memory()      # LocalMemory() -- ATILIYOR
249:  self.memory = JarvisMemory()           # ustune yaziliyor
```

**Neden imza gerekmiyor:** Ölü atama; gözlenebilir davranış değişmez.

**Ölçülmesi gereken:** `_load_memory()` → `LocalMemory()` yapıcısının
yan etkisi var mı (dosya/DB açıyor mu). Varsa bu yalnız ölü kod değil,
**her açılışta sızdırılan bir kaynak**. Kaldırmadan önce ölçülür.

**Kabul ölçütü:** Ölü atamanın kaldırıldığı ve `LocalMemory`'nin artık
kurulmadığı testle gösterildi; `self.memory` hâlâ `JarvisMemory`.
`LocalMemory` **silinmedi** (§3: gör, söyle, silme) — yalnız bu
çağrı yeri kaldırıldı.

**Büyüklük:** küçük

---

## K7 — Öneri belgeleri tamamlanmış iş gibi okunuyor

**Nerede:** `docs/OSS_HARVEST_REPORT_2026-08.md` ·
`automation/FAZ4_ADIM_ONERISI.md` — envanter §G, Ç4

**Ölçüldü:** Bu iki belgede adı geçen **21 `.py` dosyası** diskte yok
(`core/log_safety.py`, `llm/tiers.py`, `memory/recall_gate.py`,
`hwfit/fit.py`, `agents/presence_model.py`, `scripts/gen_uydu.py`, …).
Envanter bunu Ç4'te "büyük olasılıkla öneri, iddia değil" diye
kaydetmiş ama **[EMİN DEĞİLİM]** işaretiyle.

**Neden imza gerekmiyor:** Yapılacak şey yorum değil, **ölçülmüş
olgunun** belgeye eklenmesi: "bu belgede anılan şu dosyalar
2026-09-08 itibarıyla repoda yok". Belgenin niyeti hakkında hüküm
verilmiyor, hiçbir şey silinmiyor.

**Kabul ölçütü:** Her iki belgenin başına ölçüm tarihli "anılan şu
dosyalar repoda yok" bloğu eklendi; liste envanterden üretildi,
elle yazılmadı.

**Büyüklük:** küçük

---

## K8 — 13 yetim modülün **neden** yetim olduğunu araştır

**Nerede:** `docs/JARVIS_ENVANTER.md` §D — `dev_patches/project_inspect_v2.py`,
`mcp/__init__.py`, `memory/jarvis_db.py`, `tools/browser_agent.py`,
`tools/document_analyst.py`, `tools/document_writer.py`,
`tools/jarvis_interpreter.py`, `tools/project_analyst.py`,
`tools/save_conversation.py`, `tools/vision_analyst.py`,
`tools/wake_word.py`, `tools/web_research_eski.py`,
`voice/voice_interface.py`

**Neden imza gerekmiyor:** Araştırma imza gerektirmez. **Silmek**
gerektirir (§3) → A20.

**Kabul ölçütü:** Her dosya için tek satır: "yerine geçen X" /
"hiç bitmemiş" / "tarihsel". Kanıt commit geçmişi ve içerik; tahmin
[EMİN DEĞİLİM] ile işaretli. Çıktı `automation/`'a yazılır, hiçbir
dosya silinmez.

**Büyüklük:** orta

**Durum:** 8'i `tools/`, 1'i `memory/` → o dosyalara **yazmak**
Codex'te. Okumak ve araştırma yazmak serbest.

---

## K9 — 24 "yalnız-test" modülü: hazırda mı bekliyor, terk mi edilmiş

**Nerede:** `docs/JARVIS_ENVANTER.md` §C `agents/` tablosu, Ç5

**Kayıtlı gözlem:** "bir modülün tek kullanıcısının kendi testi olması,
'entegre' ile 'yazılmış' arasındaki farkın tam ölçüsüdür." 24'ünün
**hepsi** `agents/` altında.

**Neden imza gerekmiyor:** Araştırma. Bağlamak mimari karardır → A19.

**Kabul ölçütü:** Her modül için "hangi adımın parçası, neden bağlı
değil" tek satır; kaynak `roadmap_state.json` ve commit geçmişi.

**Büyüklük:** orta

**Durum:** **Codex'te — beklemede** (kod dokunuşu için). Araştırma serbest.

---

## K10 — `find_and_load_pdf` kullanıcının belirttiği dosyayı seçmiyor

**Nerede:** `tools/tools.py` → `find_and_load_pdf`

**Kayıtlı durum:** `eca272d` commit gövdesi: *"KAPSAM DISI,
duzeltilmedi: find_and_load_pdf hala kullanicinin belirttigi dosyayi
cozmek yerine EN YENI PDF'yi seciyor, ve add_documents her cagrida ayni
belgeleri tekrar ekleyebiliyor (tekillestirme yok)."*

**Neden imza gerekmiyor:** Kullanıcı "rapor.pdf oku" diyor, başka bir
dosya açılıyor. Doğru davranış tartışmalı değil.

**Kabul ölçütü:** Codex'in yazdığı kabul testi: "belirtilen A dosyası
varken daha yeni B seçilmez". Ayrıca `add_documents` tekilleştirme.

**Büyüklük:** orta

**Durum:** **Codex'te — beklemede** (`tools/`).

---

## K11 — `agents/api_budget_gate.py` üretimden hiç çağrılmıyor

**Nerede:** envanter Ç2 — modül testleriyle birlikte duruyor, dış model
çağrısı yapan hat (`assistant_executor` → `executor_registry` →
`api_executor`) bütçe kapısından **geçmiyor**.

**Neden imza gerekmiyor:** "Neden bağlı değil, bağlanırsa nereye
girer" sorusunun araştırılması. **Bağlamak** mimari yön değişikliğidir
ve maliyet davranışını değiştirir → A19.

**Kabul ölçütü:** Kapının beklediği arayüz ile çağrı hattının
sunduğu arayüz yan yana yazıldı; bağlamanın maliyeti ve riski
ölçüldü. Kod değişmedi.

**Büyüklük:** küçük

**Durum:** **Codex'te — beklemede** (`agents/`).

---

## K13 — `scripts/j0_mic_check.py` geçersiz kaçış dizisi taşıyor

**Nerede:** `scripts/j0_mic_check.py`

**Ölçüldü (2026-09-08, K3 sırasında yan bulgu):** Dosya `'\.'` geçersiz
kaçış dizisi içeriyor; `ast.parse` sırasında
`DeprecationWarning: invalid escape sequence '\.'` üretiyor. Depodaki
324 `.py` içinde bu uyarıyı veren tek dosya.

**Neden imza gerekmiyor:** Ham dize (`r"..."`) kullanılmamış bir regex;
doğru davranış tartışmalı değil. Python 3.12'de bu uyarı `SyntaxWarning`
oldu, ileride hata olacak.

**Kabul ölçütü:** Dosya `-W error::DeprecationWarning` altında
ayrıştırılıyor; `tests/test_kaynak_hijyeni.py` içindeki uyarı
susturması kaldırılabiliyor.

**Büyüklük:** küçük

---

## K14 — `run_turkish_quality.py` `.env`'i hiç yüklemiyor ✅ KAPANDI

**Commit:** `3b44d80` · 2 test, 1'i kırmızı görüldü. Aynı commit'te ağ
yeniden denemesi ve puanlayıcı etiketi de düzeltildi (asıl kusur oydu).

**Nerede:** `eval/run_turkish_quality.py:401`

**Ölçüldü (2026-09-09, Ahmet frontier ölçümünü başlatırken):**

```python
anahtar = os.environ.get(tanim["env"], "").strip()
```

Betik anahtarı **yalnız ortam değişkeninden** okuyor ve `.env` dosyasını
hiç yüklemiyor. `main.py:26` `load_dotenv()` çağırıyor, bu betik
çağırmıyor. Sonuç: `.env` doğru doldurulmuş olsa bile `--saglayici`
yolu "anahtar yok" diyor.

**Ahmet bunu canlı yaşadı.** Geçici çözüm, `.env`'i PowerShell'de elle
ayrıştırıp oturuma yüklemek oldu — işe yaradı ama her yeni terminalde
tekrar gerekiyor.

**Neden imza gerekmiyor:** `python-dotenv` **zaten bağımlılık**
(`main.py` kullanıyor), yeni teknoloji yok. Betiğin belgelenen davranışı
ile gerçek davranışı arasındaki fark; doğru davranış tartışmalı değil.

**Neden önemli:** Bu betik "yerel mi bulut mu" kararını besleyen tek
ölçüm aracı. Kurulum sürtünmesi ölçümün **yapılmamasına** yol açar —
nitekim `.env` bir gündür duruyordu ve ölçüm bu yüzden alınmamıştı.

**Kabul ölçütü:** `.env` varken `--saglayici deepseek` ek bir kabuk
komutu gerektirmeden çalışıyor; ortam değişkeni zaten tanımlıysa
**`.env` onu ezmiyor** (öncelik: gerçek ortam > dosya); `.env` yoksa
davranış değişmiyor. Anahtarın hiçbir kod yolunda loglanmadığı testle
kilitli. **`.env` dosyasının içeriği hiçbir teste girmez** (§9).

**Büyüklük:** küçük

---

## K12 — `ruff` borcu 283

**Nerede:** repo geneli

**Neden imza gerekmiyor:** Taban kuralı "artmasın" diyor; azaltmak
`CLAUDE.md` §13.2'de zaten **ayrı bir kart** olarak yazılı.

**Kabul ölçütü:** Ayrı kartın kendi ölçütü. Bu kuyrukta yalnız
görünürlük için duruyor; en sonda olması bilinçli — 283 bulgunun
hiçbiri kullanıcıya yanlış cevap verdirmiyor.

**Büyüklük:** büyük

---

## Kuyruğa ALINMAYANLAR

| Konu | Nereye | Neden |
|---|---|---|
| `auto_runner.py` docstring'i hâlâ "Tek komut: python auto_runner.py" diyor | A16 | Park edilmiş cephe (§9) |
| `jarvis_server.py` → `0.0.0.0:8000`, kimlik doğrulama yok | A17 | Park edilmiş cephe komşusu |
| `config/provider_profiles.json` yok ama üretim kodu okuyor | A18 | Gerçek yapılandırma dosyası |
| `api_budget_gate` / 24 modülü hatta bağlamak | A19 | Mimari yön değişikliği |
| 13 yetim modülü silmek | A20 | §3: gör, söyle, silme |
| `redaction_guard` + `web_research_policy` desen sıkılaştırma | A21 | D2 eval ölçümünü oynatır |
| Letta çelişkisi | CLAUDE.md §12 | Zaten açık, Ahmet'in kararı |
