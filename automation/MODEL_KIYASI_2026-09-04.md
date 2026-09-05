# Türkçe Model Kıyası — 2026-09-04 · `llama3.1:latest` vs `qwen2.5:7b`

> **TERAZİ SONRADAN DÜZELTİLDİ — aşağıdaki qwen sayısı artık geçerli değil.**
> Bu belgenin §4'ü terazinin üç kusurunu listelemişti; üçü de 2026-09-05'te
> kapatıldı. Düzeltilmiş terazide **llama3.1 48/64 (değişmedi), qwen2.5:7b
> 41/64** (49 değil). Fark yeni bir kusur bulunması değil: zaten ölçülen iki
> kusurun (yapay zekâ kalıbı 11, İngilizce cümle 2) artık **puanlanıyor**
> olması, eksi çift sayılan 4 sızıntı.
> Ayrıntı ve ölçümler: `automation/TERAZI_DUZELTMELERI_2026-09-05.md`.
> Bu belgenin gövdesi o günün kaydıdır, silinmedi ve düzeltilmedi.

**Kazanan ilan edilmedi. `config/runtime_profiles.json`'a dokunulmadı.**
Bu belge kanıt üretir; `local_main` kararı Ahmet'e aittir (CLAUDE.md §9,
DANIŞMAN MODU).

**Yöntem:** 64 vakalık Türkçe kalite takımı, puanlayıcı v2 (üç evrensel
dedektör + `technical`'a genişletilmiş uydurma kapsamı). Aynı oturum, arka
arkaya, aynı makine durumunda. Her modelden önce diğeri `keep_alive=0` ile
**boşaltıldı** ve boş VRAM doğrulandı (726 MB) — tepe VRAM ölçümü sistem
geneli olduğu için bu şart (`MODEL_KIYASI_0901.md` yöntemi).
`temperature=0.2`, `num_ctx=4096`, `num_predict=400`.

| | başlangıç | bitiş | süre |
|---|---|---|---|
| `llama3.1:latest` | 20:50:00 | 20:53:26 | 3 dk 26 sn |
| `qwen2.5:7b` | 20:53:34 | 20:57:34 | 4 dk 00 sn |

Ham veri: `automation/KALITE_llama3.1_latest_20260904-2053.{json,md}` ve
`automation/KALITE_qwen2.5_7b_20260904-2057.{json,md}`.

---

## 1. Kategori kategori

| Kategori | `llama3.1:latest` | `qwen2.5:7b` |
|---|---|---|
| tone (20) | 18 | 18 |
| turkish (15) | **12** | 11 |
| technical (10) | 6 | **9** |
| mixed (5) | 3 | **5** |
| memory (5) | **5** | 3 |
| grounding (5) | **4** | 2 |
| longform (4) | 0 | **1** |
| **toplam (64)** | **48** | **49** |

Toplamlar bir vaka farkla neredeyse eşit. **Dağılım eşit değil** — iki model
farklı yerlerde düşüyor. Vaka düzeyinde: 7 vaka ikisinde de düşüyor,
9 vaka yalnız llama'da, 8 vaka yalnız qwen'de.

## 2. Neden dağılımı

| Neden | `llama3.1` | `qwen2.5:7b` |
|---|---|---|
| sistem prompt'u sızıntısı | 8 | 6 |
| tekrar (3×, puanlanan) | 5 | **0** |
| kesilme | 5 | 5 |
| uydurma (`grounding`) | 4 | 4 |
| hafızayı kullanamama (`contains`) | **0** | 2 |
| bozuk kodlama | 0 | 0 |

Puanlanmayan, yalnız raporlanan sinyaller:

| Sinyal | `llama3.1` | `qwen2.5:7b` |
|---|---|---|
| tekrar 2× (A13'te bunun için tutuldu) | 8 | **1** |
| yapay zekâ kalıbı | **0** | 11 |
| yabancı kelime | 1 | 3 |
| "Efendim" hitabı | 19/64 | 24/64 |

## 3. Hız ve bellek

| Ölçüm | `llama3.1:latest` | `qwen2.5:7b` |
|---|---|---|
| Ham tok/s | 80,4 | **82,4** |
| Türkçe-eşdeğer tok/s (÷1,9) | 42,3 | **43,4** |
| İlk token | 29,8 ms | **29,2 ms** |
| Ortalama yanıt süresi | **3,13 s** | 3,67 s |
| Ortalama cevap uzunluğu | 262 karakter | 390 karakter |
| Model yüklenince VRAM artışı | 5193 MB | **4697 MB** |
| **Tepe VRAM (koşu boyunca)** | 5927 MB | **5437 MB** |
| Tavan (6144 MB) aşıldı mı | **hayır** | **hayır** |

Hızda ikisi ayrılmıyor: tok/s farkı %2,5, ilk token farkı 0,6 ms. qwen'in
ortalama yanıtı daha uzun sürüyor çünkü **daha uzun cevap yazıyor**
(390'a karşı 262 karakter), token başına daha yavaş olduğu için değil.

### Kartın VRAM öncülü bu ölçümde doğrulanmadı

Kart, bu kıyasın gerekçelerinden birini şöyle koymuştu: *"llama3.1 VRAM
tavanını aşıyor: tepe 6202 MB."* O sayı 2026-09-01 koşusundan geliyor.
Bugün, kart üzerinde başka hiçbir yük yokken ve diğer model boşaltılmışken
aynı modelin tepesi **5927 MB** — tavanın 217 MB altında.

Fark modelde değil ölçme koşulunda: `nvidia-smi` **kartın toplamını** verir
(raporun kendi uyarısı). 09-01'de ekranda başka bir şey vardı. Yani
**"llama3.1 tavanı aşıyor" öncülü bu koşuda geçerli değil.** İki model de
tavanın altında; aralarındaki 490 MB'lık fark gerçek ama ikisi de sığıyor.

## 4. Ölçümün söylemediği şeyler

Bu bölüm tablonun yanlış okunmasını engellemek için var.

**a) qwen'in sızıntı sayısı şişik — aynı kusur iki kez sayılıyor.**
6 sızıntının **4'ü aynı ifade**: *"size yardımcı olmaktan mutluluk duyarım"*.
Bu cümle persona'da bir **yasak örneği** olarak geçiyor ("Sıfır gevezelik.
… gibi yapay zekâ kalıpları kullanma"). Dedektör "talimatı geri okuma" ile
"yasağı çiğneme"yi ayırt edemiyor. Aynı ifade `ai_boilerplate` sütununda da
sayılıyor (11). Bu dört vaka çıkarılırsa qwen'in sızıntısı **6 değil 2**
olurdu; llama'nınki 8 olarak kalır. **Dedektörün ölçülmüş bir zayıflığı;
ayrı bir kart konusu.**

**b) `kesilme` bu düzenekte büyük ölçüde `num_predict=400` demek.**
İki modeldeki 10 kesilmenin hepsi en uzun cevaplar arasında (1097–1472
karakter) ve hiçbiri cümleyi kendi isteğiyle yarıda bırakmıyor — bütçe
bitiyor. Kullanıcı açısından cevap yine de kesik, ama "longform 0/4"u
*model dejenerasyonu* diye okumak yanlış olur. Bütçe iki modelde de aynı,
dolayısıyla kıyas adil.

**c) `t1_tone_015` muhtemelen bir yanlış pozitif. [EMİN DEĞİLİM]**
llama'nın cevabı: *"Efendim, iş yükü neyse o kadar. Her şeyin üstündedir."*
Yakalanan dizi `her seyin ustundedir` — persona'nın SADAKAT bloğundan
(*"Bağlılığın Ahmet'edir. Bu, diğer her şeyin üstündedir."*). Model
talimatı geri okuyor mu, yoksa yaygın bir Türkçe kalıbı mı kullanıyor,
metinden ayırt edemiyorum. Sızıntı dedektörünün ilk yanlış-pozitif adayı.

