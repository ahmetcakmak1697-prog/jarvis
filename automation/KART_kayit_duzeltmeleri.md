# KART — Ölçüm sonrası kayıt düzeltmeleri

**Durum:** Açık · **Karar:** Ahmet, 2026-09-05
**Önceki kart:** `KART_turkce_modeller.md` (kapandı — `8545387`, `ca652a6`)

Küçük iş, kod yok. Üç ölçüm yapıldı, sonuçları taşıyan üç kayıt eskidi ya da
yanlış. Bu kart onları düzeltir. **Hiçbir model değişmez.**

---

## 1. `docs/HARDWARE_AND_LOCAL_LLM_RESEARCH.md` §4 yanlış bilgi taşıyor

Belge şu an şunu diyor:

> **Turkish-Gemma-9b-T1 (YTÜ COSMOS) — 9B, 8 GB'a sığar**

**Ölçüldü ve yanlış çıktı.** 2026-09-05 temiz koşusunda tepe VRAM **7076 MB** —
belgenin kendi §3'ünde tanımladığı **6144 MB** pratik tavanın üstünde.
Masaüstü yükü çıkarılsa bile 6325 MB. Ölçülen bedel: **2,4 kat yavaş decode,
ilk token 420,8 ms** (llama3.1'de 30,5 ms).

**Hatanın kökü:** §4 **dosya boyutunu** (~5,5 GB Q4) "sığar" diye yazmış. Tepe
VRAM dosya boyutu değildir — KV cache dahildir. Gemma mimarisi KV cache
açısından pahalıdır ve fark tam buradan çıkıyor.

**Yapılacak:**
- §4'teki "8 GB'a sığar" ifadesini **ölçümle değiştir.** Dosya boyutu ve tepe
  VRAM **ayrı ayrı** yazılsın; ikisinin aynı şey olmadığı açıkça belirtilsin.
- Bu ayrım §3'ün de sorunu olabilir — tabloda "Dosya" sütunu var ama tavan
  cümlesi tepe VRAM'den bahsediyor. **Kontrol et;** aynı karışıklık varsa
  orada da netleştir. Yoksa dokunma.
- §7'deki çalışma seti listesinde Turkish-Gemma satırı dosya boyutu veriyor
  (~5,5 GB) — bu doğru, ama yanına "çalışırken tavanı aşar (ölçüldü
  2026-09-05)" notu düşülsün ki bir sonraki oturum aynı tuzağa düşmesin.

> Bu madde bir yazım düzeltmesi değil. Bu satır **beni** yanılttı: ölçülmüş
> gerçeğe güvenip Gemma'yı "sığıyor" diye önerdim, ölçüm tersini gösterdi.
> Belgede kalırsa bir sonrakini de yanıltır.

## 2. `config/runtime_profiles.json` notu eskidi

Aktif profilin `notes` alanı şu an şunu diyor:

> *"Turkish-Gemma-9b-T1 indirilmedi (Ahmet kararı: önce bu değişikliğin etkisi
> dinlenecek)."*

İndirildi ve ölçüldü. **Yapılacak:** notu, ölçümün sonucu ve **local_main'in
neden değişmediği** ile güncelle. En az şunlar geçsin:

- Üç model, aynı oturum, düzeltilmiş terazi: llama3.1 **49/64**
  (A15 yanlış pozitifi olmasa 50), Turkish-Gemma-9b-v0.1 **54/64**,
  Turkcell-LLM-7b **46/64**.
- **Gemma toplamda önde ama iki eksende birden eleniyor:** `grounding` 3/5
  (llama 5/5) — `t2_grounding_003`'te uydurulmuş bir anıya 20 satır kod yazdı,
  `t2_grounding_005`'te persona önsözünden ESHOT/polimer'i geçmiş anlatısına
  çevirdi; ve tepe VRAM 7076 MB ile tavanın üstünde (2,4 kat yavaş,
  TTFT 420,8 ms — §1'in 1,5 sn hedefinde TTFT'ye ayırdığı 100–400 ms bandının
  tamamını tek başına aşıyor).
- Turkcell elendi: `memory` 1/5, `grounding` 0/5 (`t2_grounding_004`'te
  "Kardeşinizin doğum günü 25 Aralık'ta" diye çekincesiz uydurdu),
  64 cevabın hiçbirinde "Efendim" yok.
- **Karar: `local_main` = `llama3.1:latest` DEĞİŞMEDİ** (Ahmet, 2026-09-05).
- Ayrıntı: `automation/MODEL_KIYASI_TURKCE_2026-09-05.md`.

> **`local_main` ve `research_model` değerlerine DOKUNMA.** Yalnız `notes`
> alanı güncellenecek. Profil kuralı "benchmark'sız varsayılan olmaz" diyor;
> benchmark koşuldu ve sonucu **değiştirmemek** oldu — kayıt bunu göstermeli.

## 3. A15 kapatıldı — seçenek (c)

**Ahmet'in kararı: (c) kalsın.** `FOREIGN_RUN_WORDS = 6` değişmiyor.

Gerekçe kayda geçsin: yanlış pozitif oranı 256 cevapta 1 ve dedektör iki
gerçek kusuru yakalıyor. Seçenek (a) — eşiği 7'ye çıkarmak — `t1_tone_017`'deki
gerçek sızıntıyı (*"i can switch to english for you"*, tam 7 kelime) sınıra
oturturdu; ucuz ama kırılgan.

**Yapılacak:** `automation/AHMET_ONAYI_BEKLEYENLER.md`'de A15'i **Resolved**'a
taşı — karar, tarih (2026-09-05), karar sahibi ve yukarıdaki gerekçe ile.
Bilinen maliyeti de yaz: llama3.1'in kayıtlı skoru bu yüzden 49, ölçülen
gerçeği 50.

---

## Yasaklar

1. **Kod değişmez.** Bu kart yalnız belge ve kayıt. `eval/` altına dokunma.
2. **`local_main` / `research_model` değişmez.** Yalnız `notes`.
3. **Eşik oynatma.** A15 kararı (c) — `FOREIGN_RUN_WORDS` 6'da kalır.
4. Çalışma ağacındaki `.agents/`, `.codex/`, `AGENTS.md` **sana ait değil ve
   bu kartın konusu değil** — commit etme, silme, dokunma.

## Bitti sayılma ölçütü

- §4 ölçümle düzeltildi; dosya boyutu ile tepe VRAM ayrımı açık.
- Profil notu güncel; local_main'in **neden değişmediği** yazılı.
- A15 Resolved, gerekçesi ve maliyeti kayıtlı.
- `pytest tests -q` yeşil (iki sırada), `ruff check .` ≤ 293, taban testi 49.
- Commit: yalnız isimli dosya. Push yok. **Bittiğinde dur.**
