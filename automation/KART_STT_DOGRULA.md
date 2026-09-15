# KART — `small`/5 + `hotwords`'ü üretime almadan önce iki eksik

**Kime:** Claude Code (VS Code) · **Veren:** Ahmet, 2026-09-16
**Dal:** `auto/opencode-deepseek` · **Taban:** `cbaac97`
**Sınıf:** Ölçüm. **Hiçbir varsayılan değişmez** — bu kart uygulamaz, sınar.

---

## 0. Neden — öneri güçlü ama kanıtı dar

`automation/STT_HOTWORDS_2026-09-15.md` ölçtü: `small`/5 + `hotwords`,
mevcut üretim ayarına göre **13 → 4 hata**, düzelen 5 cümle, **bozulan
sıfır**, maliyet +45 ms. PUSULA cümlesi ("Hey Jarvis, nerede kaldık?")
yalnız bu bileşimde duyuldu — beam 5 tek başına da, `hotwords` tek başına
da düzeltmiyor.

Raporun kendi hükmü: **n = 1.** Bir konuşmacı, bir okuma, bir kayıt. Ve
raporun kendi işaret ettiği iki ölçülmemiş risk:

1. **"Hey Jarvis" tek okuma.** Bir kez doğru duyulması, sistematik olarak
   doğru duyulacağı anlamına gelmez.
2. **Gürültü-yalnız klipte sızıntı ölçülmedi.** `voice/stt.py:410-414`'ün
   kendi yorumu Whisper'ın **saf sessizliğe metin uydurduğunu** yazıyor
   (*"Bu dizinin betimlemesi, Yeni Gizem…"*). `vad_filter=True` saf
   sessizliği kesiyor — ama **VAD'den geçen gürültü** için bilinmiyor. Bir
   ipucu listesi verildiğinde model o kelimeleri gürültüye kusarsa, JARVIS
   sen konuşmadan "Jarvis DeepSeek Ollama commit klima" duyar.

**İkinci risk asimetriktir.** Kazanç ölçüldü ve geri alınabilir bir
varsayılan; bu risk ise **canlıda ortaya çıkana kadar görünmez** ve yeni
bir hata sınıfı yaratır. Bu yüzden uygulamadan önce ölçülür.

## 1. Ölçülmüş taban — bu kartın karşılaştıracağı sayılar

| ayar | hata / 76 | "Hey Jarvis" | p50 ms |
|---|---|---|---|
| `small`/1 (**mevcut üretim**) | 13 | Heyecan mısın? (2) | ~956 |
| `small`/5 (ipucusuz) | 10 | Heyecan mısın? (2) | ~994 |
| **`small`/5 + `hotwords`** | **4** | **Hey Jarvis (0)** | ~1001 |

`hotwords` = `Jarvis DeepSeek Ollama commit klima`

> **Mutlak ms oturumlar arası kararsız** (aynı kayıtlarda dün 1252, bugün
> 956; sebebi ölçülmedi). Süre karşılaştırması **yalnız koşu içinde**
> yapılır. Bu kartın konusu süre değil zaten.

---

## 2. Görev

### ADIM 0 — Ahmet kaydeder (ön koşul, DUR ve iste)

Sondaya yeni bir alt komut gerekiyor: `dogrula`. İki tür kayıt alır.

