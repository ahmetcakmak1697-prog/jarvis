# STT DOĞRULAMA — `small`/5 + `hotwords` ölçümü

**Kart:** `automation/KART_STT_DOGRULA.md` · **Tarih:** 2026-09-25
**Dal:** `auto/opencode-deepseek` · **Taban:** `fa62ff4`
**Sonda:** `scripts/olc_stt_turkce.py dogrula`
**Kayıtlar:** `%TEMP%\jarvis_stt_kayit\dogrula-20260924-215203` (A + ilk B),
`dogrula-20260925-002405` (ikinci B) — **repo dışında**, Ahmet'in sesi.

> **HÜKÜM: BELİRSİZ.** Kazanç ölçüldü ve büyük; risk **hâlâ ölçülmedi.**
> Ayrıntı §4'te. Hiçbir varsayılan değiştirilmedi.

---

## 1. ADIM 2 — uyandırma cümlesi, 10 okuma

Kartın istediği yayılım örneklendi: her okuma bir koşul etiketiyle alındı
(normal / hızlı / yavaş / mikrofondan biraz uzak / cümle başında
duraklayarak, ikişer kez).

| ayar | "Hey Jarvis" | kaçırdığı koşullar |
|---|---|---|
| `small`/1 (**mevcut üretim**) | **5/10** | hızlı ×2, uzak, yavaş, duraklayarak |
| `small`/5 (ipucusuz) | **4/10** | hızlı ×2, uzak, yavaş, duraklayarak ×2 |
| **`small`/5 + `hotwords`** | **9/10** | hızlı (1 kez) |

Toplam WER yazılmadı — kartın kuralı: ölçülen tek şey o cümlenin duyulup
duyulmadığı.

**İki bulgu, ikisi de kartın beklentisinin dışında:**

**(a) `beam_size` tek başına işe yaramıyor, hatta zarar veriyor.** 4/10,
üretimdeki 5/10'un altında. Kazancın tamamı `hotwords`'ten geliyor. Kart
"beam 5 tek başına da düzeltmiyor" diyordu; ölçüm bunu doğruluyor ve bir
adım ileri götürüyor — beam 5'i `hotwords` olmadan almanın gerekçesi yok.

**(b) Hata her zaman aynı yerde ve aynı türde.** Cümlenin geri kalanı
doğru alınıyor, yalnız ad bozuluyor: *Cervis* (4 kez), *service* (2),
*Hicabi'si*, *Heicar mısın*. Yani sorun akustik anlaşılırlık değil,
modelin sözlüğünde bu adın olmaması — `hotwords`'ün tam olarak
çözdüğü şey bu.

Ham örnekler:

```
[2] hizli      small/1  'Hey Cervis, nerede kaldık?'
               +hot     'Hey Jarvis, nerede kaldık?'
[8] yavas      small/5  'Hey service nerede kaldık?'
               +hot     'Hey Jarvis, nerede kaldık?'
[7] hizli      +hot     "Hey Jarvis'i nerele kaldık?"   ← tek kaçan
```

## 2. ADIM 3 — sızıntı: iki koşu, ikisi de eksik

### Birinci koşu (20260924-215203) — GEÇERSİZ, konuşma içeriyor

Üç klibin üçünde de konuşma vardı; "sessiz oda" klibi baştan sona bir
sohbet yazıya döktü. Kart bu kliplerin **konuşmasız** olmasını istiyor,
çünkü ölçülen şey Whisper'ın konuşma-olmayan sesten ne ürettiği.

Bu koşudan çıkan tek ilginç satır, **sızıntı sanılıp değil çıktı:**

```
klavye klibi  ipucusuz : "... İki araç denemeleri yapıyorum ..."
              ipuçlu   : "... Jarvis denemeleri yapıyorum ..."
```

