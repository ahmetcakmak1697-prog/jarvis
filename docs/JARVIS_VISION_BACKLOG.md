# JARVIS — VİZYON BACKLOG'U (sırayı bozmaz, unutulmaz)

> **Bu dosyanın amacı:** Ahmet'in aklına gelen yeni hedefleri kaydetmek — ama
> `REALITY_OS_ROADMAP.md` §9'daki **stratejik sırayı bozdurmadan.**
>
> Kendi frenimiz (§10, üç AI mutabakatı): *"Hiçbir yeni model/proje heyecanı
> sırayı bozmaz."* Buraya yazılan madde **hemen yapılacak** demek değildir;
> **unutulmayacak** demektir.
>
> Bir madde olgunlaşınca `roadmap_state.json`'a makine kriterleriyle aktarılır
> ve ancak o zaman sıraya girer.

**Oluşturma:** 2026-08-23
**Kaynak:** Ahmet'in 2026-08-20 ve 2026-08-23 tarihli vizyon anlatımları

---

## 0. VİZYONUN KENDİ CÜMLESİ (Ahmet, 2026-08-23)

Iron Man'deki JARVIS gibi bir asistan. Soru–cevap kutusu değil:

- Her şeyi danışabileceği, gerekirse **iş yaptırabileceği** bir varlık
- Ev otomasyonunu tamamen devralan
- Ahmet işteyken **atölyede/araştırmada kendi başına çalışan**, akşam rapor veren
  ("kuantum bilgisayarları çalış", "yeni bir element üzerine çalışalım")
- Eve gelen kişiyi tanıyan, tanımadığını kapıda karşılayan
- Ev ağını **kale gibi koruyan** — sızma girişimini tespit eden
- İyiliğe bağlılık yemini etmiş, çok yetenekli ve zeki bir savaşçı gibi
- **Motor kaskından** konuşulabilen
- Ahmet Bursa'dayken bile İzmir'deki PC'de çalışan JARVIS'e erişilebilen

Mevcut roadmap'in vizyon cümlesiyle uyumlu:
> *"...tek bir karakter gibi davranan kişisel gerçeklik işletim sistemi."*
> Pusula: *"Tony Stark zeki değildi; API limiti yoktu."*