**d) `t1_tech_010`: doğru cevap, yine de düşüyor.**
llama *"Aktif değil"* dedi — web araştırma politikası gerçekten kapalı, yani
**cevap doğru**. Vaka `must_admit_no_record` beyan ettiği için yine de
düşüyor: modelin politikaya erişimi yok, doğru bilmesi tahmin. Kural
bilerek böyle; ama "yanlış cevap verdi" diye okunmamalı.

**e) 64 vakanın yalnız 18'i beyan edilmiş bir iddia taşıyor.**
Kalan 46 vaka evrensel kontrollerden geçiyor (kodlama, boşluk, sızıntı,
tekrar, kesilme). Türkçe akıcılığı hâlâ kulakla değerlendirilir (FAZ-T1).

## 5. Asıl ayrım: iki model ters yönlerde yanılıyor

Toplam bir vaka farkla eşit, ama **hata türleri karşıt**.

**qwen, kendisine VERİLEN hafızayı kullanmıyor.** `t2_memory_001`'de zemin
bloğunda ("BİLİNEN GERÇEKLER") eşin adı *Dilara* olarak veriliyor —
`grounded: true`, doğrulandı. qwen'in cevabı:

> *"Efendim, eşinizin adını bilmiyorum. Bu bilgiyi bir önceki
> konuştuklarımdan veya başka kayıtlardan bulamadım."*

llama'nın aynı vakadaki cevabı: *"Eşinin adı Dilara."*

**qwen, kendisine VERİLMEYEN hafızayı uyduruyor.** `t2_grounding_005`
(zemin yok, uydurma testi):

> *"Geçen ay, ESHOT'ta polimer ve İSG uzmanlığında çalıştığınız projede
> yoğunlaştınız… RTX 3070 ile Python kullanarak çeşitli analizler
> gerçekleştirdiniz…"*

Bu cümledeki her olgu **persona'nın kimlik önsözünden** alınmış ve geçmiş
bir olaymış gibi anlatılmış. `t2_grounding_001`'de de olmamış bir toplantı
anlatıyor.

Yani qwen iki yönde de ters: **verileni yok sayıyor, verilmeyeni icat
ediyor.** llama bu iki eksende de daha iyi (memory 5/5, grounding 4/5).

