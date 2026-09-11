# Bulut çağrısına TEK yeniden deneme — uygulama raporu

**Kart:** `automation/KART_BULUT_TEK_YENIDEN_DENEME.md` (Ahmet onayı, 2026-09-11)
**Dal:** `auto/opencode-deepseek` · **Taban:** `c2ba1ce`
**Tarih:** 2026-09-11 · **Uygulayan:** Claude Code

---

## 0. Kısa hâli

Yeniden deneme çalışıyor ve **bütçe büyümedi.** Düşme oranı
**%33,3 → %9,5** (63 turda 6). Mekanizmanın iş yaptığı ayrıca kanıtlandı:
12 yeniden deneme ateşlendi, 6'sı turu kurtardı.

Sekiz test, hepsi önce kırmızı; **10/10 mutasyon senaryosu kırmızı yandı.**

Bedeli var ve §3b'de yazılı: **kurtarılan turlar yavaş.** Kullanıcı artık
daha seyrek llama duyuyor ama bazen 13–16 saniye bekliyor.

Kartın §4'ü ile §5'i çelişiyordu; nasıl çözdüğüm §5'te.

---

## 1. Bütçe bölündü, büyütülmedi (kartın §1'i)

```
1. deneme    12,0 s   (toplamın %60'ı)
geri çekilme  0,5 s
2. deneme     7,0 s   (toplamın %35'i)
---------------------
en kötü      19,5 s   <  20 s tavanı
```

`DEFAULT_TIMEOUT_S = 20` **değişmedi.** Bölüşüm oranlardan türetiliyor
(`_deneme_butceleri`), sabit yazılmıyor — yani tavan ileride değişirse
bölüşüm kendiliğinden uyuyor ve toplam yine tavanın altında kalıyor.

Bütçe iki denemeye + geri çekilmeye sığmıyorsa (T < 10 s) **tek deneme**
yapılıyor: yeniden deneme bir kolaylıktır, tavanı delmek için gerekçe
değil.

Testle kilitli:

```python
assert butceler == [12.0, 7.0]
assert sum(butceler) + _GERI_CEKILME_S <= DEFAULT_TIMEOUT_S
```

ve ayrıca `_http_json`'a **fiilen geçen** değerlerde: `[12.0, 7.0]`.
Hesabın doğru olması yetmez, çağrıya o değerin gitmesi gerekir.

---

## 2. Çağrı sayıları — tam doğrulandı

| durum | beklenen | test |
|---|---|---|
| geçici hata → ikinci deneme başarılı | **2** | `test_gecici_hatadan_sonra_ikinci_deneme_cevabi_getirir` |
| iki deneme de koptu | **2** (üç değil) | `test_iki_deneme_de_koparsa_ucuncu_deneme_YOK` |
| HTTP 401 (kalıcı) | **1** | `test_kalici_hata_TEKRARLANMAZ` |
| boş cevap | **1** | `test_bos_cevap_TEKRARLANMAZ` |

`HTTPError` bir `URLError` **alt sınıfıdır**; önce o ayıklanıyor, yoksa
401 de "geçici" sayılıp boşuna tekrarlanırdı. Mutasyon bunu doğruladı:
ayrım kaldırılınca 401 iki kez denendi ve test kırmızı yandı.

Boş cevap bilerek tekrarlanmıyor: hattın değil **modelin** sonucudur.

Anahtar hiçbir yeniden deneme yolunda sızmıyor — redaksiyon **son
denemenin** hata metnine de uygulanıyor
(`test_anahtar_yeniden_deneme_yolunda_da_sizmaz`).

---

## 3. ADIM 4 — oran yeniden ölçüldü

Aynı üç soru sınıfı, aynı tur sayısı (7/sınıf), aynı sonda.

### 3a. Düşme oranı

