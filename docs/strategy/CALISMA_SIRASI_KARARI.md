# ÇALIŞMA SIRASI KARARI — hangi iş neden önce

> **Tarih:** 2026-09-01 · **Durum:** Ahmet onayı bekliyor
> **Ne karara bağlıyor:** Sıradaki işlerin sırası ve neyin *bilerek* ertelendiği.
> **Ne karara bağlamıyor:** Model seçimi (`runtime_profiles.json`), donanım alımı,
> `roadmap_state.json` adımları. Onlar kendi belgelerinde durur.

---

## 0. İLKE — bileşik getiri, özellik değil

Soru "sıradaki özellik ne" değil: **"hangi yetenek, bir kez kurulunca sonraki
beşini ucuzlatır?"**

Filmdeki JARVIS tek bir zekâdır, birçok bedeni vardır — atölye, zırh, konak,
telefon. Bedenler değişir, zekâ tektir ve hatırlar. Bu repoda karşılığı:

- **Tek zekâ** = L0→L4 cascade (yüzey başına ayrı model değil)
- **Birçok beden** = CLI, ses döngüsü, Telegram, ileride ses uyduları, telefon
- **Hatırlar** = `life_graph` + knowledge cards + `query_cache`

Üçü de tasarlanmış ve büyük ölçüde kurulu. Eksik olan tesisat değil, **basınç**.

---

## 1. NEDEN BU KARAR ŞİMDİ — 2026-09-01'de ölçülenler

Bu sıralama his değil, bir günün ölçümünden çıktı.

**Sessiz başarısızlık en pahalı hata türüdür.** Mikrofon altı saat sürdü. Sebep
mikrofon değildi: `sd.InputStream` + bloklayan `read()` DirectSound'da akışı
açıp **tam sıfır** döndürüyordu (`rms 0.000` — aynı aygıtta geri-çağırma yolu
`rms 0.020`). Hata verilmiyordu, kullanıcı yalnız `no_speech_detected`
görüyordu. Teşhis aracı olmadığı için her tahmin bir saat sürdü.

Bunun bedeli tekrar edecek: önümüzde 5 ESP32 uydusu, radarlar, kameralar var.
Her biri sessizce başarısız olabilir. Ayrıntı: `FAILURES.md`.

**Ölçmediğimiz şeyde yanıldık, ölçtüğümüzde kazandık.**

| Ölçüm | Sonuç |
|---|---|
| `mistral-nemo` (o günkü `local_main`) | 6880 MB tepe VRAM, **25,8 tok/s** |
| `qwen2.5:7b` | 5386 MB, **78,2 tok/s** |
| `llama3.1` | 5878 MB, 74,3 tok/s |
| Whisper `small` → `medium` | 2,7 kat yavaş, benzerlik **düştü** → reddedildi |

`docs/HARDWARE_AND_LOCAL_LLM_RESEARCH.md` §3, 8 GB kartta pratik tavanı ~6 GB
model dosyası olarak belgeliyor ve tavanı aşan modelin katman katman RAM'e
taştığını ölçüyor. Yani JARVIS'in "yavaş ve aptal" hissettirmesinin sebebi
model *zekâsı* değil, **modelin karta sığmamasıydı**. Bu, ancak ölçülünce
görüldü — ve ad hoc kurulan bir kıyasla, 20 dakikada.

**Sonuç:** kalite bir his olarak yönetilemez. Bugüne kadar "salak" dedik,
elimizde sayı yoktu.

---

## 2. SIRA

| # | İş | Neden bu sırada |
|---|---|---|
| **0** | Havadaki iş bitsin: A4 (dinamik proje durumu) → A2 (profil) commit'lensin, Ahmet sesli test etsin | Bitmemiş iş üstüne yeni cephe açılmaz |
| **1** | **Kalite regresyon takımı** | Sonraki her karar buna yaslanacak |
| **2** | **Frontier kapısı (L3/L4)** | Zekâ tavanını kaldırır; sonraki her şey bedava iyileşir |
| **3** | **Gözlemlenebilirlik (C4)** | Frontier'ın sızıntı olmaması için |
| **4a** | FAZ-4 **donanımsız** hazırlık — protokol kararı + yüzey soyutlaması | Paralel yürür; donanım gelmeden **karara bağlanması şart** |
| **4b** | FAZ-4 donanımlı iş — bellenim, kablolama, radar kalibrasyonu | Donanım elde olmadan yapılamaz; Ahmet "geldi" deyince açılır |

### 1 — Kalite regresyon takımı

Bugün 1500'den fazla test var ve **hepsi doğruluk ölçüyor**. Kalite için hiçbir
ölçü yok. Model kıyası ad hoc kuruldu; kalıcı hale gelmezse kaybolur ve bir
sonraki model/prompt/routing değişikliği yine his ile değerlendirilir.

