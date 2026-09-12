# KART — 400 token bütçesi: önce ölç, sonra seç (ETAP 1 deseni)

**Kime:** Claude Code (VS Code) · **Veren:** Ahmet, 2026-09-12
**Dal:** `auto/opencode-deepseek` · **Taban:** `d3487e5`
**Sınıf:** Ölçüm tanımı değişikliği — **Ahmet imzası gerekiyor** (§13.2).
Bu kart ölçümü yapar ve sayıyı **önerir**; bütçeyi değiştirmez.

---

## 0. Durum — ETAP 5'in CONCERN'ü bağımsız doğrulandı

`automation/TERAZI_ETAP5_2026-09-12.md` §5'in iddiası sınandı ve **doğru**:

| vaka | bütçe | çıkış tokeni | `done_reason` | sonuç |
|---|---|---|---|---|
| `t1_tr_001` | 400 | ~400 | `length` | `truncated` |
| `t1_tr_009` | 400 | ~400 | `length` | `truncated` |
| `t1_tr_013` | 400 | ~400 | `length` | `truncated` |

DeepSeek `turkish` 11/15; dört kaybın **üçü** duvardan. Yani terazi o
vakalarda cevabı değil **kesilmeyi** puanlıyor. Bu, ETAP 1'in longform'da
1200 için bulduğu kusurun aynı sınıfı.

## 1. DOĞRULARKEN ÇIKAN İKİNCİ BULGU — kartın asıl sebebi

Aynı ölçüm, ETAP 5 raporunda olmayan bir şey gösterdi. **400 bütçeli ve
kendiliğinden duran** (`done_reason="stop"`) en uzun cevaplar:

| sağlayıcı | en uzun 5 `stop` cevabı (çıkış tokeni) |
|---|---|
| **DeepSeek** | 370, 334, 239, 233, 232 |
| **llama3.1** | **502, 496, 464, 439, 378** |

llama 400 bütçeyle 502 token üretip `stop` ile bitiriyor. **Yani
`num_predict=400` llama tarafında tavan gibi davranmıyor.** DeepSeek'te ise
tavan sıkı: en uzun `stop` 370 ve üç vaka tam 400'de kesiliyor.

**Sonuç: aynı sayı iki sağlayıcıda aynı şeyi ifade etmiyor.** Bütçeyi
büyütmek DeepSeek'in duvarını kaldırır ama llama tarafındaki bu
tutarsızlığı açıklamaz — ve açıklanmadan iki modelin sayısı "aynı tanımla
ölçüldü" denemez.

> Bu bir **ölçüm aracı** kusuru olabilir (`raw_tps × total_s` kaba bir
> tahmindir) ya da gerçek bir sağlayıcı farkı. **Ayrılmadan bütçe
> seçilmez.** [EMİN DEĞİLİM]

---

## 2. Görev

### ADIM 1 — Token sayımını kesinleştir (önce bu)

`raw_tps × total_s` türetilmiş bir sayıdır. Sağlayıcının **kendi**
sayacını oku:

- DeepSeek: `usage.completion_tokens`
- Ollama: `eval_count`

llama'nın 502 token'lık cevabı gerçekten 502 mi, yoksa türetme hatası mı?
**Ölç ve yaz.** Gerçekse: `num_predict`'in Ollama'da nasıl uygulandığı
araştırılır ve bulgu yazılır — düzeltilmez, yazılır.

Bu adım tek başına kartın en önemli parçası: **iki sağlayıcının aynı
tanımla ölçüldüğü iddiası buna bağlı.**

### ADIM 2 — Sonda koşusu (ETAP 1 deseni, kanıtlanmış)

`automation/TERAZI_ETAP1_2026-09-10.md` §1'deki yöntem aynen uygulanır:

- Repoya hiçbir şey yazmayan bir sonda; `_http_json` sarılır, gerçek
  `usage` sayaçları okunur, istek kurulumu ve yeniden deneme mantığı
  aynen kullanılır.
