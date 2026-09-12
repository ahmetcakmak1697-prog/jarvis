# KART — 2000 bütçesini uygula ve tabanı kaydet (ödenmemiş sözü öde)

**Kime:** Claude Code (VS Code) · **Veren:** Ahmet, 2026-09-13
**Dal:** `auto/opencode-deepseek` · **Taban:** `a692d87`
**Sınıf:** Ölçüm tanımı değişikliği — **Ahmet imzaladı** (2026-09-13),
gerekçesi `automation/TERAZI_400_SONDA_2026-09-12.md` ölçümüdür.

> **SIRA UYARISI:** Önce `automation/KART_LOCALHOST_2SN.md` yapılsın.
> O kart vaka başına ~2 saniye kazandırıyor ve bu kartta **iki model ×
> 60 vaka** koşulacak. Önce yapılırsa bu koşu ~4 dakika kısalır.

---

## 0. Sonda ne ölçtü

`TERAZI_400_SONDA_2026-09-12.md` (bütçe 2000, iki model, 60 vaka):

- **120 cevabın 119'u kendi kendine durdu.**
- En uzun doğal cevaplar: **llama 644**, **DeepSeek 462** token — ikisi de
  400'ün üstünde. Yani 400 gerçekten dar.
- Tek istisna: llama `t1_mix_002`. Model sahte bir süreç tablosunu satır
  satır sayarak 2000'e kadar gitti. 3000 bütçeyle yeniden koşulunca
  **139 token'da** durdu.

**Ve benim "502 token" bulgum çürüdü:** o sayı `raw_tps × total_s`
türetmesiydi ve `localhost` gecikmesiyle şişmişti. Ollama'nın kendi
`eval_count` sayacı hiçbir vakada 400'ü geçmemiş. **400, llama'da da
gerçek bir tavan.** Kayda geçsin: ölçülmemiş bir formüle güvendim.

## 1. Seçilen sayı: 2000 — üç gerekçe

ETAP 1'in şablonu, aynen:

1. **Gerçekten koşulan sayı bu.** 1000 de 644'ün üstünde kalırdı ama
   koşulmadı; seçmek tahmin olurdu.
2. **Tavan normal cevapların maliyetini değiştirmiyor.** Medyan cevap
   uzunluğu iki bütçede de aynı: DeepSeek 67, llama ~20 token. Bedel
   yalnız bozuk cevaplarda süre olarak ödeniyor (dejenere bir llama
   cevabı ~26 saniye sürüyor, 400 bütçede ~5 saniyeydi).
3. **Koşudan koşuya oynamaya pay bırakıyor.** Aynı vaka iki kat
   uzayabiliyor (llama 307→644); 2000, görülen en uzun cevabın ~3,1 katı.

**Bilinen risk, kayda geçsin:** `t1_mix_002` 2000'de yine duvara
çarpabilir. Çarparsa bu bir bütçe kusuru değil, **tekrar dedektörünün
kör noktasıdır** — numaralı sayma döngülerini görmüyor. Ayrı bir madde
olarak kuyruğa yazılsın, bu kartta çözülmesin.

## 2. Claude'un üçüncü sorusu — ÖLÇÜLDÜ, ek iş gerekmiyor

Soru: *"llama'nın longform'da bağlam penceresini aşması taban
kaydedilmeden önce ölçülsün mü?"*

Ölçüldü (danışman Claude, 2026-09-13), ETAP 5 koşusunun kendi verisinden:

| model | longform çıktıları | `done_reason` |
|---|---|---|
| llama3.1 | 2.471 – 3.279 karakter (~1.000 token) | dördü de `stop` |
| deepseek | 4.512 – 7.733 karakter | dördü de `stop` |

llama 4000 bütçenin yalnız **dörtte birini** kullanıyor. Prompt ~1.050 +
çıkış ~1.000 = ~2.050 token, `num_ctx=4096`'nın **altında**. Endişe
aritmetik olarak geçerliydi (4000+1050 > 4096) ama **tetiklenmiyor.**

Ve llama'nın longform kaybının sebebi pencere değil: dördünün **üçü**
`repetition`. Bu, `CLAUDE.md` §7.0'ın *"yerelin kusurları modelin
tavanı"* bulgusuyla birebir aynı.