Kalıcı hali: sabit Türkçe görev seti, puanlanan çıktı, anlamlı her değişiklikte
koşan. Deterministik olan kodlanır (bozuk kodlama, yabancı kelime sızıntısı,
persona uyumu, gecikme, tepe VRAM); öznel olan Ahmet'e kalır — `FAZ-T1`
deseni: *deterministik kapı yalnız regresyonu tutar, kaliteyi Ahmet onaylar.*

Bu 2'nin önündedir çünkü **ölçemediğin şeyi iyileştiremezsin.** Frontier
kapısını ölçüsüz açarsak iyileşip iyileşmediğini bilemeyiz; yalnız para
harcarız.

### 2 — Frontier kapısı (L3/L4)

Bir özellik değil, **tavan kaldırma**. `agents/model_cascade.py` bugün açıkça
şunu diyor: *"L4 is NEVER selected automatically."* Yani bulut beyin bağlı ama
kapı kapalı.

Açıldığında bedava iyileşenler: ev otomasyonu muhakemesi, derin araştırma,
proje zekâsı, uydu konuşmaları, "akşama rapor ver" senaryosu. Hepsi aynı
kapıdan geçecek.

Ve tasarım gereği **zamanla ucuzlar**: `answer_crystallizer` + knowledge cards
sayesinde aynı soru ikinci kez dışarı çıkmaz. Çoğu sistem büyüdükçe pahalanır;
bu tersine çalışacak şekilde kurulmuş.

Sınırlar değişmedi: varsayılan kapalı, `data_classifier` redaction'ı egress
öncesi, `cost_ledger` bütçe tavanı, bütçe bitince sessizce yerele düşüş,
API anahtarını `.env`'e **yalnız Ahmet** koyar.

### 3 — Gözlemlenebilirlik

`cost_ledger` var, vitrin yok. Ne nereye gitti, ne tuttu, ne kadar tuttu —
görünmeden frontier kapısı bir sızıntıdır.

### 4a — FAZ-4 donanımsız hazırlık (paralel yürür)

**Donanım durumu 2026-09-01:** sipariş verildi, yolda, **elde değil**.
`automation/FAZ4_ADIM_ONERISI.md` §1'deki envanter tablosu *sipariş edilen*
listedir; teslim alınmış değildir. Ahmet geldiğinde bildirir.

`FAZ4_ADIM_ONERISI.md`'nin ilkesi geçerliliğini koruyor: *donanım gerektirmeyen
hazırlığı şimdi yap, donanım gelince sadece tak ve doğrula.* Ama o hazırlığın
tamamı eşit değil. İkiye ayrılır ve yalnız biri şimdi yapılabilir.

**✅ HA/Wyoming adopt-vs-build kararı VERİLDİ (Ahmet, 2026-09-01).**