İpucu kelimesi yalnız ipuçlu satırda göründü — kartın aradığı desen. Ama
Ahmet'e soruldu ve **gerçekten "Jarvis denemeleri yapıyorum" demiş.**
Yani bu sızıntı değil **düzeltme**: ipucu, ipucusuz sürümün kaçırdığı
gerçek kelimeyi yakaladı. `hotwords` lehine bir kanıt, aleyhine değil.

### İkinci koşu (20260925-002405) — konuşmasız, ama gürültüsüz de

| klip | tepe | `small`/5 ipucusuz | `small`/5 + `hotwords` |
|---|---|---|---|
| sessiz oda | 0.0001 | **boş** | **boş** |
| klavye/fare sesi | 0.0000 | **boş** | **boş** |
| arka planda konuşma/müzik | 0.0002 | **boş** | **boş** |

İpucu yüzünden eklenen kelime: **yok.**

Ama bu sonuç kartın sorusuna cevap vermiyor. Klipler dijital sessizlik
seviyesinde ve `vad_filter` hepsini Whisper'a ulaşmadan kesti. Yani
ölçülen şey *"VAD kapalıyken ipucu sızamaz"* — kartın açıkça yazdığı risk
ise **VAD'den geçen** gürültü. Klavye klibi de müzik klibi de taşımaları
gereken sesi taşımamış.

## 3. Ölçüm sırasında düzeltilen bir yanılgı (benim)

İkinci koşunun sessiz çıkması "mikrofon susturulmuş" diye okundu ve
Ahmet'e iki kez söylendi. **Yanlıştı.** Kanıt olarak sunulan şey ilk
koşudaki "sessiz oda" klibinin 0.0318 tepesiydi — ama o klipte Ahmet
konuşuyordu, yani oda tonu değil sesi ölçülmüştü. Sessiz bir klip,
konuşma içeren bir klibe karşı kıyaslandı.

Sabit 0.00003 değerinin "cihaz dijital sessizlik gönderiyor" işareti
olduğu çıkarımı da yanlıştı: o sayı SoloCast'ın gürültü tabanının
kendisi. Kırk saniyelik izleyici bunu kapattı — 1-6. saniye 0.00003,
7-31. saniye konuşmayla 0.019–0.095, 33-40. saniye yine 0.00003.
Mikrofon baştan beri çalışıyordu ve oda gerçekten o kadar sessizdi.

**Kural:** bir gürültü tabanını ölçerken karşılaştırma tabanının da
gürültü olduğu doğrulanmalı. İçinde konuşma olan bir klip, sessizlik
ölçümü için referans değildir.

## 4. HÜKÜM — BELİRSİZ (ADIM 4)

Kartın üç seçeneğinden ikincisi değil üçüncüsü:

- **Geçti değil:** koşul "uyandırma cümlesi çoğunlukla doğru **ve** ipucu
  kelimesi hiçbir gürültü klibinde çıkmadı". İlk yarı fazlasıyla sağlandı
  (9/10). İkinci yarı sağlanmış **sayılamaz**, çünkü VAD'den geçen
  gürültüyle hiç sınanmadı.
- **Kaldı değil:** ipucu kelimesi hiçbir yerde uydurma olarak çıkmadı.
  Çıktığı tek yer gerçek bir düzeltmeydi.

**Eksik olan tek ölçüm, açıkça:** gürültü tabanının **üstünde** kalan,
konuşma içermeyen bir klip — normal ses seviyesinde müzik ya da TV,
Ahmet susarken. Bir klip yeter; `dogrula-kaydet --okuma 0` ile alınır.

O klipte de ipucu kelimesi çıkmazsa hüküm **Geçti**'ye döner ve uygulama
kartı yazılabilir. Çıkarsa **Kaldı** olur ve `hotwords` üretime alınmaz.

**Hiçbir şey uygulanmadı.** `voice/stt.py`'de tek varsayılan değişmedi,
`vad_filter` hiçbir yolda kapanmadı, önceki ham ölçümlere (`olcum.json`,
`olcum_ipucu.json`) dokunulmadı.