**Kaynak kısıtı (Ahmet'in şartı):** minimum VRAM/RAM/işlemci ile maksimum verim.
Minimum harcama, maksimum çıktı.

---

## 1. ✅ ZATEN ROADMAP'TE OLANLAR (yeni değil — sırada bekliyor)

Ahmet'in anlattıklarının çoğu zaten yazılı. Yeniden yazılmasına gerek yok:

| İstenen | Roadmap karşılığı |
|---|---|
| Filmdeki JARVIS hissi, karakter | **Z** — Character & Presence (Z0 SOUL.md, Z1 presence modes, Z2 anti-repetition, Z4 gece protokolü) |
| Sesle konuşma, kesebilme | **V** — V0 wake word → V1 STT → V2 butler TTS → V3 streaming → V4 barge-in → V5 state göstergesi |
| Ev otomasyonu devri | **M1** Home Assistant + Wyoming köprüsü, **M3** oda/cihaz/sahne |
| Atölye / proje zekâsı | **M2** Project Forge / Maker Lab |
| Derin araştırma (kuantum, element) | **D3–D5** derin araştırma orkestrasyonu + decision support |
| Model seçimi / verim | **G1** Jarvis-specific Model Benchmark Lab |
| İzleme / kara kutu | **C4+** Observability |

---

## 2. 🆕 ROADMAP'TE OLMAYANLAR — YENİ HATLAR

### ⬜ P — Presence & Person Awareness (kapı / ev içi kimlik)
*Mevcut `I — Vision/Perception` hattı yalnızca ekran/oda/belge anlama diyor;
**kişi tanıma hiç yok.** Bu yüzden ayrı hat açıldı.*

- ⬜ **P0 Kapı etkileşimi (kimlik gerektirmez)** — kapıya biri geldiğinde
  karşılama, "kargo mu?" tipi diyalog, Ahmet'e bildirim. Kimlik tanıma
  olmadan da çalışır; **en hızlı değer üreten madde bu.**
- ⬜ **P1 Rızalı kayıt (enrollment)** — aile, eş, eşin ailesi, arkadaşlar,
  akrabalar kendi rızalarıyla yerelde kaydolur (kamera önünde tanıtım).
  Veri **evden çıkmaz**. Filmdeki JARVIS de Tony/Pepper/Rhodey'i tanır —
  yani zaten elindeki insanları; bu desen birebir aynı.
- ⬜ **P2 Yüz tanıma motoru** — yerel, GPU'da. Aday: InsightFace/ArcFace,
  face_recognition (dlib), DeepFace. G1 benzeri küçük bir doğruluk/hız testi
  ile seçilir. **Karar verilmedi.**
- ⬜ **P3 Bilinmeyen kişi protokolü** — tanınmayan biri = "bilinmeyen kişi".
  Sistem kimliklendirmeye **çalışmaz**; kayıt + bildirim + kapı diyaloğu.
- ⬜ **P4 Mimik / duygu okuma** — karşılama tonunu uyarlamak için
- ⬜ **P5 Ev içi varlık (presence)** — kim hangi odada, JARVIS oraya konuşsun
- ⚪ P6 Ses ile kişi tanıma (speaker ID) — yüzü görmeden tanıma
- 🟡 Borrow: InsightFace, Frigate (NVR + object/face pipeline, HA entegre),
  Double Take, CompreFace

**Kapsam dışı bırakılan (Claude'un çizdiği tek sınır):** tanınmayan bir kişiyi
**sosyal medya/internet taraması ile kimliklendirmek**. Rıza vermemiş üçüncü
kişilerin biyometrik profilini derlemek anlamına geliyor. P0–P5 bu olmadan
çalışır ve Ahmet'in anlattığı senaryoların (kargocu, aile, misafir) tamamını
karşılar.

**Fizik notu (etik değil):** "retina taraması" kapıda mümkün değil — retina
okuması gözün IR kaynağa 1–3 cm mesafede olmasını ister. İris tanıma mesafeden
mümkün ama özel NIR donanım + kişinin iş birliği gerekir. Kapıda gerçekten
çalışan şey: **yüz + boy/duruş + kıyafet + ses.**

### ⬜ S — Security & Sentinel (evi kale gibi koruma)
*Roadmap'te hiç yok. `H0` prompt-injection tarafı var ama **ağ güvenliği yok.***

- ⬜ **S0 Ağ envanteri** — evdeki her cihazı tanı, yeni cihaz görünce haber ver
- ⬜ **S1 Sızma tespiti (IDS)** — router/ağ trafiği izleme.
  🟡 Borrow: Suricata, Zeek, CrowdSec, OPNsense
- ⬜ **S2 Anomali bildirimi** — "tanımadığım bir cihaz ağa girdi", "dışarıdan
  şu porta tarama geldi"
- ⬜ **S3 Log toplama + JARVIS'in anlatması** — ham log değil, Türkçe özet
- ⬜ S4 Kamera/kapı olaylarıyla birleştirme (P hattıyla kesişir)
- ⚪ S5 Aktif yanıt (karantina/engelleme) — **dikkatli**, yanlış pozitif evi
  internetsiz bırakır

### ⬜ R — Remote & Mobility (kask + Bursa)
*Roadmap tamamen yerel varsayıyor; uzaktan erişim hiç kurgulanmamış.*

- ✅ **R0 Güvenli tünel — ZATEN VAR.** Tailscale bu PC'de kurulu ve çalışıyor
  (2026-08-23'te doğrulandı). Bursa'dan İzmir'deki JARVIS'e erişimin altyapısı
  hazır; yapılacak iş telefona/kaska istemci kurmak.
- ⬜ **R1 Telefon istemcisi** — sesli konuşma, tünel üzerinden
- ⬜ **R2 Kask modu** — motor kaskında bluetooth kulaklık; gürültü, eldiven,
  ekransız kullanım. Tamamen sesli, kısa cevap, tek komut.
- ⬜ **R3 Bağlantı koptuğunda davranış** — telefonda yerel bir "cep JARVIS"i mi
  olsun, yoksa sadece "bağlantı yok" mu desin? **Karar verilmedi.**
- ⬜ R4 Bant genişliği/gecikme uyarlaması (mobil şebeke)

---

## 3. 🔧 AÇIK KARARLAR (Ahmet'e ait)

> **Kimlik notu:** buradaki kararlar `VK` önekiyle numaralandırılır. §2'deki
> **V hattı** (ses: V0 wake word … V5) başka bir şeydir; çıplak `V2` yazılması
> ikisini karıştırıyordu.

| # | Karar | Bağlam |
|---|---|---|
| VK1 | Bu üç hat (P, S, R) sıraya ne zaman girsin? | §10 freni: sırayı bozmasın |
| ~~VK2~~ | ~~Donanım: 2×3090 / 1×5090 / mevcut + RAM+SSD~~ ✅ **cevaplandı (23.08)** — `docs/HARDWARE_AND_LOCAL_LLM_RESEARCH.md`: üçü de hayır, yalnızca 2 TB SATA SSD. Ev otomasyonu donanımı ayrı karar. |
| VK3 | P2 yüz tanıma motoru hangisi | G1 tarzı küçük test gerekir |
| VK4 | R3 bağlantı koptuğunda ne olacak | |
| VK5 | S5 aktif yanıt olacak mı | yanlış pozitif riski |

---

## 4. KAYIT DİSİPLİNİ

Yeni fikir geldiğinde:
1. **Buraya yazılır** — hemen yapılmaz, unutulmaz
2. Olgunlaşınca makine kriterli adıma çevrilir
3. `roadmap_state.json`'a aktarılır
4. Ancak o zaman sıraya girer

Bu dosya sıra listesi **değildir**; hafızadır.
