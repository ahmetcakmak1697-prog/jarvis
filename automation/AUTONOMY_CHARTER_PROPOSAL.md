# OTONOMİ SÖZLEŞMESİ — ÖNERİ (imzalanmadı, yürürlükte DEĞİL)

**Tarih:** 2026-08-20 gece
**Durum:** 🔴 TASLAK — Ahmet imzalayana kadar hiçbir maddesi uygulanmaz.
**İmza yeri:** en altta, §9.

Bu belge, Ahmet'in 2026-08-20 gecesi sözlü olarak istediği "PC açık olduğu
sürece JARVIS kodlanmaya devam etsin" yapısını yazıya döker. Yazıya dökülmesinin
sebebi şu: istenen yapı **`CLAUDE.md` §9'un iki maddesini açıkça deliyor.**
Anayasa sessizce değiştirilmez — değişiklik burada adı konarak yapılır ki altı
ay sonra "bu neden açıldı" sorusunun cevabı olsun.

---

## 1. DELİNEN İKİ KURAL (Ahmet'in açık talebi)

### 1.1 Otomatik sıradaki-işe-geçiş
`CLAUDE.md` §9: *"Otomatik sıradaki-işe-geçiş yok — her adım tamamlandığında
durulur, bir sonraki adım insan onayı bekler."*

**Ahmet'in kararı — SINIRLI ZİNCİR** (20.08 sözlü, 23.08 seçimle kesinleşti):
> *"pass gelirse beni beklemeden devam"* — ama **bağımsız maddeler için.**

- Codex PASS verdiğinde, önceden onaylanmış **BAĞIMSIZ** bir sonraki maddeye
  insan onayı beklemeden geçilir.
- **Bağımlı madde** (`depends_on` zinciri henüz onaylanmamış bir maddeye
  dayanıyorsa) **BAŞLAMAZ** — durur, Ahmet'in onayını bekler.
- Her madde ayrı commit, **çalışma dalında**, push YOK.

Gerekçe: "tam sürekli" seçeneğinde yanlış bir madde üstüne saatlerce iş
birikebilir. Bağımlılık kapısı bu birikmeyi keser: hatanın yayılma mesafesi
bir maddeyle sınırlı kalır.

### 1.2 Auto-fix retry
`CLAUDE.md` §9: *"Auto-fix retry **NOT APPROVED** — bir kontrol BLOCKER/CONCERN
verirse otomatik düzeltip tekrar denenmez, Ahmet'e gider."*

**Ahmet'in kararı (20.08):** *"fail verirse düzeltene kadar 3 kere deneyeceksin"*
→ En fazla **3 deneme**, sonra sert duruş.

**Claude'un kayda geçen itirazı:** hatayı yazan da düzelten de aynı taraf.
Üç denemede kod gitgide dolambaçlı hale gelip review'ı yüzeysel geçebilir.
Bu yüzden §4'teki sınırlar sözleşmenin ayrılmaz parçasıdır; onlar olmadan bu
madde geçerli değildir.

### 1.3 Delinmeyen kurallar (aynen yürürlükte)
Aşağıdakiler **tartışmaya kapalıdır** ve bu sözleşme onları değiştirmez:

- `git push` **yok** — push yalnız Ahmet'in elinden.
- `git add -A` **yok** — yalnız isimli dosya eklenir.
- `main` dalına commit **yok** — yalnız çalışma dalı.
- `.env` / secret dosyaları **okunmaz, yazılmaz, loglanmaz**.
- `--dangerously-*` bayrakları **kalıcı yasak**.
- Donanım (klima, mikrofon, hoparlör, ESP32), satın alma, dış servise veri
  gönderme → **her zaman dur.**
- Roadmap dışına çıkma yok; yeni teknoloji/mimari kararı Claude tek başına
  vermez.

---

## 2. ÖN KOŞUL — BU BİTMEDEN DÖNGÜ BAŞLAMAZ

