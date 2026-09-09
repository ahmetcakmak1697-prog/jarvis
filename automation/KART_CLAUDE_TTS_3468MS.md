# KART — 3.468 ms'nin içini aç: sentez mi, ağ mı, oynatıcı mı?

**Kime:** Claude Code (VS Code) · **Veren:** Ahmet, 2026-09-09
**Dal:** `auto/opencode-deepseek` · **Taban:** `6e3d033`

---

## Neden bu iş

Bugün ölçüldü (5 tur, mikrofonlu, Edge TTS açık —
`automation/SES_HATTI_COZUMLEME_2026-09-09.md`):

```
sentez_ve_oynatma_ms  =  3.468 ms  +  72,2 ms × karakter      R² = 0,986
```

Eğim normal konuşma hızı (13,8 karakter/saniye) — orada kusur yok.
**Sabit terim 3.468 ms, ilk sese kadar ödenen bedel.** Model payı yalnız
687 ms. Yani PUSULA'nın 1.500 ms'lik bütçesinin **%83'ü buradan gidiyor**
ve içinde ne olduğunu bilmiyoruz.

Bu belirsizlik doğrudan bir kararı kilitliyor: **akışlı TTS işe yarar mı?**

- Bedel ağ gidiş-dönüşüyse → akışlı TTS ilk cümleyi erken söyletir, kazanır.
- Bedel yerel dosya yazımı / oynatıcı kurulumuysa → akışlı TTS **hiçbir şey
  kazandırmaz** ve boşuna mimari değişiklik yapılmış olur.

Ve 3.468 ms bir **çıkarımdır** — beş noktalı regresyonun kesişimi, doğrudan
gözlenmedi. Bugünün dersi tam olarak buydu: çıkarımı ölçüm gibi sunmak
(`FAILURES.md` → 2026-09-09 kaydı).

---

## ADIM 1 — Olay damgaları (test-first)

`scripts/j0_tts_adapters.py` → `EdgeTTSAdapter.speak()` içine **ölçüm** koy.
Davranışı değiştirme, yalnız zamanı kaydet:

| Damga | An |
|---|---|
| `t0` | `speak()` girildi |
| `t_istek` | sentez isteği gönderildi |
| `t_ses_hazir` | ses baytları elde (dosya/bellek hazır) |
| `t_oynatma_basladi` | oynatıcıya ilk bayt verildi |
| `t_bitti` | `speak()` döndü |

Türeyen alanlar: `sentez_ms = t_ses_hazir - t_istek`,
`oynatici_kurulum_ms = t_oynatma_basladi - t_ses_hazir`,
`oynatma_ms = t_bitti - t_oynatma_basladi`.

`TTSResult`'a bu alanları ekle. **Ölçülemeyen alan `None` döner, `0` değil.**

`first_audio_hint_ms` zaten var ve kendi uyarısı "synthesis time only,
playback start is not measured" diyor. Bu kart o boşluğu kapatıyor —
**mevcut alanı silme**, yanına gerçek olanı koy ve hangisinin ne ölçtüğünü
docstring'e yaz.

**Önce düşen testi yaz, kırmızı olduğunu GÖR.** En az:
- damgalar monoton artıyor (`t0 ≤ t_istek ≤ ... ≤ t_bitti`)
- bileşenlerin toplamı `t_bitti - t0`'ı **aşmıyor**
- oynatıcı devre dışıyken `oynatma_ms` `None`, `0` değil
- sahte bir sentez ucuyla uçtan uca çalışıyor, ağa çıkmadan

## ADIM 2 — Ölçüm

**Sentetik metin kullan, Ahmet'in gerçek cevaplarını değil.** Egress
Ahmet'in bu ölçüm için onayladığı şeydir; onaylanan şey ölçüm, kişisel
veri değil. Uzunluğu bilinen 4 Türkçe cümle: ~20, ~60, ~120, ~240 karakter.
Her uzunluk **5 kez**.

Bayrağı yalnız ölçüm sürecinde tanımla (`JARVIS_J0_EDGE_TTS_ENABLED=1`),
hiçbir dosyaya yazma, `.env`'e dokunma.

Ayrıca **oynatmasız** bir tur koş (yalnız sentez). İkisinin farkı oynatıcı
kurulumunun payını doğrudan verir.

Çıktı: `automation/TTS_ANATOMISI_2026-09-09.md`.

**Cevaplanacak tek soru:** 3.468 ms'nin kaçı ağ, kaçı yerel?

Ve bir doğrulama: bugünkü regresyonun eğimi (72,2 ms/karakter) ile
doğrudan ölçülen `oynatma_ms / karakter` **uyuşuyor mu?** Uyuşmuyorsa
regresyon modeli yanlıştı ve bu belge onu söylemeli — kendi çıkarımımı
doğrulatmak için değil, sınamak için koyuyorum.

## ADIM 3 — Seçenek sun, hüküm verme

Ölçüme dayanan seçenekleri maliyetiyle yaz:

- Akışlı TTS (ilk cümlede konuşmaya başla) — **yalnız bedel ağdaysa**
- Sentez önbelleği (sık cümleler için) — kaç turda işe yarar?
- Oynatıcıyı önceden ısıtmak — pygame kurulumu paya giriyorsa
- Yerel TTS (Piper) — **park edilmiş cephe, §9, ayrı imza**; yalnız
  ölçülen ağ payı büyükse anlamlı, o zaman bile karar Ahmet'in

Desteklenmeyen seçeneği yazma.

---

## Sınırlar

- `main.py` ve ses döngüsünün davranışı **değişmez**; bu kart yalnız ölçer.
- Yeni bağımlılık yok. `config/` dosyalarına dokunma.
- `.env` okunmaz, yazılmaz (§9).
- Kapı: `pytest tests -q` **iki sırada**, `ruff check .` **≤ 283**.
- Auto-fix retry yok. Push yok. Bitince **DUR**.

## Bitti sayılma ölçütü

- `EdgeTTSAdapter.speak()` beş damgayı üretiyor, testleri var, kırmızı görüldü.
- `automation/TTS_ANATOMISI_2026-09-09.md` dört uzunluk × 5 tur + oynatmasız
  turu taşıyor.
- "3.468 ms'nin kaçı ağ" sorusu **sayıyla** cevaplı.
- Regresyon eğimi doğrudan ölçümle karşılaştırıldı; uyuşmazlık varsa yazıldı.
- Kapı iki sırada yeşil, ruff ≤ 283.