- **400 bütçeli 60 vaka**, büyük bir bütçeyle (ör. 2000) **bir kez**
  koşulur. Amaç puan değil: her vakanın **kendiliğinden durduğu** uzunluğu
  görmek.
- `done_reason` dağılımı yazılır. Hâlâ `length` ile biten varsa bütçe
  daha da büyütülüp o vaka tekrar denenir — duvara çarpan bir vaka
  bırakılmaz.

**Her iki modelde de koşulur.** ETAP 1 yalnız DeepSeek ile koşmuştu ve
raporu bunu açıkça "ölçülmeyen" diye yazmıştı; o boşluk bu sefer
kapatılıyor.

### ADIM 3 — Sayıyı öner, uygulama

Rapora şunlar yazılır:

1. Her iki modelde en uzun `stop` cevabı (sağlayıcının kendi sayacıyla).
2. Önerilen bütçe ve **üç gerekçesi** — ETAP 1'in şablonu: doğrudan
   gözlendi mi, bütçe tavandır (kullanılmayan token maliyet değildir),
   koşu-arası oynaklık payı.
3. Türkçe karakter/token oranı (ETAP 1: 2,26–2,51, ortalama ~2,40) —
   tutarlı mı?

**`eval/turkish_quality_cases.json`'a ve `DEFAULT_NUM_PREDICT`'e
DOKUNMA.** Sayı Ahmet imzalayınca ayrı bir işte uygulanır.

---

## 3. Ahmet'in kararladığı üç şey (ETAP 5 §8'e cevap)

**S1 — Taban şimdi kaydedilsin mi? HAYIR.** DeepSeek `turkish` 11/15'in
üçü duvarın ürünü. Onu tabana yazmak, kartın kendi deyişiyle *"kusuru
betona gömmek"* olur. Taban bu kart bitip bütçe imzalandıktan **sonra**
bir kez kaydedilir.

**S2 — Bütçe ne olsun? ÖLÇÜLEREK seçilecek**, bu kart onu yapıyor.
Alternatif olarak önerilen *"`length` biten vakayı 'kaldı' değil
'ölçülemedi' say"* fikri **iyi ama şimdi değil**: o bir dedektör
değişikliğidir ve aynı anda iki değişken oynatmak, hangisinin ne yaptığını
ölçülemez kılar. Bütçe düzeldikten sonra ayrıca değerlendirilir.

**S3 — ETAP 6 başlasın mı? EVET.** Plumbing'dir, bu CONCERN'den
bağımsızdır, gerçek çağrı yapmaz. Bu kart bitince sıradaki iş odur.

---

## 4. Sınırlar

- `eval/turkish_quality_cases.json`, `DEFAULT_NUM_PREDICT`, dedektörler,
  `passing_threshold`: **DOKUNMA.** Bu kart ölçer ve önerir.
- Sonda repoya rapor dışında hiçbir şey yazmaz.
- `.env` okunmaz, yazılmaz (§9).
- Kapı: `pytest tests -q` **iki sırada**, `ruff check .` **≤ 283**.
- Maliyet: iki modelde birer sonda koşusu. DeepSeek tarafı birkaç sent.
- Push yok. Bitince **DUR**.

## 5. Bitti sayılma ölçütü

- ADIM 1: llama'nın 502 token iddiası sağlayıcının **kendi sayacıyla**
  doğrulandı ya da çürütüldü; sonuç yazılı.
- ADIM 2: iki modelde de sonda koşuldu; `done_reason` dağılımı yazılı;
  `length` ile biten vaka **kalmadı**.
- ADIM 3: önerilen bütçe üç gerekçeyle yazılı; karakter/token oranı
  ETAP 1'inkiyle karşılaştırılmış.
- Hiçbir yapılandırma dosyası değişmedi (`git diff` yalnız raporu
  gösteriyor).
- Kapı iki sırada yeşil, ruff ≤ 283.