`automation/LOOP0D_J0B_SAFETY_CONTRACT.md` §6 üç seçeneği kaydetmişti (A: ayrı,
B: HA/Wyoming'e devir, C: hibrit) ve `CLAUDE.md` §12 bunu açık madde olarak
listeliyordu. **Bu madde artık kapalıdır.** Karar:

> **Her şey bu PC'den döner.** Raspberry Pi yok, ayrı sunucu yok, laptop
> sunucu yok. Home Assistant bu Windows makinesinde bir uygulama olarak
> çalışır. ESP32 uyduları, sensörler ve kameralar **ESPHome** bellenimi ile
> **WiFi üzerinden** HA ile konuşur. **Özel protokol yazılmayacak.**
> Ölçüt: "en sağlıklı çalışan hangisiyse o." Fantezi sonraya.

Neden bu karar sağlam: ESP32 bellenimi standart hale gelir, sıfırdan protokol
yazılmaz (`CLAUDE.md` §9 adopt-over-build). Wyoming, HA'nın STT/TTS
servisleriyle konuşma biçimi olarak zaten devrededir; ayrı bir entegrasyon
kalemi değildir.

**Bilinen bedel, kayda geçsin:** PC kapalıysa ev aptaldır. Raspberry Pi 7/24
açık kalmak için vardır; oyun oynanan ve Windows güncellemesi için yeniden
başlayan bir makine değildir. Ayrıca HA + Docker + Ollama (5–6 GB VRAM) +
Whisper aynı kartı paylaşacak. Bu bedel **bilerek kabul edildi**; karar geri
dönülemez değil — HA yapılandırması taşınabilir, ileride ayrı donanıma
geçilmek istenirse kopyalanır.

**İkinci sırada — ve bu aslında bileşik getirili:**
Ses hattının **kaynaktan bağımsız** hale gelmesi. `voice/stt.py` zaten
`chunk_source` parametresi taşıyor, yani mimari bunu öngörmüş; eksik olan ağ
üstünden gelen bir kaynağın aynı boruya bağlanabilmesi ve hangi uydunun
konuştuğunun taşınması.

Bunu FAZ-4 işi saymak yanıltıcı: bu, §0'daki **"tek zekâ, birçok beden"**
alt yapısının kendisidir. CLI, yerel mikrofon, uydu, Telegram, telefon — hepsi
aynı soyutlamadan geçer. Yani uydular için yapılan iş, uydular gelmese bile
değerini korur. Bileşik getirisi olduğu için sıraya girmeyi hak eder.

### 4b — Donanım geldiğinde

Bellenim, kablolama, radar kalibrasyonu, oda yerleşimi. Bunlar donanımsız
yapılamaz ve simüle edilmesi çöpe giden iş üretir.

**✅ Beşinci uydu kararı VERİLDİ (Ahmet, 2026-09-01):** eksik parçalar
(1 hoparlör + 1 LD2410C radar) **alınmayacak**, bu iş ileriye kaldı.
`FAZ4_ADIM_ONERISI.md` §1'deki eksik kayıtlı kalır; beşinci uydu ya "yalnızca
dinleyen" olarak tanımlanır ya da kurulmaz. Donanım gelince netleşir.

### Neden 4b sıranın sonunda

Aptal bir JARVIS'i beş odaya yaymak, aptallığı beş katına çıkarır. Uydular
zekâyı **taşır**, üretmez. Önce basınç, sonra borular.

---

## 3. BİLEREK ERTELENENLER — yazılı, ki geri gelmesin

Bunların hiçbiri "kötü fikir" değil. Hiçbiri **sonrakini ucuzlatmıyor**, bu
yüzden sırada değil. Yeniden gündeme gelirse bu bölüm cevaptır.

| Erteleneni | Gerekçe |
|---|---|
| **Turkish-Gemma-9b-T1 indirmesi** | Bedava kazanç (`mistral-nemo`'yu çıkarmak) henüz kulakla test edilmedi. 8K bağlam sınırı persona + proje durumu + hafıza bütçesini zorlar; Türkçe tokenizer cezası ~1,9× bunu ağırlaştırır. Yerel Türkçe hâlâ yetersizse tekrar bakılır. |
| **TTS tını ayarı / ses klonlama** | Tek seferlik kozmetik. Gerçek bir kişinin sesini klonlamak (Paul Bettany dahil) izin gerektirir; kapsam dışı. |
| **Whisper `medium`** | **Ölçüldü ve elendi:** 2,7 kat yavaş, benzerlik düştü. Ölçmeden yükseltilseydi hem yavaşlar hem kalite kaybederdik. |
| **MoE / `--n-cpu-moe` ile 30B sınıfı model** | Gerçek bir seçenek (§3'te ölçülmüş) ama motor sorusu açık ve frontier kapısından sonra değeri düşer. |
| **"Full autopilot / sıfır soru" akışı** | `CLAUDE.md` §9 ihlali. Bir kez denendi: gözetimsiz bir oturum 381 commit'i yeniden yazdı ve 38 çapraz referansı kırdı. Katmanlı denetim korunur. |
| **Abonelik oturumu üzerinden "sınırsız" API** | Kullanım şartları ihlali, hesap riski, ve sürekli kırılan bir bağımlılık. Meşru yol: Claude API + yerel-önce cascade + önbellek. |

Bu tablo `docs/JARVIS_VISION_BACKLOG.md`'nin kendi kuralının uygulanmasıdır:
*"Hiçbir yeni model/proje heyecanı sırayı bozmaz."* Fikir kaydedilir; sıra
bozulmaz.

---

## 4. BU BELGENİN DİĞERLERİYLE İLİŞKİSİ

- `roadmap_state.json` — adımların **durumu** orada, sırası burada. Çelişirse
  `roadmap_state.json` kazanır (kendini "TEK DOĞRULUK KAYNAGI" ilan ediyor).
- `docs/JARVIS_VISION_BACKLOG.md` — *ne* istendiği orada, *ne zaman* burada.
- `automation/FAZ4_ADIM_ONERISI.md` — hâlâ geçerli; yalnız aciliyeti düştü.
- `CLAUDE.md` §9 — bu belge hiçbir değişmez kuralı gevşetmez.

## 5. AHMET'İN KARARINA KALANLAR

1. Bu sıra kabul mü? (kabul edilirse madde 1'in kartı yazılır)
2. `runtime_profiles.json` — `local_main` hangisi olsun? Ölçüm `mistral-nemo`'yu
   eliyor; `qwen2.5:7b` ile `llama3.1` arasını **kulak** ayırır.
3. Frontier kapısı için hangi sağlayıcı ve hangi aylık tavan?
4. GitHub yedeği: depo **private** olarak açıldı mı, URL nedir? (İlk push
   Ahmet'in; sonrasında yalnız onaylanmış commit'ler push edilir — `CLAUDE.md`
   §9'un özü korunur.)

**Kapanan kararlar:** HA/Wyoming (§4a) ve beşinci uydu (§4b) 2026-09-01'de
karara bağlandı. `CLAUDE.md` §12'deki "HA/Wyoming adopt-vs-build" açık maddesi
artık kapalıdır ve o bölüm güncellenmelidir.
