# Türkçe Model Kıyası — 2026-09-05 · üç model, düzeltilmiş terazi

**Kazanan ilan edilmedi. `config/runtime_profiles.json`'a dokunulmadı.
Puanlayıcıya dokunulmadı.** Bu belge kanıt üretir; `local_main` kararı
Ahmet'e aittir (CLAUDE.md §9, DANIŞMAN MODU).

Bu koşu, `docs/HARDWARE_AND_LOCAL_LLM_RESEARCH.md` §8'in **6. maddesini**
kapatır: *"Turkish-Gemma-9b GGUF'unu Türkçe kalite karşılaştırmasına sok."*

**Yöntem:** 64 vakalık takım, puanlayıcı 2026-09-05 sürümü (üç kusuru
düzeltilmiş hâli). Üç model aynı oturumda, arka arkaya; her modelden önce
diğerleri `keep_alive=0` ile **boşaltıldı** ve boş VRAM doğrulandı.
`temperature=0.2`, `num_ctx=4096`, `num_predict=400` (4 longform vakası 1200).

| | başlangıç | bitiş | süre |
|---|---|---|---|
| `llama3.1:latest` | 16:13:51 | 16:17:43 | 3 dk 52 sn |
| `alibayram/turkish-gemma-9b-v0.1` | 16:17:51 | 16:24:52 | 7 dk 01 sn |
| `RefinedNeuro/Turkcell-LLM-7b-v1` | 16:25:00 | 16:28:40 | 3 dk 40 sn |

Ham veri: `automation/KALITE_llama3.1_latest_20260905-1617.{json,md}`,
`automation/KALITE_alibayram_turkish-gemma-9b-v0.1_20260905-1624.{json,md}`,
`automation/KALITE_RefinedNeuro_Turkcell-LLM-7b-v1_20260905-1628.{json,md}`.

---

## 0. Hangi paketi ölçtük — şablon doğrulaması

Kartın en büyük uyarısı buydu: yanlış sohbet şablonu iyi modeli kötü gösterir.

**Resmî `ytu-ce-cosmos` GGUF'u alınamadı.** İki deneme, iki farklı hata:

```
hf.co/ytu-ce-cosmos/Turkish-Gemma-9b-v0.1-GGUF
  -> Error: realm host "huggingface.co" does not match original host "hf.co"
hf.co/ytu-ce-cosmos/Turkish-Gemma-9b-v0.1
  -> Error: 400 Repository is not GGUF or is not compatible with llama.cpp
```

İkincisi temel (safetensors) deposu — beklenen. Birincisi büyük olasılıkla
kapılı (gated) depo ya da Ollama 0.33.2'nin yönlendirme kusuru; **ayırt
edemedim.** Bu yüzden kartın kendi işaret ettiği topluluk aynasına geçildi ve
şablonu doğrulandı.

| | Turkish-Gemma | Turkcell-LLM |
|---|---|---|
| Paket | `alibayram/turkish-gemma-9b-v0.1:latest` | `RefinedNeuro/Turkcell-LLM-7b-v1:latest` |
| Digest | `c51ed67b59a4` | `50f61cb255fa` |
| Boyut / kuantizasyon | 5,8 GB · Q4_K_M | 4,5 GB · Q4_K_M |
| Mimari | `gemma2`, 9,2B, ctx 8192 | `llama`, 7,4B, ctx 32768 |

```
# alibayram/turkish-gemma-9b-v0.1
TEMPLATE "<start_of_turn>user
{{ if .System }}{{ .System }} {{ end }}{{ .Prompt }}<end_of_turn>
<start_of_turn>model
{{ .Response }}<end_of_turn>"
PARAMETER stop <start_of_turn>
PARAMETER stop <end_of_turn>

# RefinedNeuro/Turkcell-LLM-7b-v1
TEMPLATE "{{- if .System }}
<|im_start|>system {{ .System }}<|im_end|>
{{- end }}
<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant"
PARAMETER stop <|im_start|>
PARAMETER stop <|im_end|>
```

**Doğrulama, iki yoldan:**

1. **Biçimsel.** Gemma şablonu, Gemma-2'nin kanonik biçimidir
   (`<start_of_turn>` / `<end_of_turn>`); sistem rolünün kullanıcı turuna
   katlanması Gemma'da standarttır — Gemma'nın ayrı bir system rolü yoktur.
   Turkcell ChatML kullanıyor ve `<|im_start|>`/`<|im_end|>` **stop
   token'ları şablonuyla tutarlı**. 7,4B parametre / 4096 gömme, Mistral-7B
   tabanı + **genişletilmiş** kelime dağarcığıyla uyumlu (temel Mistral
   7,24B) — kartın tokenizer iddiasını yapısal olarak destekliyor.
