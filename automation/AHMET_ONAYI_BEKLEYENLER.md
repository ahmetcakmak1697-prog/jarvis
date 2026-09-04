# AHMET ONAYI BEKLEYENLER

Gözetimsiz çalışma sırasında karar kapısına gelindiğinde buraya yazılır ve
bağımsız bir sonraki işe geçilir. **Hiçbiri Claude tarafından kararlaştırılmaz.**

Açıldı: 2026-09-01, gözetimsiz oturum.

---

## KARARLANMIŞ (2026-09-01)

- **A1** Turkish-Gemma indirme → **HAYIR** (şimdilik). Önce mistral-nemo
  çıkışının kulakla etkisi görülecek; ölçülmemiş iyileştirmenin üstüne yeni
  değişken eklenmeyecek. 8K bağlam sınırı da gerçek risk.
- **A2** `runtime_profiles.json` → **EVET**: `local_main` → `llama3.1`,
  `local_small` → `qwen2.5:7b` (değişmiyor). Profil değişikliği tek başına
  dursun diye **en son, ayrı commit'te** uygulanıyor.
- **A3** SkillSpector → `run_python_code` ajan sözlüğünden çıkarıldı;
  `tools.py` değişmedi. `__pycache__` bulguları gürültü olarak işaretlendi.
- **A4** `_load_project_context()` dinamikleştirilmesi → **EVET**, sözleşme
  değişikliği onaylandı.

---

## KARARLANMIŞ (2026-09-04)