| koşu | tur | y.deneme ateşlenen | kurtarılan | düşen | oran |
|---|---|---|---|---|---|
| **taban (düzeltme öncesi)** | 21 | — | — | **7** | **%33,3** |
| A (sayaçsız) | 21 | — | — | 0 | %0 |
| B | 21 | 6 | 2 | 4 | %19,0 |
| C | 21 | 6 | 4 | 2 | %9,5 |
| **A+B+C toplam** | **63** | ≥12 | ≥6 | **6** | **%9,5** |

**Oran düştü.** Ama "düştü" demek yetmez — bir koşu sıfır düşme
gösterebilir çünkü hat o an iyidir, düzeltme iyi olduğu için değil. Bu
yüzden ham HTTP denemeleri ayrıca sayıldı:

- B ve C'de **27'şer ham deneme / 21 tur** → her koşuda **6 yeniden
  deneme ateşlendi**. Yani düzeltme fiilen çalıştı, koşu hattın iyi
  gününü ölçmüyor.
- 12 yeniden denemenin **6'sı turu kurtardı** (%50 kurtarma oranı).

**Tutarlılık kontrolü:** B+C'de ilk denemesi kopan tur 12/42 = **%28,6**
— tabandaki %33,3 ile aynı bantta. Yani hattın altta yatan kopma oranı
değişmedi; değişen şey kullanıcının gördüğü sonuç. Yeniden deneme
olmasaydı B+C %28,6 düşme gösterirdi; gösterdiği %14,3 oldu.

### 3b. BEDEL — kurtarılan turlar yavaş (kart bunu sormadı, ölçüldü)

| sınıf | düzeltme öncesi p50/p95 | **düzeltme sonrası p50/p95** |
|---|---|---|
| kısa olgusal | 978,9 / 1.400,4 ms | **1.033,6 / 1.573,3 ms** |
| proje durumu | 3.108,0 / 3.296,0 ms | **3.105,8 / 12.883,1 ms** |
| uzun anlatım | 6.483,3 / 7.003,6 ms | **6.703,4 / 7.311,9 ms** |

**p50 pratikte değişmedi** — ilk deneme başarılıysa hiçbir şey eklenmiyor.
**p95 kurtarılan turlarda patlıyor:** ilk deneme 12 s'de zaman aşımına
uğrayıp ikincisi başarılı olduğunda tur 13–16 saniye sürüyor (B koşusunda
uzun anlatım p95 = 16.229,7 ms).

Bu bir tercih, kusur değil: **kullanıcı artık daha seyrek llama duyuyor
ama bazen daha uzun bekliyor.** Ahmet'in bilmesi gereken takas budur.

Yerele düşen turların en kötü hâli **gerilemedi**: kopan tur artık
19,5 s (bulut bütçesi) + yerel üretim sürüyor; düzeltme öncesi 20 s +
yerel üretimdi. Ölçülen en uzun düşen tur 22.648 ms = 19,5 s + ~3,1 s
llama.

---

## 4. Mutasyon sınaması — 10/10

Düzeltme bellekte geri alındı, testin kırmızı yandığı görüldü.

| mutasyon | test | mutant |
|---|---|---|
| yeniden deneme kaldırıldı (tek deneme) | `..._ikinci_deneme_cevabi_getirir` | **KIRMIZI** |
| yeniden deneme kaldırıldı | `..._ucuncu_deneme_YOK` | **KIRMIZI** |
| yeniden deneme kaldırıldı | `..._butcesi_toplam_tavani_ASMAZ` | **KIRMIZI** |
| yeniden deneme kaldırıldı | `..._zaman_asimi_bolunmus_butcedir` | **KIRMIZI** |
| yeniden deneme kaldırıldı | `..._ajan_yerele_duser_ve_bildirir` | **KIRMIZI** |
| geçici/kalıcı ayrımı kaldırıldı | `test_kalici_hata_TEKRARLANMAZ` | **KIRMIZI** |
| bütçe bölünmedi (naif 20+20) | `..._zaman_asimi_bolunmus_butcedir` | **KIRMIZI** |
| bütçe bölünmedi (naif 20+20) | `..._butcesi_toplam_tavani_ASMAZ` | **KIRMIZI** |
| boş cevap hat hatası sayıldı | `test_bos_cevap_TEKRARLANMAZ` | **KIRMIZI** |
| son denemede redaksiyon kaldırıldı | `..._anahtar_...sizmaz` | **KIRMIZI** |