2. **Deneysel** — asıl kanıt. Üç kısa Türkçe soru, iki modele:
   hiçbir cevapta şablon artığı yok (`<|im_start|>`, `<start_of_turn>`,
   `[INST]` aranmış, bulunmamış) ve **kısa cevaplar `done_reason=stop` ile
   bitiyor**. Şablon/stop eşleşmesi yanlış olsaydı model durma token'ını
   üretemez, `length` ile kesilir ve devam artıkları görünürdü.

Şablonlar doğrulandı; ölçüm bu temelde yapıldı.

---

## 1. Kategori kategori

| Kategori | `llama3.1` | `Turkish-Gemma-9b` | `Turkcell-LLM-7b` |
|---|---|---|---|
| tone (20) | 19 | 19 | 19 |
| turkish (15) | 10 | 12 | **13** |
| technical (10) | 6 | **9** | 6 |
| mixed (5) | 3 | **5** | 4 |
| memory (5) | **5** | **5** | 1 |
| grounding (5) | **5** | 3 | 0 |
| longform (4) | 1 | 1 | **3** |
| **toplam (64)** | **49** | **54** | **46** |

Üç modelde de düşen vaka sayısı 2. Ayrışma büyük: yalnız llama'da düşen 8,
yalnız Gemma'da 4, yalnız Turkcell'de 9 vaka.

## 2. Neden dağılımı

| Neden | `llama3.1` | `Turkish-Gemma` | `Turkcell` |
|---|---|---|---|
| sistem prompt'u sızıntısı | 7 | 3 | **0** |
| tekrar (3×, puanlanan) | 6 | **0** | 4 |
| kesilme | 2 | 3 | 4 |
| uydurma (`grounding`) | 3 | 3 | 9 |
| hafızayı kullanamama (`contains`) | **0** | **0** | 4 |
| yapay zekâ kalıbı | **0** | 2 | 1 |
| İngilizce cümle | 1\* | **0** | **0** |
| bozuk kodlama | 0 | 0 | 0 |

\* Ölçülmüş yanlış pozitif — §6'ya bakınız.

Raporlanan, puanlanmayan sinyaller:

| | `llama3.1` | `Turkish-Gemma` | `Turkcell` |
|---|---|---|---|
| tekrar 2× | 7 | **0** | 6 |
| yabancı kelime | 1 | 2 | **0** |
| "Efendim" hitabı | 21/64 | **25/64** | **0/64** |

## 3. Hız

| Ölçüm | `llama3.1` | `Turkish-Gemma` | `Turkcell` |
|---|---|---|---|
| Ham tok/s | 78,8 | **32,3** | **83,5** |
| İlk token | 30,5 ms | **420,8 ms** | **28,1 ms** |
| Ortalama yanıt | 3,47 s | 6,39 s | **3,30 s** |
| Toplam koşu | 222 s | 409 s | **211 s** |
| Ortalama cevap | 335 karakter | 384 karakter | 368 karakter |

Gemma **2,4 kat yavaş** ve ilk token'ı **13,8 kat geç** veriyor. Sesli
asistanda ilk token gecikmesi doğrudan hissedilir; 420 ms tek başına
PUSULA'daki ~1,5 saniyelik hedefin dörtte birini yer.

### Turkcell'in tokenizer iddiası — ölçüldü, kısmen tuttu

Kart bu iddianın burada sınanacağını yazmıştı. Rapordaki "Türkçe-eşdeğer
tok/s" bunu **ölçmez**: puanlayıcı `TURKISH_TOKENIZER_PENALTY = 1.9`
sabitini üç modele de aynı uygular. Gerçek ölçüm, aynı Türkçe metnin her
modelde kaç token ettiğidir (`prompt_eval_count`, dört farklı metin):

| Metin türü | `llama3.1` | `Turkish-Gemma` | `Turkcell` |
|---|---|---|---|
| uzun teknik | 3,38 kar/token | 3,22 | **3,43** |
| günlük konuşma | 2,58 | 2,74 | **3,11** |
| eklemeli yığın | 3,00 | 2,87 | **3,14** |
| kurumsal | 3,00 | 3,00 | 2,93 |
| **toplam** | **3,005** | 2,975 (−1,0%) | **3,179 (+5,8%)** |

**İddia gerçek ama küçük.** Turkcell aynı Türkçe metni %5,8 daha az tokenle
işliyor; en büyük kazanç günlük konuşmada (%20), teknik metinde neredeyse
yok. Bu, `1.9` katsayısının tarif ettiği cezayı **kaldırmıyor**, kenarından
kırpıyor. Ham hız avantajıyla birleşince (%6) Türkçe iş başına toplam
kazanç llama3.1'e göre kabaca **%12**.

