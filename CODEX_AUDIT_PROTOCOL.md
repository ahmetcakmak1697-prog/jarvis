# CODEX DENETİM PROTOKOLÜ

> Codex baş denetçisinin JARVIS diff'lerini incelerken kullandığı sabit
> kriter listesi. Bu dosya **denetleyicinin sözleşmesidir**: Codex burada
> yazmayan bir gerekçeyle BLOCKER veremez, burada yazan bir kontrolü de
> atlayamaz.

## Kapsam ve yetki

- Codex **review-only**'dir: bulguyu yazar, düzeltmeyi kendisi uygulamaz.
- Auto-fix retry **NOT APPROVED** (`CLAUDE.md` §9). Bir kriter BLOCKER
  veya CONCERN verirse iş otomatik düzeltilip yeniden denenmez; Ahmet'e
  gider.
- Verdict üç değerden biridir: **PASS** | **CONCERN** | **BLOCKER**.
  Kararsızlık PASS değildir — kararsızlık CONCERN'dür.

## Bulgu formatı

Her bulgu şu üçlüyle yazılır, aksi hâlde bulgu sayılmaz:

1. **Nerede** — `dosya:satır`
2. **Ne olur** — somut başarısızlık senaryosu (girdi/durum → yanlış sonuç)
3. **Neden şimdi** — bu diff'in hangi satırı bu riski yarattı

"Genel olarak dikkatli olunmalı" bir bulgu değildir.

---

## Kriter 1 — Bellek Sızıntısı & Kapatılmamış Socket/I2S Tamponu

Aranan: ömrü boyunca açık kalan veya hata yolunda kapanmayan kaynak.

- I2S/ses akışı, seri port, WebSocket, dosya tanıtıcısı, `subprocess`
  borusu: **her biri** `try/finally`, context manager veya açık `close()`
  ile kapanıyor mu?
- **Hata yolu** da kapatıyor mu? Mutlu yolda kapanıp `except` dalında
  sızdıran kod BLOCKER'dır.
- Sınırsız büyüyen tampon var mı? (`list.append` içeren, hiç boşalmayan
  döngü; `deque(maxlen=...)` olmadan biriken ses çerçevesi.)
- `asyncio` görevleri: oluşturulan her task bekleniyor veya iptal
  ediliyor mu? Sahipsiz task = sessiz sızıntı.
- Test edilebilirlik: `tests/mocks/mock_hardware.py` içindeki mock'lar
  `closed` bayrağı ve `frames_read`/`reads`/`connect_count` sayaçları
  tutar. Kapanış iddiası bu bayrakla **doğrulanmalıdır**, gözle değil.

**BLOCKER eşiği:** hata yolunda kapanmayan donanım/socket kaynağı, veya
sınırsız büyüyen ses tamponu.

---

## Kriter 2 — Ağ Kopması Hata Toleransı (HA / Wi-Fi drop)

Aranan: bağlantı koptuğunda sistemin çökmesi, kilitlenmesi veya sessizce
yanlış davranması.

- HA WebSocket veya Wi-Fi koptuğunda kod **ne yapıyor?** Çökme, sonsuz
  bekleme ve sessiz yutma üçü de kabul edilemez.
- Yeniden bağlanma var mı, ve **geri çekilmeli (backoff)** mı? Sıkı
  yeniden deneme döngüsü hem CPU hem token yakar.
- Yeniden bağlanma sonrası durum tutarlı mı? Kopma anında yarım kalan
  istek tekrar gönderiliyorsa **çift işlem (double delivery)** riski var
  mı?
- Zaman aşımı **her** ağ çağrısında tanımlı mı? Zaman aşımsız `await` =
  kalıcı asılma.
- Sessiz yutma yasak: `except: pass` ile yutulan bağlantı hatası
  BLOCKER'dır (repo genelinde 59 adet `bare-except` bulunduğu bilinir —
  yeni bir tane eklemek regresyondur).