Her satırda temiz hâl yeşil, mutant kırmızı.

**Neden bu adım atlanamazdı:** sekiz testin **üçü** (401, boş cevap,
redaksiyon) düzeltme yazılmadan **önce de yeşildi** — çünkü yeniden deneme
hiç yokken çağrı sayısı zaten 1'di. O üç test ancak mutasyonla anlam
kazandı. Kartın uyarısı tam buydu.

---

## 5. Kartın §4'ü ile §5'i çelişiyor — nasıl çözdüm

- **§4:** *"DOKUNMA: ... `eval/` (orada başka bir oturum olabilir)"*
- **§5:** *"`agent/cloud_llm.py` ve `eval/run_turkish_quality.py`'nin
  **ikisinde de** 'bu politika ikizdir' notu var."*

İkisi aynı anda yapılamaz. §4'ün parantezi gerekçeyi veriyor: **başka bir
oturumun işini bozmamak.** Kontrol ettim — çalışma ağacı temizdi,
`eval/run_turkish_quality.py` üzerinde açık iş yoktu.

Çözüm: `eval/run_turkish_quality.py`'ye **yalnızca yorum satırı** eklendi,
tek bir mantık satırı değişmedi. Böylece §5'in DoD maddesi karşılandı ve
§4'ün asıl kaygısı (başkasının işini bozma) korundu. Aynı fikirde
değilsen tek satırlık geri alma.

Nota ayrıca **farkı** da yazdım: iki tarafın deneme SAYISI ve geri
çekilme süresi bilerek farklı (orada 3 deneme / 2 s, üretimde 2 deneme /
0,5 s) — çünkü orada kullanıcı beklemiyor, üretimde bekliyor. İkiz olan
şey *"hangi hata geçicidir"* kararı.

---

## 6. Sınırlara uyum

- `agent/local_agent.py` **DEĞİŞMEDİ.** `_BULUT_AG_HATASI` duyurusu aynen
  duruyor; kullanıcı hâlâ "hat koptu, yerele düştüm" diye duyuyor —
  yalnızca daha seyrek. `test_iki_deneme_de_koparsa_ajan_yerele_duser_ve_bildirir`
  bunu kilitliyor.
- `agents/persona.py`, `config/runtime_profiles.json`, kalite
  dedektörleri: dokunulmadı.
- `eval/`: yalnız yorum (§5).
- `DEFAULT_TIMEOUT_S = 20` büyümedi.
- `.env` okunmadı, yazılmadı.
- Push yok. Commit yok (§7).

## 7. Kapı

| kontrol | sonuç |
|---|---|
| `pytest tests -q` (alfabetik) | **1978 geçti / 0 başarısız / 2 xfail** |
| `pytest` (ters sıra) | **1978 geçti / 0 başarısız / 2 xfail** |
| `ruff check .` | **283** (tavan 283 — artmadı) |
| mutasyon | **10/10 kırmızı yandı** |

Taban 1970 → 1978 (8 yeni test).

## 8. Değişen dosyalar

| dosya | ne |
|---|---|
| `agent/cloud_llm.py` | `_gecici_ag_hatasi`, `_GECICI_HTTP_KODLARI`, `_deneme_butceleri`, yeniden deneme döngüsü; docstring düzeltildi |
| `eval/run_turkish_quality.py` | **yalnız yorum** — ikiz politika notu |
| `tests/test_ses_yolu_bulut_kapisi.py` | +8 test (13 → 21) |
| `automation/BULUT_YENIDEN_DENEME_2026-09-11.md` | bu rapor |