**Roadmap'in tek doğruluk kaynağı yok.**
`roadmap_state.json` kendini "TEK DOĞRULUK KAYNAĞI" ilan ediyor ama en son
**2026-06-18**'de güncellenmiş. `CLAUDE.md` §12'de üç çelişki kayıtlı:
Letta hem "reddedildi" hem "adopt adayı"; `HUMAN_NEEDED.md` bir maddeyi
"Pending" derken `roadmap_state.json` aynı maddeyi "DONE" gösteriyor.

**Çelişkili roadmap üstüne otomatik görev seçici kurulursa, gece boyunca
kendinden emin biçimde yanlış işi yapar.** Gözetimsiz bir sistemde bu, hiç
çalışmamasından kötüdür.

**Ahmet'in kararı (20.08):** Claude önce tam bir denetim raporu çıkarır
(çelişkiler, tamamlanmış-ama-işaretlenmemiş maddeler, bug/mantık hataları),
**kararları Ahmet verir**, Claude tek kaynağa çevirir.
→ **✅ YAPILDI:** `automation/ROADMAP_AUDIT.md` (23.08). Ön koşulun *rapor*
kısmı kapandı; ama raporun **kendisi 6 karar** üretti (§8) ve döngünün gerçek
engeli artık o kararlar. Özellikle: **`roadmap_state.json`'da `pending` adım
YOK** — 13 done, 1 imza bekliyor. Döngü bugün silahlansa **ilk turda durur**,
çünkü seçecek iş bulamaz. FAZ-4+ adımları yazılmadan otonomi anlamsız.

---

## 3. DÖNGÜ

```
  [1] Görev seç        onaylı tek-kaynak roadmap'ten sıradaki uygun madde
       |
  [2] İnsan kapısı?    ses / donanım / gizli anahtar / dış servis /
       |               park edilmiş cephe / mimari sapma  -> DUR + BİLDİRİM
       |
  [3] Kodla            küçük patch, test-first (CLAUDE.md §4), cerrahi (§3)
       |
  [4] Kendi kapım      py_compile + testler + git status temiz + import smoke
       |               (bu kapı geçilmeden Codex'e gidilmez)
       |
  [5] Codex review     codex review --uncommitted   (§5'teki review sözleşmesi)
       |
  [6] Sonuç
       |-- PASS ------> isimli dosyalarla commit (çalışma dalı)
       |                BLACKBOX'a append -> [1] sıradaki madde
       |
       |-- CONCERN/BLOCKER
                       aynı bulguya odaklı düzeltme -> [4]
                       en fazla 3 deneme
                       3. denemede hâlâ FAIL -> DUR + BİLDİRİM
```

Her adım `automation/BLACKBOX.jsonl`'a **append-only** yazılır (mevcut disiplin
korunur; geçmiş satır silinmez, yeniden yazılmaz).

---

## 4. AUTO-FIX RETRY'IN SINIRLARI (1.2'nin ayrılmaz koşulu)

1. Her deneme **yalnızca Codex'in işaret ettiği bulguya** dokunur. İlgisiz kod
   elden geçirilmez, "bu arada şunu da iyileştireyim" yok.
2. Her deneme BLACKBOX'a **ayrı event** olarak yazılır: kaçıncı deneme, hangi
   bulgu, ne değişti, diff hash.
3. Üç deneme **aynı bulgu** içindir. Düzeltme yeni bir bulgu doğurursa sayaç
   sıfırlanmaz — o madde toplamda 3 denemeyi aşamaz.
4. 3. denemeden sonra: **sert duruş**, otomatik geçiş yok, bildirim gider.
5. Deneme sırasında test **silinemez veya gevşetilemez**. Testi geçirmek için
   testi değiştirmek = anında duruş.
6. Bir düzeltme, önceki bir maddenin commit'ini geri almayı gerektiriyorsa →
   **dur**, Ahmet karar verir.

---