- Test edilebilirlik: `MockHomeAssistantWebSocket(drop_after=N)` geçici
  kopmayı üretir; `connect()` ile toparlanma yolu test edilmelidir.

**BLOCKER eşiği:** zaman aşımsız ağ beklemesi, veya kopmayı sessizce
yutup "başarılı" rapor eden yol.

---

## Kriter 3 — Çoklu Uydu Yarış Durumu (Race Condition / Deadlock)

Aranan: birden fazla uydu (J2/J5) aynı anda konuştuğunda bozulan durum.

- Paylaşılan durum (varlık durumu, wake-word sahipliği, TTS kuyruğu)
  kilitle mi korunuyor, yoksa "nasılsa çakışmaz" varsayımıyla mı?
- **Kilit sırası tutarlı mı?** İki kilit farklı sırayla alınıyorsa
  deadlock vardır — bu, testte görünmeyip sahada kilitlenen sınıftır.
- Kilit tutarken `await` ediliyor mu? Kilit altında yapılan ağ çağrısı
  tüm uyduları bloke eder.
- "Son yazan kazanır" ile üzerine yazılan durum var mı? İki uydu aynı
  anda varlık bildirirse hangisi kazanır ve bu **kasıtlı** mı?
- Aynı wake-word'ü iki uydunun duyması: hangisi cevap verecek, karar
  deterministik mi? (Vector skoru veya zamanlama *girdi*dir, karar
  değil — `CLAUDE.md` §7.)
- Zaman kaynaklı testler: `sleep` ile senkronize edilen test yarışı
  gizler. Deterministik senaryo (`MockLD2410CRadar(script=...)`)
  kullanılmalıdır.

**BLOCKER eşiği:** kilitsiz paylaşılan yazılabilir durum, veya tutarsız
kilit sırası.

---

## Kriter 4 — Graphify Bağımlılık Uyumu (Circular Import Kontrolü)

Aranan: bağımlılık grafiğinin bozulması.

- Diff yeni bir **import döngüsü** yaratıyor mu? Kontrol:
  `graphify update .` sonrası `graphify-out/GRAPH_REPORT.md` içindeki
  **Import Cycles** bölümü. Taban çizgisi: *None detected* (2026-08-30).
  Bu bölümde bir döngü belirdiyse BLOCKER'dır.
- Yeni bir **god node** doğdu mu? Bir modül aniden 60+ kenara ulaşıyorsa
  sorumluluk sızıntısı vardır — en az CONCERN.
- Katman ihlali: alt katman üst katmanı import ediyor mu? (ör. `tools/`
  içinden `agents/` çağrısı, `scripts/` içinden `jarvis_server` çağrısı.)
- Fonksiyon içine gizlenmiş import: döngüyü *saklar*, çözmez. Gerekçesi
  yazılmamış geç import CONCERN'dür.
- Grafik güncelliği: 3'ten fazla dosya değiştiyse `graphify update .`
  çalıştırılmış olmalı (`CLAUDE.md` §13.3). Çalıştırılmadıysa denetim
  eski grafiğe bakıyordur — bu, bulgunun kendisidir.

**BLOCKER eşiği:** yeni import döngüsü.

---

## Denetim çıktısı

Codex denetimi bittiğinde:

1. Verdict (PASS / CONCERN / BLOCKER) + kriter bazında tek satırlık gerekçe.
2. BLOCKER/CONCERN varsa `automation/HUMAN_NEEDED.md`'ye madde açılır.
3. Sonuç `automation/BLACKBOX.jsonl`'ye **append-only** yazılır; önceki
   event silinmez, yeniden yazılmaz — düzeltme yeni bir `sequence`tır.
4. Çözülen kritik mimari/mantık hatası `FAILURES.md`'ye tuzak + kök neden
   + kural üçlüsüyle işlenir (`CLAUDE.md` §13.4).