- **A13** Tekrar dedektörü eşiği → **3'te KALIR.** 2× eşiği ayrıca ölçülüp
  **raporlanır ama puanlanmaz** (`has_efendim` ile aynı sınıf).
  *Gerekçe:* 2×'in "yanlış pozitif yok" ölçümü **tek** modelin 64 cevabı
  üzerinde yapıldı. Bu takımın varlık sebebi modelleri kıyaslamak;
  llama3.1'de temiz olan eşik başka modelde, paralel kurulmuş bir listede
  tökezleyebilir — dedektör liste **işaretini** atıp **içeriğini** bıraktığı
  için (ki bu doğru karardır: gözlenen dejenerasyonların dördü de madde
  içlerindeydi). Asimetri `_NO_RECORD_ROOTS` notundakiyle aynı: iyi bir
  cevabı haksız yere düşürmek ölçümün kendisini çürütür.
  *Uygulandı:* `REPETITION_REPORT_MIN_HITS = 2`, `repeated_phrase_2x` alanı,
  raporda `Tekrar 2× (raporlanır, puanlanmaz)` satırı. Ölçülen: **8/64**
  (bunların 3'ü zaten puanlanan eşikte de düşüyor). Skor **49/64** değişmedi.
- **A14** `passing_threshold` bloğu → **taban kaydına dönüştü.** Yeni bir
  hedef sayı **yazılmadı** (">=47" vb. yasak — az önce kurtulduğumuz "sayıyı
  tutturmaya oynama" baskısını geri getirirdi). Blok artık ölçülmüş tabanı
  taşıyor: `overall_v2: "taban 49/64"`, kategoriler aynı mantıkla. Eski
  hedeflerin hepsi eski puanlayıcıya kalibreydi (`technical ">=8/10"` iken
  şimdi 5/10, `longform ">=3/4"` iken 0/4), o yüzden hepsi düzeltildi.
  Anahtar adları korundu (gereksiz kırılma yok). Bloğu hiçbir Python kodu
  okumuyor; bu bir insan yorumudur.

---

## A7 — `AUTONOMY_CHARTER_PROPOSAL.md` kisisel e-posta iceriyor (COMMIT EDILMEDI)

`automation/AUTONOMY_CHARTER_PROPOSAL.md:154` senin kisisel e-posta adresini
duz metin olarak tasiyor (`ahmet...@gmail.com`, satir 156'da da bir ikinci
hesap adi). GitHub yedegi kartinda bu dosya "otomasyon kayitlari" grubunda
listelenmisti; **bilerek commit ETMEDIM.**

Gerekce: private depoda felaket degil, ama bu hafta `.env` gecmisini kazimak
zorunda kaldik ve maliyeti gorduk. Kisisel veriyi gecmise gommek geri
alinmasi pahali bir istir; depo ileride public yapilirsa ya da erisim
paylasilirsa veri onbellekte kalir.

**Secenekler:** (a) oldugu gibi commit et (private depo yeterli koruma sayilir),
(b) e-postayi `<AHMET_EPOSTA>` gibi bir yer tutucuyla degistirip commit et,
(c) dosyayi hic izleme.

---

## A8 — Depo boyutu 618 MB: `venv/` gecmiste (BU KARTTA COZULMEDI)

Olculdu: `size-pack 618.83 MiB`, ve gecmiste **69.184 adet `venv/` nesnesi**
var -- boyutun tamami pratikte bu. Kart bunu bilinen borc olarak isaretledi
ve cozmemeyi soyledi; uymadim demeyeyim, uydum: **dokunulmadi.**

Ikinci bir gecmis yeniden yazma riskli: `.env` kazimasi zaten tum commit
hash'lerini degistirdi ve `AUTONOMY_LOG.md` (27) ile `BLACKBOX.jsonl` (10)
icindeki git referanslarini bayatlatti. Ayni bedeli ikinci kez odemek,
ustelik push'tan sonra yapmak, cok daha pahali olur.

**Onemli sira notu:** yapilacaksa **ilk push'tan ONCE** yapilmali. Push
edildikten sonra gecmis yeniden yazmak, klonlamis herkesi bozar.

**Secenekler:** (a) simdilik 618 MB ile yasa (private depo, boyut sinirinin
altinda), (b) push'tan once `git filter-repo --path venv --invert-paths`
ile temizle (yedek zaten var: `jarvis-agent-auto-BACKUP-20260831-180827.bundle`).

---

## A9 — Kucuk kalanlar (uc madde)

1. **`automation/_ss_raw/`, `_model_bench_raw.json`, `_whisper_bench_raw.json`**
   commit edilmedi (kart boyle dedi). `.gitignore`'a eklenmesini **oneriyorum**,
   eklemedim -- yoksa her `git status`'ta gorunmeye devam ederler.
2. **`automation/codex_denetim_2026-08-27_185006.txt`** hicbir grupta adi
   gecmiyordu. Bir denetim transkripti; tarihsel deger tasiyor ama karar
   bana ait degil, birakildi.
3. **`.gitattributes`'taki `merge=graphify` satiri artik olu** --
   `graphify-out/` `01e1bf04e`'de gitignore'a girdi, yani surucunun yonettigi
   dosya hic izlenmiyor. Zararsiz, oldugu gibi commit edildi.

---

## A12 — ruff taban cizgisi 293 -> 300 (kapsam buyudu, kalite dusmedi)

`.gitignore`'dan `agent/` kaldirilinca (borc maddesi 3) ruff o dizini
**taramaya basladi** -- ruff varsayilan olarak `.gitignore`'a uyar, yani
`agent/` yillardir hic linte girmemisti.

**7 yeni bulgu, hepsi onceden var:**

```
agent/jarvis_agent.py:29    F401  JARVIS_MODEL imported but unused
agent/jarvis_agent.py:265   F541  f-string without placeholders
agent/local_agent.py:7      F401  time imported but unused
agent/local_agent.py:421    F841  local variable 'e' never used
agent/local_agent.py:542    F541  f-string without placeholders
agent/local_agent.py:545    F541  f-string without placeholders
agent/local_agent_memory.py:109  E402  import not at top of file
```

Dogrulandi: `import time` bu oturumdan ONCE de kullanilmiyordu
(`2be8863b2~1`'de `time.` kullanimi sifir). Yani hicbiri bu oturumda
uretilmedi. CLAUDE.md 3 geregi dokunulmadi: "onceden var olan dead code'a
dokunma -- gor, soyle, silme."

**Sayi neden onemli:** kapi kurali "ruff artamaz" diyor. Bu artis bir
gerileme DEGIL, olcum kapsaminin genislemesi. Ama sayiyi sessizce kabul
etmek, kuralin anlamini asindirir -- o yuzden burada yaziyor.

**Gerekli olan:** taban cizgisi **300** olarak mi guncellensin, yoksa 7
bulgu duzeltilip **293**'e mi donulsun? Altisi `--fix` ile otomatik
duzelebilir; `E402` elle bakilmali.

**Duzeltme notu:** `d464b7a5f` commit mesaji "ruff check . -> 293,
unchanged" diyor. **Bu yanlis.** Sayiyi commit'ten sonra gordum. Gecmis
yeniden yazilmadigi icin mesaj oldugu gibi duruyor; dogrusu burada ve bir
sonraki commit mesajinda kayitli.

---

## A11 — Kalite takimi kosular arasi OYNAK (sahte regresyon riski)

**Olculdu** (2026-09-01, llama3.1, `temperature=0.2`, ayni vakalar):
grounding kategorisi uc kosuda **5/5, 5/5, 4/5** verdi. Diger kategoriler
sabit kaldi ama grounding oynuyor -- cunku "uydurma mi, itiraf mi" sinirinda
modelin kelime secimi degisiyor.

**Sonucu:** takim su haliyle **sahte regresyon uretebilir.** Uc hafta sonra
biri "63/64 idi, 62/64 oldu, bir sey bozuldu" diyip sebebini kodda arayabilir
-- oysa sebep kodda degil, orneklemde olabilir. Bu not tam olarak o aramanin
onune gecmek icin var.

**Cozulmedi, bilerek.** Uc secenek gorunuyor:

(a) **N kosu ortalamasi** -- her kosu N kez, ortalama raporlanir. Dogru ama
    sureyi N katina cikarir (su an 64 vaka ~3 dakika).
(b) **Tolerans bandi** -- taban +-1 vaka regresyon sayilmaz. Ucuz ama gercek
    bir tek-vaka gerilemesini de gizler.
(c) **Yalniz oynak kategoriyi tekrarla** -- grounding N kez, digerleri 1 kez.
    Maliyeti dusuk, ama hangi kategorinin oynak oldugunu once olcmek gerekir.

**Simdilik ne yapiliyor:** rapor basligina "tek kosu hukum degildir" uyarisi
konuldu ve olculen 5/5-5/5-4/5 dizisi oraya yazildi. Yani takim kullanilabilir,
ama sonucu okuyan kisi sinirini goruyor.

**EK ÖLÇÜM (2026-09-04) — kararı hâlâ değiştirmiyor ama sayılar geldi.**
Tam takım (64 vaka) `llama3.1` ile canlı koşturuldu ve **kayıtlı** 09-01
cevaplarının aynı puanlayıcıyla puanlanmasıyla karşılaştırıldı. Model aynı,
puanlayıcı aynı, değişen yalnız koşu:

| | kayıtlı | canlı | oynama |
|---|---|---|---|
| Toplam | 49/64 | 48/64 | ±1 (%1,6) |
| Düşen vakaların kimliği | 15 vaka | 16 vaka | **3 vaka yer değiştirdi (%4,7)** |
| Neden dağılımı | sızıntı 6 / tekrar 3 / kesilme 7 / uydurma 5 | 8 / 5 / 5 / 4 | **bir nedende ±2** |

Yani **toplam sanıldığı kadar oynak değil; oynayan şey neden dağılımı ve
hangi vakanın düştüğü.** Bu, (b) tolerans bandını toplam için makul,
kategori/neden iddiaları için yetersiz kılıyor — 4-5 vakalık kategorilerde
bir vaka %20-25 demek. Ayrıntı: `automation/MODEL_KIYASI_2026-09-04.md` §6.

**Gerekli olan:** (a)/(b)/(c) arasinda bir karar -- ya da "simdilik boyle
kalsin".

---

## A10 — Bu depo bir git WORKTREE (yedegi etkiler)

`.git` bir dizin degil, dosya: asil git dizini
`C:/Users/Ahmedov/Desktop/Jarvis/jarvis/.git/worktrees/jarvis-agent-auto`
altinda. Yani **nesneler bu klasorde degil, ana depoda yasiyor.**

Pratik sonucu: bu dizinden push etmek calisir ve tum dallari gonderir
(refler paylasilir), ama "bu klasoru kopyalarsam yedegim olur" YANLIS.
`git count-objects` de bir uyari veriyor:
*"garbage found: .../worktrees/jarvis-agent-auto/refs"*.

**Onerim:** push kurulduktan sonra ana depo (`Jarvis/jarvis`) icin de ayni
remote dusunulmeli; ayrica o "garbage" uyarisi ayrica bakilmali. Karar senin.

---

## A6 — `HUMAN_NEEDED.md` ile `roadmap_state.json` hala celisiyor (YENI)

A4 uygulandiktan sonra CANLI blokta gorundu: model artik **ayni prompt icinde
iki celiskili olgu** goruyor.

```
### Insan Onayi Gereken Isler (HUMAN_NEEDED)
  - [ ] [2026-06-24] [E1-S4] Live Telegram proactive smoke test...   <- BEKLIYOR

### Yol Haritasi Durumu
  - FAZ-3-E1 [in_progress] ...
      e1_s4: DONE                                                    <- TAMAM
```

Bu, `CLAUDE.md` 12'de zaten kayitli olan celiskinin ta kendisi
(`HUMAN_NEEDED.md` "Pending" derken `roadmap_state.json` "DONE" diyor).
Kod tarafinda cozulemez: iki dosya da mesru kaynak, hangisinin guncel oldugu
bir PROJE GERCEGI karari.

Ek olarak `memory/` hafiza kaydi `project_e1_s4_done.md` de DONE diyor
(Ahmet telefon onayi, 2026-06-27) -- yani iki kaynak DONE, biri Pending.

**Onerim:** `automation/HUMAN_NEEDED.md`'deki E1-S4 maddesi `- [x]` yapilsin
ya da Resolved bolumune tasinsin. Kendi basima yapmadim: proje gercegi.

**Not:** Sablon yer tutucusu (`- [ ] [YYYY-MM-DD] [TASK-ID] ...`) koddan
filtrelendi -- o bir veri karari degil, acik bir hataydi.

---

## A5 — `analyze_file` de ulasilamiyor (YENI)

`_detect_tool()` yalnız 6 araca yol açıyor; `analyze_file` ajanın araç
sözlüğünde ama hiçbir tetikleyiciye bağlı değil — `run_python_code` ile aynı
durumda. `exec`/`eval` içermediği için A3 turunda **kapsam dışı bırakıldı**.

**Seçenekler:** (a) sözlükten çıkar (ölü yüzey azalır), (b) bir
`TOOL_TRIGGERS["analyze_file"]` girdisi ekle (araç kullanılabilir hâle gelir).
`tests/test_local_agent_tool_surface.py::test_no_loaded_tool_is_unreachable`
bunu bilinen istisna olarak tutuyor; karar verilince liste güncellenir.

---

## A1 — Turkish-Gemma-9b-T1 indirilsin mi?

**Karar:** Model indirme insan kapısıdır (§9 + kartın açık talimatı).

`docs/HARDWARE_AND_LOCAL_LLM_RESEARCH.md` §4'e göre 1450 soruluk insan
değerlendirmesinde **%68,65** ile Qwen3-32B'yi (%67,20) geçmiş; Q4 ~5,5 GB,
8 GB'a sığıyor. Zayıflığı: Gemma 2 tabanlı, bağlam **8K**, araç kullanımı
zayıf — JARVIS'in prompt'u (persona + proje durumu + hafıza) 8K'yı zorlayabilir.

**Durum:** İndirilmedi. Kıyas yalnız kurulu üç modelle yapıldı.
**Gerekli olan:** "indir" / "indirme" kararı.

---

## A2 — `runtime_profiles.json` değişikliği (ADIM C çıktısı)

**Karar:** Aktif profildeki `local_main` değişikliği yalnız Ahmet'in.

Kıyas tablosu `automation/MODEL_KIYASI_0901.md`. Kazanan ilan edilmedi,
dosyaya dokunulmadı. Profilin kendi notu zaten *"local_main icin Qwen'e
gecis HALA benchmark bekliyor"* diyor — benchmark artık var, karar yok.

**Gerekli olan:** Tablodaki veriye bakıp `local_main` kalsın mı, değişsin mi.

---

## A3 — SkillSpector bulguları (4 madde)

`automation/SKILLSPECTOR_RAPORU.md` sonundaki karar listesi. Özet:

1. `run_python_code` aracı (`exec()`, `tools.py:482`) kalsın mı?
2. `auto_updater.py` canlı mı, ölü kod mu? (park edilmiş AUTO cephesi olabilir)
3. Kurulu skill'ler güncellendiğinde yeniden taransın mı?
4. `agents/retrieval_priority.py:9` "Memory Manipulation" bulgusu elle bakılsın.

**Hiçbiri düzeltilmedi** — kart "sınıflandır, düzeltme" diyordu.

---

## A4 — `_load_project_context()` eskimiş durum bloğu

**Sorun:** `agent/local_agent.py` içinde proje durumu sabit yazılı ve üç satır
`roadmap_state.json`'la çelişiyor (E1-S4 DONE ama kodda BEKLIYOR; E1-S5
APPROVED ama kodda "henuz kod yok"; T1-S2 Resolved ama kodda BEKLIYOR).
Model bu tabloyu her turda görüyor ve canlı testte *"tasarım aşamasındayız"*
dedi — halüsinasyon değil, eskimiş veriyi sadakatle tekrar etmesi.

**Neden kendi başıma yapmadım:** `tests/test_local_agent_grounding.py` içindeki
`test_load_project_context_includes_known_state` bu eskimiş dizeleri
(`"BEKLIYOR"`, `"Proaktif bildirimler: CANLI DEGIL"`) **sabitliyor**. Düzeltmek
o testi değiştirmeyi gerektirir → §13.1 sözleşme kilidi → sorulur.

**Önerim:**
1. Durum `roadmap_state.json`'dan okunsun (`steps[].status` + `evidence.verdict`),
   sabit metin kalmasın. Dosya yoksa/bozuksa blok **boş** dönsün — uydurma
   durum yerine hiç durum yeğdir (mevcut fail-safe deseni korunur).
2. `JARVIS_PROACTIVE_ENABLED=0` iddiası **doğru**, kaldırılmasın.
3. Test, sabit dizeler yerine "blok `roadmap_state.json`'daki verdict'lerle
   tutarlı" iddiasına çevrilsin.

**Ayrıca bulunan test kusuru (ADIM 1'de raporlanmıştı):**
`_call_real_loader()` gerçek metodu bir **replikayla** değiştiriyor
(`patch.object(LocalJarvisAgent, "_load_project_context", patched_loader)`).
176/186/203/213 satırlarındaki dört test gerçek fonksiyonu değil, testin
içine yazılmış kopyayı ölçüyor. Replika, gerçekteki `T1_S2_FAIL_LOG.md`
okumasını ve "Onemli Kural" bloğunu içermiyor — yani zaten sapmış.

**Gerekli olan:** Yukarıdaki 3 maddeye onay; sonra test-first uygulanır.