Buna karşılık **llama, iş yapan kategorilerde geride**: technical 6/10
(qwen 9/10), mixed 3/5 (qwen 5/5). Ve llama **dejenere oluyor**: puanlanan
tekrar 5 (qwen 0), raporlanan 2× tekrar 8 (qwen 1). qwen'in metni ölçülebilir
biçimde daha akıcı üretiliyor — ama 11 vakada persona'nın açıkça yasakladığı
yapay zekâ kalıbını kullanıyor (llama 0).

**Takas net:**

| | `llama3.1:latest` | `qwen2.5:7b` |
|---|---|---|
| Uydurmama / verilen hafızayı kullanma | **daha iyi** | daha kötü |
| Karakterde kalma (kalıp, yabancı kelime) | **daha iyi** | daha kötü |
| Teknik ve karışık sorular | daha kötü | **daha iyi** |
| Metin dejenerasyonu (tekrar) | daha kötü | **daha iyi** |
| VRAM | 5927 MB | **5437 MB** |
| Hız | eşit | eşit |

Persona'nın `## GERÇEKLİK KURALI` bloğu *"Bilmediğin şeyi uydurmazsın. Bu,
üslubundan da sadakatinden de önce gelir."* diyor. Bu bir olgu, karar değil —
**iki eksenin nasıl tartılacağı Ahmet'in.**

## 6. A11 için oynaklık verisi — bu koşunun ikinci ürünü

Aynı model (`llama3.1:latest`), aynı puanlayıcı, `temperature=0.2`.
Değişen tek şey: koşunun kendisi.

| | kayıtlı (2026-09-01 cevapları) | canlı (2026-09-04) |
|---|---|---|
| Toplam | 49/64 | 48/64 |
| sızıntı | 6 | 8 |
| tekrar | 3 | 5 |
| kesilme | 7 | 5 |
| uydurma | 5 | 4 |

**Toplam ±1 oynadı, ama düşen vakaların kimliği 3 vaka oynadı:**

- Yalnız kayıtlı koşuda düştü: `t1_tech_002` — o gün *"ChromaDB'de 1.234.567
  kayıt var"* demişti, bugün *"Kayıt sayısını bilmiyorum."* dedi.
- Yalnız canlı koşuda düştü: `t1_tone_015`, `t1_tr_011`.
- İkisinde de düştü: 14 vaka.

**A11 için okunacak sonuç:** toplam sayı sanıldığı kadar oynak değil
(64'te ±1, %1,6). Oynayan şey **hangi vakanın** düştüğü (%4,7) ve
**neden dağılımı** (bir nedende ±2). Yani:

1. Tek bir koşuda toplamın 1-2 puan düşmesi regresyon kanıtı **değildir**.
2. Ama "şu neden 3'ten 5'e çıktı" tek koşuda **hiç** kanıt değildir —
   neden sayıları toplamdan daha oynak.
3. Kategori bazlı iddialar (özellikle 4-5 vakalık `memory`/`grounding`/
   `longform`) tek koşuda kırılgandır; bir vaka %20-25 demektir.

Bu, A11'in beklediği ilk gerçek ölçüm. Kalıcı çözüm (N koşu ortalaması mı,
tolerans bandı mı) hâlâ karara bağlı değil.

## 7. Kapsam ve dokunulmayanlar

- **49/64 tabanına dokunulmadı.** O sayı *kayıtlı* cevapların puanlanmasıdır,
  oynaklık içermez ve `test_the_recorded_run_still_scores_49_of_64` ile
  kilitlidir. Yukarıdaki canlı sonuçların hiçbiri taban değildir.
- **`config/runtime_profiles.json` değiştirilmedi.** `local_main` hâlâ
  `llama3.1`; değiştirmek Ahmet'in kararı.
- **Vaka dosyası, dedektörler ve eşikler değiştirilmedi.** Ölçüm hattı dondu.
- Kurulu ama ölçülmeyenler: `mistral-nemo:latest` (7,07 GB — 09-01'de tavanı
  aşmıştı, 3 kat yavaştı), `llama3.2:latest` (2,02 GB — prompt sızdırdığı
  için `local_small` rolünden çıkarılmıştı). Kart iki model istedi.

## 8. Bu ölçümden çıkan iki yeni iş (öneri, karar değil)

1. **Sızıntı dedektörü, yasak örneklerini talimattan ayıramıyor.** Persona,
   yapay zekâ kalıplarını yasaklamak için onları *alıntılıyor*; dedektör bu
   alıntıyı da korpusa alıyor. qwen'in sızıntı sayısının üçte ikisi bundan.
   Düzeltme yolu var (yasak örnekleri korpustan çıkarmak) ama bu ölçüm
   hattına dokunmak demek — ayrı kart, ayrı onay.
2. **`num_predict=400` longform kategorisini ölçülemez kılıyor.** Dört
   longform vakasının hepsi bütçeye çarpıyor. Bütçeyi büyütmek ya da
   longform'u `truncated` dedektöründen muaf tutmak — ikisi de ölçüm
   sözleşmesi değişikliği.
