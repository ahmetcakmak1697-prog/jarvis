# ETAP 2 — Taban yeni tanımla tazelendi · ZİNCİR BURADA DURDU

**Ölçen:** Claude Code · **Tarih:** 2026-09-10 · **Dal:** `auto/opencode-deepseek`
**Kart:** `automation/KART_TERAZI_ZINCIR.md` ETAP 2
**Ham veri:** `automation/KALITE_deepseek_deepseek-chat_20260910-0053.json`,
`automation/KALITE_llama3.1_latest_20260910-0103.json`

---

## 0. ZİNCİR DURDU — sebep

> **ETAP 3'e geçilmedi.** Kartın kuralı: *"Beklenmedik bir şey çıkarsa dur —
> ör. bir kategori 2+ vaka oynarsa, sebebini yaz ve Ahmet'e sor."*

İki koşul birden gerçekleşti:

1. **`prompt_leak` dedektörü yanlış alarm veriyor ve bütçe artışı bunu
   görünür hâle getirdi.** DeepSeek'in dört longform vakasının **dördü de**
   bu yüzden düşüyor. llama'nın biri de.
2. **DeepSeek `technical` kategorisi 9'dan 7'ye düştü** (2 vaka), biri ağ
   ölümü biri bilinen zemin kusuru.