`num_ctx = 4096` üç yerde **kodda sabit**
(`agent/local_agent.py:924`, `eval/run_turkish_quality.py:526`,
`scripts/olc_llm_anatomisi.py:99`) — profilden gelmiyor. Bu kartta
**dokunulmuyor**; bilinsin diye yazıldı.

## 3. Görev

### ADIM 1 — Bütçeyi uygula

400 bütçeli 60 vakanın bütçesi **2000** olur. Longform'un 4000'i
**değişmez** (ETAP 1'de ayrıca ölçülmüştü).

Nereye yazılacağı senin ölçümüne bağlı: `DEFAULT_NUM_PREDICT` mi,
vaka dosyasındaki alan mı — hangisi daha az yeri değiştiriyorsa o
(§3 cerrahi). Seçimini gerekçesiyle yaz.

### ADIM 2 — İki modeli de koştur

`llama3.1:latest` ve `deepseek/deepseek-chat`, yeni bütçeyle, tam 64 vaka.

`done_reason` dağılımı yazılır. **`length` ile biten vaka kaldıysa
adıyla listelenir** — `t1_mix_002` beklenen istisnadır, başkası varsa
DUR ve söyle.

### ADIM 3 — Tabanı kaydet (ödenmemiş söz)

`eval/turkish_quality_cases.json` → `passing_threshold` şu an hâlâ
**eski tanımın** sayılarını taşıyor (49/64, turkish 13/15, longform 0/4)
ve şunu diyor: *"Yeni tanimdaki taban ETAP 2'de olculecek."*

O söz iki kez ertelendi (ETAP 2 durdu, ETAP 5 durdu). **Şimdi ödenecek.**

- A14: **hedef yazılmaz**, taban kaydı yazılır. `">=N"` sözdizimi yasak.
- Eski sayılar **silinmez**; tanımlarıyla yanlarında durur.
- `olcum_tanimi` bloğu güncellenir: `num_predict` **ve** dedektör
  sürümü **ve** `localhost` düzeltmesinin yapılıp yapılmadığı.
- `CLAUDE.md` §13.2'deki kalite tabanı cümlesi güncellenir.
- **Tek koşu hüküm değildir** (A11) uyarısı korunur.

### ADIM 4 — ETAP 6'ya not

Karakter/token oranı **iki model arasında taşınamıyor**: DeepSeek 2,41
(ETAP 1'deki ~2,40 ile tutarlı), llama ~3,2–3,3. `KART_TERAZI_COK_SAGLAYICI`
içindeki `--tahmin` bayrağı tek bir oran kullanamaz — sağlayıcı başına
oran ister. Bunu o kartın ilgili maddesine **not olarak ekle**, uygulama.

## 4. Sınırlar

- Longform bütçesi (4000), `num_ctx`, dedektörler: **dokunma.**
- `t1_mix_002`'nin tekrar dedektörü kör noktası: **kuyruğa yaz, çözme.**
- Park edilmiş cepheler: dokunma (§9).
- Kapı: `pytest tests -q` **iki sırada**, `ruff check .` **≤ 283**.
- Maliyet: DeepSeek tarafında bir tam koşu (~60 çağrı).
- Push yok. ADIM 3 bitince **DUR**; ETAP 6 ayrı bir iştir.

## 5. Bitti sayılma ölçütü

- Bütçe 2000 uygulandı; nereye yazıldığı gerekçeli.
- İki model de koşuldu; `done_reason` dağılımı yazılı; `length` ile
  biten vaka varsa adıyla listeli.
- `passing_threshold` **gerçek sayıları** taşıyor; "ETAP 2'de ölçülecek"
  sözü artık yok; eski sayılar tanımlarıyla duruyor.
- `olcum_tanimi` üç değişkeni de içeriyor (bütçe, dedektör, localhost).
- `CLAUDE.md` §13.2 güncel.
- `t1_mix_002` kör noktası kuyruğa yazıldı.
- Karakter/token notu ETAP 6 kartına eklendi.
- Kapı iki sırada yeşil, ruff ≤ 283.