**A — uyandırma cümlesi, çok okuma.** Aynı cümle (*"Hey Jarvis, nerede
kaldık?"*) **8–10 kez**. Ahmet'ten doğal çeşitlilik istenir ve her kaydın
hangi koşulda alındığı **etikete yazılır**: normal, hızlı, yavaş,
mikrofondan biraz uzak, cümle başında duraklayarak. Amaç aynı okumayı
kopyalamak değil, **gerçek kullanımın yayılımını** örneklemek.

**B — gürültü-yalnız klipler, 3 adet, ~10 sn.** Ahmet **hiç konuşmaz**:
(1) sessiz oda, (2) klavye/fare sesi, (3) arka planda konuşma ya da müzik
(TV, Discord, Spotify — ne varsa). Bu klipler `vad_filter`'ın neyi
geçirdiğini sınar.

> **Kayıtlar Ahmet'in sesi ve evinin sesi. Repoya GİRMEZ.** `kaydet`'teki
> `--cikti` deseni izlenir; varsayılan `%TEMP%` altında, repo dışında.
> Raporda yalnız **metin** ve sayı yer alır.

### ADIM 1 — `dogrula` alt komutu

`ipucu` alt komutunun desenini izle; **yeni bir ölçüm yolu yazma, mevcut
`_yaziya`'yı kullan.** İpucusuz çağrının üretimle birebir aynı kalması
(`{language, beam_size, vad_filter=True}`, `None` bile geçilmez) zaten
testle kilitli — o kilidi bozma.

`ipucu`'nun **çıktı dosyası sabit** (`olcum_ipucu.json`); `dogrula` kendi
dosyasına yazsın (`olcum_dogrula.json`) ve **önceki ham ölçümlerin hiçbirine
dokunmasın**. `--kayit` ve `--cikti` ikisi de olsun.

### ADIM 2 — Uyandırma cümlesi: kaç okumada doğru

Her okuma için üç satır, aynı koşuda:

| ayar | ipucu |
|---|---|
| `small`/1 | yok (**mevcut üretim**) |
| `small`/5 | yok |
| `small`/5 | `hotwords` |

Rapor **N/N olarak** yazar: "`small`/5 + `hotwords` 10 okumanın 9'unda
*Hey Jarvis* duydu; 1'inde *…*". Kaçırdığı okumaların **etiketi** yazılır
(hızlı mıydı, uzak mıydı) — hangi koşulda bozulduğu, kaç kez bozulduğundan
daha bilgilendirici.

Toplam WER **yazma**; burada ölçülen tek şey o cümlenin duyulup
duyulmadığı.

### ADIM 3 — Sızıntı: gürültüye ne kusuyor

Üç gürültü klibi, **ipuçlu ve ipucusuz**, `vad_filter=True` (kapatma):

| klip | `small`/5 ipucusuz | `small`/5 + `hotwords` |
|---|---|---|
| sessiz oda | çıktı metni | çıktı metni |
| klavye | | |
| arka plan konuşma | | |

Rapor **ham çıktı metnini aynen** yazar — boşsa "boş" yazar, özetlemez.
Sonra iki soru:

1. İpuçlu satırda **ipucu kelimelerinden biri** göründü mü? (`Jarvis`,
   `DeepSeek`, `Ollama`, `commit`, `klima`)
2. İpucusuz satırda görünmeyip ipuçlu satırda görünen bir şey var mı? Yani
   uydurma **ipucu yüzünden mi arttı**, yoksa zaten var mıydı?

İkinci soru kritik: Whisper ipucusuz da uyduruyor. Ölçülen şey **ipucunun
farkı**, uydurmanın varlığı değil.

### ADIM 4 — Hüküm (uygulama yok)

Üç sonuçtan biri, açıkça:

- **Geçti** — uyandırma cümlesi okumaların büyük çoğunluğunda doğru ve
  ipucu kelimesi hiçbir gürültü klibinde çıkmadı. → Uygulama kartı
  yazılabilir.
- **Kaldı** — ipucu kelimesi gürültüde çıktı. → `hotwords` üretime
  **alınmaz**; `beam_size` ayrı değerlendirilir (o tek başına sızıntı
  riski taşımıyor).
- **Belirsiz** — arada. Ne eksik olduğu ve **hangi ölçümün** kapatacağı
  yazılır. Tahmin yürütülmez.

Hangi sonuç çıkarsa çıksın: **hiçbir şey uygulanmaz.** Uygulama ayrı bir
kart ve Ahmet'in imzası.

---

## 3. Ölçüm hijyeni

- Ölçüm sırasında makine boş olsun; başka komut çalıştırma.
- **İki PID çekişme değildir** — `.venv\Scripts\python.exe` bir başlatıcıdır
  ve gerçek yorumlayıcıyı alt süreç olarak açar. `ParentProcessId` oku.
  (`FAILURES.md`, 2026-09-14.)
- Mutlak süreler oturumlar arası kararsız; bu kart süre karşılaştırması
  yapmıyor, yapma.

## 4. Sınırlar

- `voice/stt.py`'de **hiçbir varsayılan değişmez.** `vad_filter` hiçbir
  yolda kapanmaz.
- `olcum.json` ve `olcum_ipucu.json`'a **dokunulmaz.**
- `medium` ölçülmez (bütçeyle elendi).
- İpucu listesi büyütülmez — bu kart aynı beş kelimeyi sınar. Cihaz
  adlarıyla genişletmek ayrı bir ölçüm.
- `agent/`, `eval/`, `agents/persona.py`, `voice/`: dokunma.
- Kapı: `pytest tests -q` **iki sırada**, `ruff check .` **≤ 283**.
- Push yok. ADIM 0 Ahmet'in kaydını gerektirir — **orada DUR ve iste.**

## 5. Bitti sayılma ölçütü

- `dogrula` alt komutu var; ipucusuz çağrının üretimle eşliği hâlâ testli.
- Uyandırma cümlesi **N/N olarak** yazılı, kaçıranların etiketi belirtilmiş.
- Üç gürültü klibinin **ham çıktı metni** raporda, ipuçlu ve ipucusuz.
- Sızıntı sorusu ikisi de cevaplanmış (ipucu kelimesi çıktı mı; ipucu
  farkı yarattı mı).
- ADIM 4 hükmü üç seçenekten biri olarak açıkça yazılı.
- Hiçbir varsayılan değişmedi; önceki ham ölçümler dokunulmamış.
- Kapı iki sırada yeşil, ruff ≤ 283.