> **Kayda geçsin:** `TURKISH_TOKENIZER_PENALTY` tek bir sabit olduğu için
> rapordaki "Türkçe-eşdeğer tok/s" sütunu modeller arası tokenizer farkını
> **gizler**. Bugünkü sayılar (41,5 / 17,0 / 43,9) yalnız ham hızın 1,9'a
> bölünmüş hâlidir. Puanlayıcı bu kartta donmuş durumda; düzeltmek ayrı bir
> karar.

## 4. VRAM — açık ucun cevabı

Masaüstü yükü **751 MB** (hiçbir model yüklü değilken ölçüldü). Tepe değer
koşu boyunca **saniyede bir** örneklendi; koşucunun kendi `peak_vram_mb`'si
yalnız vaka sonrası örnek alır, ikisi de yazıldı.

| | `llama3.1` | `Turkish-Gemma` | `Turkcell` |
|---|---|---|---|
| Ollama'nın modele verdiği | 5027 MB | 5506 MB | 4771 MB |
| Isıtma sonrası toplam | 5944 MB | 7001 MB | 5716 MB |
| **Örneklenmiş tepe (masaüstü dahil)** | **6003 MB** | **7076 MB** | **6026 MB** |
| Koşucunun bildirdiği tepe | 5968 MB | 7078 MB | 6026 MB |
| Masaüstü çıkarılınca (~751 MB) | 5252 MB | 6325 MB | 5275 MB |
| **6144 MB tavanını aşıyor mu** | **hayır** | **EVET** | **hayır** |

**Açık uç kapandı: 1200 token'lık longform bütçesi tavanı aşmıyor.**
Önceki turda görülen 6275 MB kirli koşulun eseriydi ([EMİN DEĞİLİM] diye
işaretlenmişti, doğru işaretlenmiş). Temiz ölçümde llama3.1'in tepesi
**6003 MB** — tavanın 141 MB altında. Turkcell de altında (6026 MB).

**Turkish-Gemma tavanın üstünde: 7076 MB.** Masaüstü yükü çıkarılsa bile
6325 MB. Ölçülen bedeli tabloda görünüyor: 2,4 kat yavaş üretim, 13,8 kat
geç ilk token — `mistral-nemo`'da ölçülen örüntünün aynısı
(`docs/HARDWARE_AND_LOCAL_LLM_RESEARCH.md` §3). Gemma'nın kalite
üstünlüğünün faturası budur.

## 5. `done_reason` dağılımı

| | `stop` | `length` (bütçe bitti) | bütçeden kesilen |
|---|---|---|---|
| `llama3.1` | 62 | 2 | 2 |
| `Turkish-Gemma` | 62 | 2 | 2 |
| `Turkcell` | 61 | 3 | 3 |

Üç modelde de kesilmelerin **hepsi** bütçe kaynaklı — hiçbiri kendi
cümlesini yarıda bırakmıyor. 1200 token'lık longform bütçesi işini gördü:
64 vakada yalnız 2–3 cevap sınıra çarpıyor (düzeltme öncesi bu sayı tek
başına longform'da 4/4'tü).

## 6. Ölçümün söylemediği şeyler

**a) Yeni ölçülmüş yanlış pozitif: `FOREIGN_RUN_WORDS = 6` bir şarkı adını
yakaladı.** llama3.1 `t1_tone_014`'te (AC/DC önerisi) *"you shook me all
night long"* yazdı — altı kelimelik bir **şarkı adı**, İngilizce cümle
sızıntısı değil. Eşik 192 cevap üzerinde ölçülmüştü ve o veride en uzun
meşru İngilizce dizi 3 kelimeydi; 6 kelimelik bir özel isim ilk kez çıktı.
llama3.1'e **bir vakaya** mal oldu (49 yerine 50 olurdu). Puanlayıcı bu
kartta dondurulmuş olduğu için düzeltilmedi; `AHMET_ONAYI_BEKLEYENLER.md`
→ **A15**.

**b) Turkcell'in `grounding 0/5`'i uydurmayı abartıyor.** Beş cevabın
yalnız **biri** gerçek uydurma (`t2_grounding_004`: *"Kardeşinizin doğum
günü 25 Aralık'ta"*). Üçü bağlam istiyor (*"lütfen bana daha fazla bağlam
sağlayın"*), biri soruyu geri soruyor (*"Dün akşam bana ne önerdin?"*).
"Bağlam iste" ne itiraftır ne uydurma; puanlayıcı onu uydurma sayıyor.
Yine de **davranış kusurlu**: model kayıt yokluğunu söylemiyor, topu
kullanıcıya atıyor. Aynı örüntü hafızada da var — `t2_memory_001`'e cevabı
*"Eşinizin adı nedir?"*, oysa eşin adı zemin bloğunda **verilmişti**.

**c) Gemma uyduruyor ama etiketleyerek.** İki zemin kusurunun ikisi de
`[VARSAYIM]` ile başlıyor ve *"olabilir"* diyor
(`t2_grounding_005`: *"[VARSAYIM] … projeniz 'ESHOT'ta polimer bazlı ısı
yalıtım malzemesi testleri' olabilir"*). Persona'nın *"Emin olmadığın her
yere [VARSAYIM] koy"* kuralına uyuyor, ama yine de olmayan bir içerik
üretiyor. Puanlayıcı için ikisi aynı; kulak için değil. Ahmet'in
değerlendirmesine bırakılıyor.

**d) Turkcell persona'nın dışında.** 64 cevabın **hiçbirinde** "Efendim"
yok (llama 21, Gemma 25) ve `t2_memory_005`'te *"**Ailemde** 2 büyükanne…"*
diyerek kullanıcının ailesini kendine mal ediyor. Sistem prompt'unu hiç
sızdırmaması (0) bu tabloda bir erdem değil, prompt'u pek de
umursamadığının işareti olabilir. [EMİN DEĞİLİM]

