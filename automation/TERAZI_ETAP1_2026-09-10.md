# ETAP 1 — Longform bütçesi: ölçümle seçildi

**Ölçen:** Claude Code · **Tarih:** 2026-09-10 · **Dal:** `auto/opencode-deepseek`
**Kart:** `automation/KART_TERAZI_ZINCIR.md` ETAP 1
**Kaynak kart:** `automation/KART_DEEPSEEK_10_KUSUR.md` PARÇA B (Ahmet imzalı, koşullu)

---

## 0. ÖNGÖRÜ — sayı görülmeden yazıldı

> **Bu bölüm 2026-09-10 00:39'da, hiçbir ölçüm koşulmadan önce yazıldı.**
> Aşağıdaki ölçüm dosyalarının damgası bu saatten sonradır; sıra
> doğrulanabilir. Kartın kuralı: *"Öngörüyü önce yaz, sonra sayıyı gör;
> tersini yaparsan sonuca göre hikâye kurmuş olursun."*

`llama3.1`'in ölçülmüş başlıca kusuru **tekrar/dejenerasyon** (49/64 tabanında
6 vaka). Bütçeyi büyütmek modele tekrar etmesi için **daha çok yer** verir.

**Öngörüm:**

1. **`llama3.1`'in puanı düşer.** En olası yer longform: bugün 1200 token
   duvarına çarparak kesiliyor ve kesilme dedektörü ceza yazıyor; duvar
   kalkınca kesilme cezası kalkacak ama modelin kendi durma noktası
   gelmezse yerini **tekrar cezası** alacak. Net etkinin **negatif ya da
   nötr** olmasını bekliyorum, pozitif değil.
2. **DeepSeek'in puanı yükselir.** Onun dört longform vakası da yalnız
   `length` ile kesildiği için düşüyordu; duvar kalkınca bu dört vakanın
   **en az ikisinin** geçmesini bekliyorum.
3. **İki modelin arası açılır.** 54 − 49 = 5 olan fark büyür.

Bu bir kestirimdir, hüküm değil. Ölçüm ne derse rapor onu yazar; öngörü
tutmazsa **tutmadığı yazılır**, öngörüye uydurulmaz.

---

## 1. Bütçe nasıl seçildi — tahminle değil, ölçümle

Kart açıktı: *"Tahminle yazma."* Önce modelin **kendi durduğu** noktayı
gördüm.

**Sonda:** dört longform vakası, DeepSeek, bütçe **4000** token. Sonda
repo'ya hiçbir şey yazmadı; `_http_json` sarılıp gerçek `usage` sayaçları
okundu, istek kurulumu ve yeniden deneme mantığı aynen kullanıldı.

| vaka | `done_reason` | karakter | çıkış tokeni | karakter/token |
|---|---|---|---|---|
| `t2_longform_001` | **stop** | 7.268 | **2.977** | 2,441 |
| `t2_longform_002` | **stop** | 3.903 | 1.557 | 2,507 |
| `t2_longform_003` | **stop** | 3.932 | 1.652 | 2,380 |
| `t2_longform_004` | **stop** | 3.834 | 1.697 | 2,259 |

Dördü de **kendiliğinden durdu.** En uzun cevap 2.977 token; 4000'lik
bütçenin 1.023 tokeni hiç kullanılmadı.

Türkçe token oranı bağımsız olarak doğrulandı: **2,26–2,51 karakter/token**,
ortalama ~2,40. Önceki ölçümün 2,39'u ile tutarlı.

### Seçilen sayı: 4000 — gerekçe

Üç gerekçe, sırayla:

1. **Doğrudan gözlendi.** 4000, dört vakanın da `stop` ile bittiği ölçülmüş
   değerdir. 3600 gibi bir sayı 2.977'nin üstünde kalırdı ama **koşulmadı**;
   ölçülmemiş bir sayıyı seçmek kartın yasakladığı tahmindir.
2. **Bütçe bir tavandır, tüketim değil.** `max_tokens`/`num_predict` üst
   sınırdır; model `stop` ile durduğunda kalan token ne üretilir ne
   faturalanır. 4000 ile 3600 arasındaki fark, modelin kendi durduğu
   koşullarda **sıfır** maliyet farkı demektir.
3. **Koşu-arası oynaklık payı.** Aynı vaka iki sondada 6.516 ve 7.268
   karakter üretti (temperature 0,2, yine de belirlenimci değil). En uzun
   gözlemin hemen üstüne sıkışmak, bir sonraki koşuda yine duvara çarpma
   riski taşır.

**Ölçülmeyen:** yerel `llama3.1`'in kendi durma noktası. Bu sonda yalnız
DeepSeek ile koşuldu. llama duvara çarpmaya devam ederse bu ETAP 2'de
`done_reason` sayısında görünecek.

## 2. Yapılan değişiklikler

- `eval/turkish_quality_cases.json` — dört longform vakasının bütçesi
  1200 → **4000**. Diğer 60 vaka **dokunulmadı** (bir test bunu koruyor).
- `passing_threshold` bloğuna **`olcum_tanimi`** eklendi: sayıların hangi
  bütçeyle ölçüldüğünü ve artık **eski tanım** olduğunu söylüyor.
  Eski sayılar (49/64 dahil) **silinmedi**; A14 gereği `">=N"` sözdizimi
  hâlâ yok ve bir test bunu koruyor.
- `CLAUDE.md` §13.2 — 49/64'ün geçmiş tanımın sayısı olduğu, gerekçesiyle
  yazıldı.
- `tests/test_quality_runner.py::test_only_longform_cases_declare_a_larger_budget`
  — beklenen bütçe 1200 → 4000. **Koruduğu sözleşme değişmedi** (bütçeyi
  yalnız longform beyan eder); değişen tek şey imzalı sayıdır ve imzanın
  yeri docstring'e yazıldı.

Test-first: `tests/test_longform_butcesi.py` beş test, ikisi kırmızı
görüldü (bütçe düşüktü, `olcum_tanimi` yoktu), üçü zaten geçerli olan
değişmezleri koruyordu.

## 3. Öngörü — henüz doğrulanmadı

§0'daki öngörü **ETAP 2'de** ölçülecek; ETAP 1 yalnız tanımı değiştirdi,
hiçbir puan koşmadı. Öngörü sayı görülmeden yazıldı ve bu dosyada
değiştirilmeden duruyor.

## 4. Kapı

```
pytest tests -q  alfabetik : 1955 geçti / 0 başarısız (2 xfail)
pytest tests -q  ters sıra : 1955 geçti / 0 başarısız (2 xfail)
ruff check .               : 283  (taban 283)
```

Zincir devam ediyor: kapı yeşil, BLOCKER yok, doğrulama kırmızısı yok.

## 5. Ara rapor (tek paragraf)

Longform bütçesi 1200'den 4000'e çıkarıldı ve sayı ölçümle seçildi: dört
vakanın dördü de 4000'de kendiliğinden durdu, en uzun cevap 2.977 çıkış
tokeni tuttu, yani eski 1200'lük duvar cevabın yarısını kesiyormuş. Eski
taban 49/64 silinmedi, "eski tanımın sayısı" olarak etiketlendi ve yeni
tanımdaki sayılarla karşılaştırılamaz. llama'nın puanının düşebileceğine
dair öngörü ölçümden önce yazıldı ve ETAP 2'de sınanacak. Kapı iki sırada
yeşil (1955), ruff 283 — zincir ETAP 2'ye devam ediyor.
