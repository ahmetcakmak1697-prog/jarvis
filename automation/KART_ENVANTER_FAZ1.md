# KART — JARVIS Envanteri (Faz 1: HARİTA)

**Durum:** Açık · **Karar:** Ahmet, 2026-09-05
**Bu kart hiçbir dosyayı taşımaz, silmez, yeniden yazmaz.** Tek ürünü bir harita.

---

## Neden bu kart var

Ahmet'in şikayeti: *"sen daha JARVIS'te ne entegre ne değil bilmiyorsun,
çünkü her şey darmadağın."*

**Şikayet doğru ve kanıtı taze.** 2026-09-05'te danışman, Ahmet'e "çok
sağlayıcılı dış model mimarisi kuralım" dedi. Sonra grafiğe baktı ve şunları
buldu — hepsi aylardır repoda, testleriyle:

`agents/cost_ledger.py` · `agents/api_executor.py` · `agents/provider_profiles.py`
`agents/local_first_router.py` · `agents/api_budget_gate.py`

Yani mimari kurulmuş, kimse bilmiyor. Bu bir düzen sorunu değil, **bir
görünürlük sorunu.** Faz 1 görünürlüğü kurar. Ne taşınacaksa Faz 2'de,
haritaya bakarak ve Ahmet'in onayıyla taşınır.

> **Ahmet'in gönderdiği görsel bu kartın gerekçesidir:** sağdaki "mühendislik"
> resminde borular düzgün *çünkü döşeyen her borunun nereye gittiğini
> biliyordu*. Önce bilgi, sonra düzen. Ters sırası vibe coding'dir.

---

## Faz 1'in tek ürünü

**`docs/JARVIS_ENVANTER.md`** — makineyle türetilmiş, elle yazılmamış.

### Zorunlu kural: ÖLÇ, TAHMİN ETME

Bu belgenin her satırı **hesaplanmış** olmalı. "Şuna baktım, kullanılmıyor
gibi" kabul edilmez. Erişilebilirlik import/çağrı grafiğinden **hesaplanır**;
`graphify-out/graph.json` (5495 düğüm) zaten var, önce `graphify update .`
ile tazele ve **onu kaynak olarak kullan.** Grep ile göz kararı envanter
çıkarmak bu kartın reddettiği şeydir.

Üretimi tekrarlanabilir yap: envanteri üreten betik `scripts/` altına
yazılırsa altı ay sonra tekrar koşturulabilir ve harita eskimez. Bu, kartın
tercih ettiği yoldur — ama betik yazmak belgeyi geciktiriyorsa önce belgeyi
çıkar, betiği ikinci commit'e bırak.

### Belgede olması gerekenler

**1. Giriş noktaları (entry points).** Bu sistemi çalıştıran her şey:
`main.py`, `jarvis_brain.py`, `agent/local_agent.py`, `tools/telegram_agent.py`,
`gui.py`, `auto_runner.py` (**PARK EDİLMİŞ** — §9, çalıştırma), `eval/` koşucuları,
`scripts/` altındakiler. Her biri için tek cümle: **bunu ne çalıştırır?**

**2. Her modülün sınıfı.** Repodaki her `.py` dosyası şu beş kovadan birine
girecek, **kanıtıyla** (hangi giriş noktasından kaç adımda erişiliyor):

| Sınıf | Anlamı |
|---|---|
| **CANLI** | Bir giriş noktasından erişilebiliyor |
| **YETİM** | Hiçbir giriş noktasından erişilemiyor, testi de yok |
| **YALNIZ-TEST** | Sadece testler çağırıyor |
| **ÖRNEK/ŞABLON** | `.example` yapılandırma bekliyor, gerçek dosya yok (bkz. `config/api_providers.example.json`) |
| **BELGE-VAR-KOD-YOK** | Belgede anlatılıyor ama kod yok |

**3. Ana akışın kablolaması.** "Hey JARVIS" dendiğinde ses hangi modülleri
hangi sırayla dolaşıyor — mikrofon → STT → sınıflandırma → model → TTS.
Her okun yanında **dosya:satır**. Bu, Ahmet'in "ne nereye bağlı" sorusunun
doğrudan cevabıdır.