## 5. CODEX REVIEW SÖZLEŞMESİ — ✅ ONAYLANDI (26.08)

> Ahmet: *"görevleri öğretme olayını yaparken bana sor, taraflı yorumlar
> yapmasın, gerçekten açık bulacak, baş mühendis gibi görev yapacak, asla
> acımayacak ki iş kusursuz olsun."*

Metnin kendisi ayrı dosyada duruyor: **`automation/CODEX_REVIEW_TALIMATI.md`**
(2086 bayt, sha256 `7e25f8fc44d663bb5ddb26032abd5047fca746ce0ec7df7fdd332f96b5d3fead`).

**Neden burada kopyası yok:** aynı metnin iki yerde durması kaçınılmaz olarak
birbirinden ayrışır ve "hangisi onaylandı?" sorusu cevapsız kalır. Onaylanan
şey yukarıdaki hash'tir; dosya değişirse hash tutmaz ve yeni onay gerekir.

**Ahmet'in onayı (2026-08-26, sözlü):** *"okey codex in görev metnini
onaylıyorum"*. Metin o tarihten beri değiştirilmedi.

Çalıştıran: `scripts/codex_denetle.ps1` (talimatı stdin'den besler,
verdict'i `scripts/codex_verdict.ps1` çözer).

---

## 6. BİLDİRİM

**Ahmet'in kararı (23.08, kesin):** Telegram yok, Claude hesabı yok →
**düz e-posta**, hedef: `ahmetcakmak1697@gmail.com`

**Gönderen taraf AYRI BİR ÇÖP HESAP olacak** (örn. `jarvis.bildirim@gmail.com`),
Ahmet'in kendi hesabı değil. Gerekçe: Gmail Uygulama Şifresi "sadece gönder"
yetkisi değildir — o posta kutusuna **tam SMTP/IMAP erişimi** verir. Sızarsa
Ahmet'in gerçek yazışmaları okunabilir. Boş bir hesapta ele geçen şey bomboş
bir kutudur.

**⏸ DURUM: Ahmet henüz hesabı açmadı.** Bu, bildirim hattının tek engeli.

**Ne zaman gider:**
| Olay | Bildirim |
|---|---|
| 3 denemede çözülemeyen FAIL | ✅ anında |
| İnsan kapısı (ses seçimi, donanım, gizli anahtar, mimari karar) | ✅ anında |
| Kural ihlali riski / beklenmedik duruş | ✅ anında |
| Bir madde PASS aldı | ❌ hayır (gürültü olur) |
| Günlük özet (kaç madde bitti, nerede duruldu) | ✅ günde bir |

**Duruş bildiriminin içeriği (Ahmet'in şartı: "neden ve ne zaman durduğumu
bileyim ki ne zaman PC'ye gelmem gerektiğini bileyim"):**
- duruş zamanı (tarih + saat)
- hangi roadmap maddesi
- duruş sebebi: FAIL / insan kapısı / kural
- FAIL ise: Codex'in son bulgusu, 3 denemede ne denendi
- PC'ye geldiğinde ne yapması gerektiği, tek cümle
- o ana kadar biten madde sayısı

**🔑 AHMET'TEN GEREKEN TEK ŞEY:**
Gmail **Uygulama Şifresi** (App Password, 16 hane). Bunun için hesapta
2 adımlı doğrulama açık olmalı. **Ahmet oluşturur ve kendisi yerleştirir;
Claude bu şifreyi görmez, girmez, loglamaz, commit etmez.** Şifre
`.gitignore`'a alınmış yerel bir dosyada durur ve yalnızca gönderim anında
okunur.

### ⚠️ 6.1 ÜÇÜNCÜ KURAL ETKİLEŞİMİ — bunu da imzalarken bil
`CLAUDE.md` §9: *".env / secret dosyalarına dokunulmaz, **okunmaz**, loglanmaz."*
E-posta gönderebilmek için bildirim betiğinin o şifreyi **okuması** gerekiyor.
Bu, kuralın dar bir istisnasıdır ve şöyle sınırlandırılır:

- İstisna **tek bir dosya** içindir: `.env.notify` (`.gitignore`'daki `.env.*`
  kalıbı zaten kapsıyor — doğrulandı).
- O dosyada **yalnızca** SMTP kullanıcı adı ve uygulama şifresi bulunur.
  Başka hiçbir sır oraya konmaz.
- Yalnızca bildirim betiği, yalnızca gönderim anında okur.
- Değer **hiçbir yere** yazdırılmaz: log yok, BLACKBOX yok, hata mesajı yok,
  konuşma çıktısı yok. Şifre eksikse betik "şifre yok" der, içeriği göstermez.
- Diğer tüm `.env*` dosyaları **eskisi gibi tamamen dokunulmazdır.**

Bu istisnayı istemiyorsan e-posta bildirimi kurulamaz; o durumda alternatif
kanalı yeniden konuşmamız gerekir.

---

## 7. HANGİ MADDELER OTOMATİK, HANGİLERİ DEĞİL

**Otomatik ilerler:** saf kod işi — mevcut modüle fonksiyon, test yazımı,
refactor değil düzeltme, dokümantasyon, şema/veri doğrulama, CLI aracı.

**Her zaman durur (Ahmet'in "ses gibi önemli işler" dediği sınıf — liste
genişletilebilir):**
- ses: TTS/STT motoru seçimi, model seçimi, uyandırma kelimesi, hoparlör/mikrofon
- gizli anahtar, hesap, ödeme, abonelik
- donanım: ESP32, klima, Home Assistant, herhangi bir fiziksel cihaz
- dış servise veri gönderme (dışarı çıkan her şey)
- yeni bağımlılık / yeni açık kaynak repo adopt etme kararı
- mimari sapma: v5.9 cascade, routing, hafıza sınıflandırması
- park edilmiş cepheler: Telegram auto-send, scheduler, orchestrator'ın
  kendisinden başka her şey
- `roadmap_state.json`'ın kendisini değiştirmek

---

## 8. ADOPT-OVER-BUILD

Ahmet'in 20.08 talimatı: *"hazır yapılmış GitHub repoları varsa onları entegre
edip geçelim, 0'dan yazıp gereksiz iş yükü oluşturmayalım."*

Bu, `CLAUDE.md`'nin "Claude Code kendi başına GitHub/web taraması YAPMAZ"
kuralına **Ahmet'in verdiği açık istisnadır**. Araştırma onaylandı.

Ama adopt kararının kendisi **§7 gereği insan kapısıdır**: Claude araştırır,
karşılaştırır, gerekçesiyle sunar; **hangi repoyu adopt edeceğimize Ahmet
karar verir.** Claude tek başına bağımlılık eklemez.

---

## 8.5 K2 CEVABI — orchestrator neden parklandı? (Claude araştırdı, 26.08)

Bu, sözleşmenin kendi şartıydı: *"parklanma sebebi öğrenilmeden yeniden
silahlandırılmamalı."* Ahmet'e soru olarak gitmeden önce git geçmişi tarandı.

**Bulgular:**

| Tarih | Olay |
|---|---|
| 2026-06-21 | `scripts/orchestrator.py` + `jarvis_auto_task.ps1` son kez değişti (`9097b8ba8` — *"Fail closed on missing verifier contract path"*) |
| 2026-06-24 | Commit: **`c455fba75` — *"make autonomous roadmap execution default"*** |
| 2026-06-27/28 | İlgi E1-S6'ya (proactive runner) kaydı |
| 2026-07-04+ | Tamamen J0 ses hattı + BLACKBOX-0'a geçildi |
| 2026-08-06 | `CLAUDE.md` yazıldı; AUTO/orchestrator/scheduler *"hiçbir isimle, hiçbir gerekçeyle yeniden açılmaz"* diye işaretlendi |

**Yorum:** Cephe bir arıza sonrası kapatılmamış görünüyor — tam tersine
06-24'te otonom çalışma **varsayılan yapılmış**. Sonrasında dikkat başka
cephelere kaymış ve altı hafta sonra `CLAUDE.md` bunu geriye dönük olarak
"park edilmiş" ilan etmiş.

**[EMIN DEGILIM]** Belgelenmiş bir parklanma kararı **bulunamadı**. En güçlü
hipotez: öncelik kayması. Ama `CLAUDE.md`'deki ifadenin sertliği basit bir
öncelik kaymasına göre fazla keskin — arkasında yazılmamış bir şey olabilir.
**Ahmet hatırlıyorsa söylemeli.**

**Dolaylı ipucu:** maker tarafı (OpenCode/DeepSeek) sancılıymış — beş ayrı
düzeltme görevi dosyası var: `TASK_FIX_AUTOCODER_OPENCODE_FAILURE`,
`..._CWD_AND_FALSE_SUCCESS`, `..._STDERR_HANDLING`, `..._TIMEOUT_AND_LOGGING`,
`TASK_HARDEN_AUTOPILOT_RUNNER`. Bu, "iskelet sağlam ama maker kötü" tablosuna
uyuyor — ve önerilen çözüm (maker'ı Claude+Codex yapmak) tam da o tarafı
değiştiriyor.

### ⚠️ AYRICA BULUNDU — üçüncü yönetişim çelişkisi
`automation/AUTONOMY_RULES.md` §4:
> *"Self-correct test failures **up to 3 attempts**. Stop and report if still failing."*

`CLAUDE.md` §9:
> *"Auto-fix retry **NOT APPROVED** — bir kontrol BLOCKER/CONCERN verirse
> otomatik düzeltip tekrar denenmez, Ahmet'e gider."*

İki yönetişim dosyası aynı konuda **zıt** söylüyor. `AUTONOMY_RULES.md` daha
eski (06-24 dönemi), `CLAUDE.md` daha yeni (08-06). Ahmet'in §1.2 kararı
(3 deneme, §4 sınırlarıyla) fiilen `AUTONOMY_RULES.md`'ye geri dönüş oluyor.
**İmzadan sonra iki dosya birbirine atıfla hizalanmalı**, yoksa üçüncü bir
oturum hangisine uyacağını bilemez.

---

## 9. İMZA

Bu sözleşme, aşağısı Ahmet tarafından doldurulana kadar **yürürlükte değildir**.

### Ahmet'in ZATEN verdiği kararlar (23.08, seçimle)
- [x] **§1.1 — SINIRLI ZİNCİR** seçildi (tam sürekli DEĞİL)
- [x] **§6 — ayrı çöp Gmail hesabı** seçildi
- [x] **§2 — roadmap denetim raporu** üretildi (`ROADMAP_AUDIT.md`)

### Henüz AÇIK olanlar — imza için gereken
- [ ] §1.2 auto-fix retry (3 deneme, §4 sınırlarıyla) açılsın — onaylıyorum
- [x] §5 Codex review sözleşmesi metnini okudum ve onayladım
      — *26.08 sözlü onay, Claude tarafından kaydedildi. Ahmet imza anında
      teyit etsin; teyit edilmezse işaret kaldırılır.*
- [ ] §6 çöp Gmail hesabını açtım ve Uygulama Şifresini yerleştirdim
- [ ] §8.5 orchestrator'ın parklanma sebebi: hatırlıyorum / hatırlamıyorum
- [ ] `ROADMAP_AUDIT.md` §8'deki K1, K3, K4, K5, K6 kararları verildi

Ahmet, tarih: ______________

**İmzalandıktan sonra yapılacak:** `CLAUDE.md` §9 bu sözleşmeye atıfla
güncellenir (kurallar silinmez, "şu tarihte şu kapsamda delindi, bkz.
AUTONOMY_CHARTER" diye işaretlenir).