Dedektörlere dokunmak bu kartın **açık yasağı** (*"Kalite eşikleri ve
dedektörler değişmez"*), ve düzeltme muhtemelen `agents/persona.py`'ye
dokunmayı gerektiriyor — orada Codex var, karta göre **dur ve söyle**.

**Bu yüzden ETAP 3 başlatılmadı.** Karar Ahmet'in.

---

## 1. Dört sayı yan yana

> **UYARI: eski ve yeni tanım karşılaştırılamaz.** Farklı ölçüm tanımıdır;
> aynı modelin iki sayısı yan yana konabilir ama biri diğerinin
> "iyileşmesi/gerilemesi" değildir.

Temiz karşılaştırma **aynı persona + aynı gün** koşuları arasındadır. 2026-09-09'da
Codex persona'yı değiştirdi (PARÇA A); onun öncesindeki sayılar iki değişkeni
birden taşır.

| model | ESKİ tanım (1200) | YENİ tanım (4000) | fark |
|---|---|---|---|
| `llama3.1:latest` | **50/64** (2026-09-09 23:42) | **52/64** (2026-09-10 01:03) | +2 |
| `deepseek/deepseek-chat` | **56/64** (2026-09-09 23:44) | **53/64** (2026-09-10 00:53) | −3 |

Daha eski kayıtlar, tanımlarıyla birlikte (silinmedi):

| | sayı | tanım |
|---|---|---|
| llama3.1 | 49/64 | 1200 token, 2026-09-03 puanlama, **persona öncesi** |
| deepseek | 54/64 | 1200 token, 2026-09-09 22:08, **persona öncesi** |

**56'yı taban ilan etmedim** (kartın açık talimatı). Yeni tanımdaki sayılar
53 ve 52; ikisi de **tek koşudur** ve A11'in oynaklık zarfı içinde okunmalıdır.

---

## 2. Öngörü ne oldu — **TUTMADI**

§0'da (`TERAZI_ETAP1_2026-09-10.md`) sayı görülmeden şunu yazmıştım:

| öngörü | gerçekleşen | sonuç |
|---|---|---|
| llama'nın puanı **düşer** (negatif ya da nötr) | **52/64, +2 yükseldi** | ❌ **YANLIŞ** |
| DeepSeek'in puanı **yükselir**, 4 longform'un en az 2'si geçer | **53/64, −3 düştü; longform 0/4 kaldı** | ❌ **YANLIŞ** |
| İki modelin arası **açılır** (5'ten büyür) | 56−50 = 6 iken 53−52 = **1'e daraldı** | ❌ **YANLIŞ** |

Üçü de yanlış. Öngörüyü yeniden yazmıyorum; yanlış olduğu böyle duruyor.

**Ama mekanizma göründü.** Öngörünün dayanağı şuydu: *"bütçeyi büyütmek
llama'ya tekrar etmek için daha çok yer verir."* Bu **gerçekleşti**:

- `t2_longform_003`, llama: eski tanımda `stop`, 2.001 karakter.
  Yeni tanımda **`length`, 14.307 karakter** — yani 4000 token duvarına
  tekrar ede ede çarptı. Karakter sayısı **7 katına** çıktı.

Puana yansımadı çünkü o vaka zaten `repetition` ile düşüyordu; ceza iki kez
yazılmıyor. Yani **mekanizma doğruydu, sonuç tahminim yanlıştı** — ve ikisini
ayırmak gerekiyor, çünkü mekanizma bir sonraki bütçe kararında geri gelecek.

Puanı yukarı taşıyan iki vaka bütçeyle ilgili değildi:
`t1_tech_002` (önceki koşuda **ağ ölümü**) ve `t1_tone_013`.

---

## 3. Bütçe değişikliği ne yaptı — hedeflenen kısmı çalıştı

**Kesilme bitti.** DeepSeek'in dört longform vakası eski tanımda dördü de
`done_reason="length"` ile kesiliyordu; yeni tanımda dördü de `"stop"`:

| vaka | eski (1200) | yeni (4000) |
|---|---|---|
| `t2_longform_001` | `length`, 2.926 kar, `truncated` | `stop`, 6.173 kar, **`prompt_leak`** |
| `t2_longform_002` | `length`, 3.084 kar, `truncated` | `stop`, 4.733 kar, **`prompt_leak`** |
| `t2_longform_003` | `length`, 2.854 kar, `truncated` | `stop`, 5.603 kar, **`prompt_leak`** |
| `t2_longform_004` | `length`, 2.682 kar, `truncated` | `stop`, 4.050 kar, **`prompt_leak`** |

Kabul ölçütünün birinci yarısı sağlandı: **kesilme yok.** İkinci yarısı
sağlanmadı: longform **0/4 kaldı**, ama sebebi değişti.

---

## 4. CONCERN — `prompt_leak` dedektörü talimata uymayı sızıntı sayıyor

Bu bulgunun tamamı ölçümdür, çıkarım değil.

`agents/persona.py:147` şu talimatı veriyor:

```
7. Risk, test ve geri alma yolunu ayrı bir maddede belirt
```

`eval/quality_scorer.py` sızıntı korpusunu **talimat metninden n-gram
çıkararak** kuruyor (`_instruction_ngrams()`), yani `"risk test ve"`,
`"test ve geri"`, `"ve geri alma"` üçlüleri sızıntı listesinde.

Model talimata **uyuyor** ve cevabına şu başlığı yazıyor:

```
### 6. Risk, Test ve Geri Alma Yolu
```

Dedektör bunu **prompt sızıntısı** olarak puanlıyor. Yakalanan n-gram'lar
tam olarak bunlar:

| vaka | `prompt_leak_hits` |
|---|---|
| `t2_longform_001` | `['ve geri alma']` |
| `t2_longform_002` | `['ve geri alma']` |
| `t2_longform_003` | `['risk test ve', 'test ve geri', 've geri alma']` |
| `t2_longform_004` | `['risk test ve', 'test ve geri', 've geri alma']` |
| `t2_grounding_005` | `['ve geri alma']` |
| `t2_longform_004` (llama) | `prompt_leak` |

**Neden şimdi göründü:** 1200 token duvarı cevabı 6. maddeye varmadan
kesiyordu. Duvar kalkınca model bölümü yazabildi ve dedektör ateşledi.
Yani bu kusur **yeni değil**, bütçe onu **görünür yaptı**.

Bu, 2026-09-05'te kapatılan hatanın **aynı sınıfı**: o zaman sızıntı
korpusundan persona'nın tırnaklı örnekleri çıkarılmıştı
(`TERAZI_DUZELTMELERI_2026-09-05.md`). Şimdi aynı şey bir **talimat
cümlesi** ile oluyor.

### Neden dokunmadım

- Kart: *"Kalite eşikleri ve dedektörler **değişmez.**"*
- Kart: *"`agents/persona.py`'ye **dokunma.** Codex aynı anda orada."*
- Olası düzeltmelerin ikisi de bu iki yasaktan birine giriyor: ya korpustan
  bu n-gram'lar çıkarılacak (dedektör değişikliği) ya da talimat yeniden
  yazılacak (persona).

**[EMİN DEĞİLİM]** Hangi düzeltmenin doğru olduğunu ölçmedim. Korpustan
çıkarmak sızıntı kapsamını daraltır; talimatı yeniden yazmak modelin çıktı
biçimini değiştirir ve iki modeli birden etkiler. İkisi de taban oynatır.

---

## 5. Diğer hareketler — hangisi gürültü

DeepSeek, eski → yeni tanım:

| vaka | kategori | ne oldu | değerlendirme |
|---|---|---|---|
| `t1_tr_014` | turkish | düzeldi | — |
| `t1_tech_002` | technical | **`empty`** — `RemoteDisconnected` | **ağ ölümü, kalite değil** |
| `t1_tech_004` | technical | `grounding` | bilinen kusur (10-kusur listesinde) |
| `t1_tr_003` | turkish | `boilerplate` | oynak |
| `t2_grounding_005` | grounding | **`prompt_leak`** | §4'teki aynı yanlış alarm |

`technical` 9 → 7 hareketinin **biri ağ**, biri bilinen model kusuru. Yani
kategori gerçekten 2 oynadı ama ikisi de bütçe değişikliğiyle ilgisiz.

llama tarafında bozulan vaka **yok**; iki vaka düzeldi.

---

## 6. Kapı

```
pytest tests -q  alfabetik : 1955 geçti / 0 başarısız (2 xfail)
pytest tests -q  ters sıra : 1955 geçti / 0 başarısız (2 xfail)
ruff check .               : 283  (taban 283)
```

Kapı yeşil. Zincirin durma sebebi kapı değil, **§4'teki CONCERN**.

---

## 7. Ahmet'e sorular

1. **`prompt_leak` yanlış alarmı nasıl kapatılsın?** Korpustan talimat
   n-gram'larını çıkarmak mı, talimatı yeniden yazmak mı? İkisi de tabanı
   oynatır ve ikisi de bu kartın yasakları içinde.
2. **Yeni taban 53/52 olarak kaydedilsin mi**, yoksa §4 düzeltildikten
   sonra mı? Şu an `passing_threshold` bloğu ESKİ tanımın sayılarını
   taşıyor ve "yeni taban ETAP 2'de ölçülecek" diyor — o cümle şu an
   ödenmemiş bir söz.
3. **ETAP 3 (çok sağlayıcı) başlasın mı?** Plumbing işidir ve §4'ten
   bağımsızdır; ama zincir kuralı gereği kendiliğinden başlatmadım.

## 8. Ara rapor (tek paragraf)

Yeni bütçeyle iki model de koşuldu: llama3.1 50 → **52/64**, DeepSeek
56 → **53/64** (aynı persona, aynı gün; eski ve yeni tanım karşılaştırılamaz
ve 56 taban ilan edilmedi). Bütçe değişikliğinin hedeflediği kısım çalıştı —
DeepSeek'in dört longform vakası artık kesilmiyor, dördü de `stop` ile
bitiyor. Ama longform yine 0/4: kesilme cezasının yerini **`prompt_leak`
yanlış alarmı** aldı, çünkü persona *"Risk, test ve geri alma yolunu ayrı
bir maddede belirt"* diyor ve dedektör talimat n-gram'larını sızıntı
korpusuna koyuyor — model talimata uyunca sızıntı sayılıyor. Bu, 1200
duvarının gizlediği eski bir kusur. Öngörümün üçü de tutmadı (llama düştü
sanıyordum, yükseldi), ama öngörünün mekanizması göründü: llama bir longform
vakasında 4000 duvarına tekrar ede ede çarpıp 14.307 karakter üretti. Kapı
iki sırada yeşil; **zincir ETAP 3'e geçmeden burada durdu** çünkü düzeltme
ya dedektöre ya persona'ya dokunmayı gerektiriyor ve ikisi de kartın yasağı.