**4. Dış model hattının gerçek durumu.** Yukarıdaki beş modül ne kadar
bağlı? `LocalFirstRouter` çağrılıyor mu, yoksa yazılıp rafta mı? `CostLedger`
kim tarafından besleniyor? `.example` yapılandırmalar gerçek dosyaya
kopyalanmış mı? **Bu bölüm Faz 2'nin girdisidir**, özenle yaz.

**5. Çelişki listesi.** Belgenin bir şey, kodun başka şey söylediği yerler.
`CLAUDE.md` §12 bu türden üç çelişkiyi zaten kaydetmiş (Letta, HA/Wyoming,
auto_runner) — desen tanıdık, yenilerini ara.

**6. Çöp adayları — LİSTE, SİLME DEĞİL.** YETİM çıkan her dosya için: adı,
boyutu, son commit tarihi, neden yetim olduğu. **§3 nettir: "önceden var olan
dead code'a dokunma (gör, söyle, silme)."** Bu bölüm Ahmet'in okuyup karar
vereceği bir listedir; kartın kendisi hiçbir şey silmez.

---

## Yasaklar — bu kartın omurgası

1. **HİÇBİR DOSYA TAŞINMAZ, SİLİNMEZ, YENİDEN ADLANDIRILMAZ.** Faz 1 salt-okunur
   bir keşiftir. Tek yazma izni: `docs/JARVIS_ENVANTER.md` ve (isteğe bağlı)
   onu üreten `scripts/` betiği.
2. **Hiçbir modül refactor edilmez.** §2/§3: *"No rewrite; v5 korunur"*,
   *"Bozuk olmayanı refactor etme."* Kötü kod görürsen **yaz**, düzeltme.
3. **1706 test yeşil kalır.** Bu kart koda dokunmadığı için sayı değişmemeli.
   Değişirse bir şeyi yanlış yapmışsındır.
4. **`.env` okunmaz, yazılmaz, loglanmaz** (§9). Hangi anahtarların *tanımlı
   olması gerektiğini* yaz, değerlerini asla.
5. **Park edilmiş cepheler açılmaz** (§9). `auto_runner.py`, orchestrator,
   scheduler, Telegram auto-send: envanterde **park edilmiş** olarak
   işaretlenir, çalıştırılmaz, canlandırılmaz.
6. **Uydurma yok.** Bir şeyin ne yaptığından emin değilsen `[EMİN DEĞİLİM]`
   yaz. Yanlış bir harita, haritasızlıktan kötüdür.

## Kalite çıtası

Ahmet'in isteği: *"20 senelik yazılımcı gibi bir iş."* Somut karşılığı:

- Envanterdeki **her iddia doğrulanabilir** — dosya:satır ya da hesaplanmış
  erişilebilirlik zinciri.
- Belge **altı ay sonra da okunabilir**: bugünkü commit hash'ine, bugünkü
  ruh haline bağlı cümle yok (§10'un dersi — sabit olgu belgeye yazılmaz).
- **Ne bulunduğu kadar ne BULUNAMADIĞI da yazılır.** Erişilebilirliği
  hesaplanamayan modül varsa (dinamik import, `getattr` ile çağrı) o
  ayrı bir başlıkta listelenir — sessizce CANLI sayılmaz.
- Uzunluk hedefi yok; **eksiksizlik** hedefi var. Repodaki her `.py`
  sınıflandırılmış olmalı, atlanan dosya kalmamalı.

## Bitti sayılma ölçütü

- `docs/JARVIS_ENVANTER.md` var; repodaki **her** `.py` beş sınıftan birinde,
  kanıtıyla.
- Ana ses akışının kablolaması dosya:satır ile yazılı.
- Dış model hattının gerçek durumu ayrı bölümde.
- Çöp adayları **listelenmiş, silinmemiş**.
- `graphify update .` koşuldu, grafik güncel.
- `pytest tests -q` **1706** (iki sırada), `ruff check .` ≤ 293 — koda
  dokunulmadığı için ikisi de değişmemeli.
- Commit: yalnız isimli dosya. Push yok. **Bittiğinde dur — Faz 2'ye
  geçme, Ahmet haritayı okuyacak.**