**e) Tek koşu hüküm değildir.** A11 hâlâ açık; aşağıdaki sapmaya bakınız.

## 7. A11 — üçüncü oynaklık verisi

`llama3.1`, dün (09-04) ve bugün (09-05), aynı puanlayıcıyla:

| | 09-04 | 09-05 |
|---|---|---|
| Toplam | 48/64 | 49/64 |
| Yalnız o gün düşen | `t1_tone_013`, `t1_tone_015`, `t2_grounding_003`, `t2_longform_002` | `t1_tone_014`, `t1_tr_005`, `t1_tr_013` |
| İkisinde de düşen | 12 | 12 |

**Toplam yine ±1, ama 7 vaka yer değiştirdi (%11).** Bunun **biri**
açıklanabilir: `t2_longform_002` dün 400 token bütçesine çarpıp kesilmişti,
bugün 1200 ile bitirdi — düzeltmenin eseri, oynaklık değil. Kalan **6 vaka
saf oynaklık**; önceki ölçümde bu sayı 3'tü.

Birikmiş üç ölçüm: toplam **±1 vaka** (%1,6) oynuyor, düşen vakaların
kimliği **3–6 vaka** (%5–9) oynuyor. Sonuç değişmiyor: toplamdaki 1-2
puanlık fark regresyon kanıtı değildir; kategori ve neden bazlı iddialar
tek koşuda kırılgandır.

## 8. Takaslar — karar Ahmet'in

Üç model üç ayrı yerde iyi; hiçbiri her yerde iyi değil.

| | `llama3.1` (mevcut) | `Turkish-Gemma-9b` | `Turkcell-LLM-7b` |
|---|---|---|---|
| Toplam puan | 49 | **54** | 46 |
| Uydurmama + verilen hafızayı kullanma | **5/5 + 5/5** | 3/5 + 5/5 | 0/5 + 1/5 |
| Teknik / karışık | 6 + 3 | **9 + 5** | 6 + 4 |
| Metin dejenerasyonu (tekrar) | 6 | **0** | 4 |
| Prompt sızdırma | 7 | 3 | **0** |
| Persona ("Efendim") | 21/64 | **25/64** | 0/64 |
| Hız (ilk token) | 30,5 ms | 420,8 ms | **28,1 ms** |
| VRAM tavanı | altında | **ÜSTÜNDE** | altında |
| Türkçe tokenizer verimi | temel | −1,0% | **+5,8%** |

Kabaca: **Gemma en yüksek puanı alıyor ama tavanı aşıyor ve 13,8 kat geç
başlıyor**; **llama3.1 zeminde en güvenilir olanı** (uydurma 3, hafıza 5/5,
zemin 5/5) ama en çok tekrar eden ve en çok prompt sızdıran; **Turkcell en
hızlısı ve tokenizer'ı gerçekten daha verimli** ama persona'nın tamamen
dışında ve hafıza/zemin ekseninde kullanılamaz durumda.

Bu üç eksenin nasıl tartılacağı — özellikle "sesli asistanda 420 ms ilk
token kabul edilebilir mi" ve "tavanı aşan model kalıcı olarak çalıştırılır
mı" — ölçüm değil **karar**. `config/runtime_profiles.json` değiştirilmedi.

## 9. Kapsam

- `config/runtime_profiles.json` — **değiştirilmedi**.
- Puanlayıcı, eşikler, vaka metinleri — **değiştirilmedi**. Üç koşu da aynı
  puanlayıcıyı kullandı. `test_the_recorded_run_still_scores_49_of_64`
  hâlâ 49 diyor.
- Turkish-Gemma **T1 değil, v0.1** ölçüldü (kart gereği: T1'in düşünme
  blokları bütçeyi yer).
- `mistral-nemo` ve `llama3.2` bu turda ölçülmedi (kart üç model istedi).
