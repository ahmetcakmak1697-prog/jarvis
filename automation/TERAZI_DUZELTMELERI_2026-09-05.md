# Terazinin üç kusuru kapatıldı — 2026-09-05

**Kaynak kart:** `automation/KART_terazi_duzeltmeleri.md`
**Karar:** Ahmet, 2026-09-05 — `local_main` **llama3.1'de kalır**, önce ölçüm düzelir.
**Değişen:** ölçüm hattı. **Değişmeyen:** model, persona, vaka metinleri,
`config/runtime_profiles.json`.

Kusurları kıyas koşusunun kendi raporu listelemişti
(`automation/MODEL_KIYASI_2026-09-04.md` §4). Bu belge onların kapanışını ve
**ölçülmüş** etkilerini kaydeder.

---

## Baş sonuç: taban 49/64 **kıpırdamadı**

Kart, kusur 1 ve 3'ün kayıtlı cevapların puanını değiştireceğini ve tabanın
yeniden kurulması gerekeceğini öngörüyordu. **Ölçüm bunu doğrulamadı.**

`llama3.1` kayıtlı koşusu (2026-09-01 cevapları), düzeltmelerden önce ve
sonra, vaka vaka aynı:

| | önce | sonra |
|---|---|---|
| Toplam | 49/64 | **49/64** |
| tone / turkish / technical | 19/20 · 13/15 · 5/10 | aynı |
| mixed / memory / grounding / longform | 3/5 · 5/5 · 4/5 · 0/4 | aynı |
| Neden dağılımı | sızıntı 6 · tekrar 3 · kesilme 7 · uydurma 5 | aynı |

Sebebi tesadüf değil, ölçülebilir:

- **Kusur 1** (tırnaklı örnekler korpustan çıktı) llama'nın 6 sızıntısının
  hiçbirine dokunmadı — altısı da tırnaksız **talimat** metninden geliyordu.
  Çıkan 4 vakanın hepsi qwen'deydi.
- **Kusur 3** (kalıp + yabancı puanlanır) kayıtlı llama koşusunda hiçbir şeyi
  düşürmedi: o koşuda **0** yapay zekâ kalıbı ve **0** İngilizce cümle var.
- **Kusur 2** zaten kayıtlı cevapları etkilemiyor (yalnız gelecek koşuları).

Yani düzeltmeler cerrahiydi: hedefledikleri kusurları vurdular, tabanı değil.
`test_the_recorded_run_still_scores_49_of_64` **değiştirilmedi ve geçiyor** —
bu, kartın istediğinden daha iyi bir sonuç: sayıyı yeniden kurmak gerekmedi.

---

## Kusur 1 — sızıntı dedektörü iki farklı şeyi karıştırıyordu

**Kural:** persona'nın talimat metnindeki **tırnaklı parçalar** korpustan
çıkarılır. Ölçüldü: talimat bölümünde 13 tırnaklı parça var ve **hiçbiri
talimat değil** — üçü de örnektir:

| tür | örnek | modelin yapması gereken |
|---|---|---|
| yasak kalıbı | *"Size yardımcı olmaktan mutluluk duyarım"* | kurmamak |
| söylenmesi istenen | *"bu konuşmanın kaydına erişimim yok"* | **kurmak** |
| üslup örneği | *"Efendim, hesaplarıma göre…"* | kurabilmek |

Bunları sızıntı saymak iki hata üretiyordu. Birincisi kartın gördüğü:
qwen'in 6 "sızıntısının" 4'ü tek bir yasak kalıptı ve aynı kusur
`ai_boilerplate` sütununda ikinci kez sayılıyordu.

İkincisi kartın görmediği ve daha sinsi olanı: persona modele *"bu
konuşmanın kaydına erişimim yok" de* diyor. Model **doğru davranıp** bunu
deseydi sızıntı yiyecekti — hem de tam `grounding` kategorisinde, yani en
çok önemsediğimiz yerde. Bu, `expect_efendim` hatasının aynısıydı ve henüz
patlamamıştı. Test artık kilitliyor:
`test_a_phrase_the_persona_tells_jarvis_to_say_is_not_a_leak`.

**Ölçülen etki (3 koşu, 192 cevap):**

| koşu | önce | sonra |
|---|---|---|
| llama kayıtlı | 6 | **6** |
| llama canlı | 8 | **8** |
| qwen canlı | 6 | **2** |

Çıkan dört vakanın (`t1_tone_010`, `t1_tone_013`, `t1_tr_010`, `t1_tr_015`)
eşleşmesi aynı ifadeydi. Kusur kaybolmadı, **yer değiştirdi**: dördü de
`ai_boilerplate` sayacında duruyor ve artık orada puanlanıyor.

Uygulama: `_QUOTED_EXAMPLE` tırnaklı parçayı **silmez, ayırıcıyla değiştirir**
— silseydi tırnağın iki yanındaki kelimeler birleşip persona'da hiç geçmeyen
bir dizi üretirdi.

---

## Kusur 2 — kesilmelerin hepsi bütçeydi, model kararı değil

**2a — sebep artık ölçüm.** Ollama'nın `done_reason` alanı sonuç JSON'una ve
rapora yazılıyor: `length` = bütçe bitti, `stop` = model kendi durdu. Rapor
kesilmeleri ikiye ayırıyor.

**2b — uzun anlatım hak ettiği bütçeyi alıyor.** `num_predict` artık vaka
başına: varsayılan **400**, yalnız 4 `longform` vakası **1200**. Diğer 60
vakanın koşulu hiç değişmedi (CLAUDE.md §3).

**Canlı doğrulama** (llama3.1, `--category longform`, 2026-09-05 15:46):

| vaka | bütçe | done_reason | uzunluk | kesik mi |
|---|---|---|---|---|
| t2_longform_001 | 1200 | `stop` | 2562 | hayır |
| t2_longform_002 | 1200 | `stop` | 2019 | hayır |
| t2_longform_003 | 1200 | `stop` | 2343 | hayır |
| t2_longform_004 | 1200 | `stop` | 2082 | hayır |

**4/4 kesilme → 0/4.** Dördü de artık cümlesini bitiriyor. Kategori 0/4'ten
1/4'e çıktı ve kalan üç düşüş **gerçek** kusur: `longform_001` ve `_004`
tekrar, `longform_002` sızıntı. Ölçüm artık modeli ölçüyor, bütçeyi değil.

> **Not, doğrulanmadı:** bu duman testinde tepe VRAM **6275 MB** göründü —
> 6144 MB tavanın üstünde. Ama koşu temiz durumda değildi (öncesinde model
> boşaltılmadı; `nvidia-smi` kartın toplamını verir ve o an ~900 MB masaüstü
> yükü vardı; Ollama modelin kendisi için 5272 MB bildiriyor). Daha uzun
> üretimin KV önbelleğini büyütüp tavanı zorlaması **mümkün** ama
> ölçülmedi. [EMİN DEĞİLİM] — temiz koşulda yeniden ölçülmeli.

---

## Kusur 3 — iki gerçek kusur ölçülüyordu ama puanlanmıyordu

### 3a — yapay zekâ kalıbı artık düşürüyor

192 cevapta ölçüldü: **yanlış pozitif yok.** 11 eşleşmenin hepsi persona'nın
adıyla yasakladığı ifadeler (*"nasıl yardımcı olabilirim"*, *"mutluluk
duyarım"*, *"buradayım"*). llama iki koşuda da 0, qwen 11.

### 3b — yabancı sızıntı: kartın önerdiği çözüm ölçümle yetersiz çıktı

Kart *"yanlış pozitif çıkarsa listeyi daralt"* diyordu. Ölçtüm: 192 cevapta
5 eşleşme, **3'ü yanlış pozitif**:

| vaka | eşleşme | gerçekte ne |
|---|---|---|
| `t1_tone_014` (llama) | ` the `, ` and ` | AC/DC albüm adları — *"The Razors Edge"*, *"Rock and roll'ın"* |
| `t1_tech_005` (qwen) | ` with ` | Python anahtar kelimesi: ` ```python with open(...)` |
| `t1_tone_017` (qwen) | `sure,`, ` you ` | cevabın tamamı İngilizce — **gerçek kusur** |
| `t2_memory_002` (qwen) | ` and ` | *"3 Mart'taCelebratory cake and balloons are…"* — **gerçek kusur** |

Listeyi daraltmak **işe yaramıyor**: yanlış pozitifleri üreten ` and `, aynı
zamanda kartın gösterdiği tek vakayı (`t2_memory_002`) yakalayan işaretçi.
Onu atmak kusuru da atardı.

Ayrım kelimede değil **uzunlukta**: gerçek sızıntı 7+ kelimelik bir İngilizce
cümle, yanlış pozitifler en fazla 3 kelimelik özel isim. Puanlanan kural bu
yüzden **ardışık İngilizce dizisi** (`FOREIGN_RUN_WORDS = 6`), kod blokları
hariç (`_prose_only`, tekrar dedektörüyle aynı ayrım).

Eşik 4–7 aralığında **aynı** sonucu veriyor (2 vaka, 0 yanlış pozitif); 6
bilerek ortadan seçildi. `foreign_hits` raporlanan sinyal olarak
**değişmedi** — tek kelime hâlâ görülür, yalnızca puanlanmaz.

**Ek koruma:** soru İngilizce ise puanlanmaz. Persona *"Ahmet İngilizce
yazarsa İngilizce yanıt verirsin"* diyor; vaka setindeki tek örnek
`t1_mix_001`. Bu koruma olmasa persona'sına **uyan** model düşerdi —
`expect_efendim` hatasının üçüncü tekrarı.

---

## Düzeltmelerin kıyas tablosuna etkisi

Kusur 1 ve 3, **qwen'in** sayısını değiştirdi; llama'nınkini değiştirmedi.

| | llama3.1 canlı | qwen2.5:7b canlı |
|---|---|---|
| Eski terazi (09-04) | 48/64 | 49/64 |
| **Düzeltilmiş terazi** | **48/64** | **41/64** |
| sızıntı | 8 → 8 | 6 → **2** |
| kalıp (artık puanlanır) | 0 | **11** |
| İngilizce cümle (artık puanlanır) | 0 | **2** |

qwen'in düşüşü yeni bir kusur bulunduğu için değil; zaten ölçülen iki kusurun
artık **puanlanıyor** olması. 09-04 kıyas belgesine bu yönde bir uyarı
banner'ı eklendi; gövdesi değiştirilmedi.

Bu tablo `local_main` kararını **değiştirmez** — o karar Ahmet'in ve
2026-09-05'te verildi: llama3.1 kalır.

---

## Dokunulmayanlar

- `config/runtime_profiles.json` — değiştirilmedi.
- Vaka metinleri — değiştirilmedi. Tek ekleme: 4 longform vakasına
  `num_predict: 1200` (kusur 2b'nin gerektirdiği alan).
- `passing_threshold` taban kayıtları — sayılar değişmediği için oldukları
  gibi geçerli (A14 kararı yürürlükte, yeni hedef yazılmadı).
- Eşikler: `LEAK_NGRAM_WORDS = 3`, `REPETITION_MIN_HITS = 3`,
  `REPETITION_REPORT_MIN_HITS = 2`, `TRUNCATION_MIN_CHARS = 200` — hiçbiri
  gevşetilmedi. Tek yeni eşik `FOREIGN_RUN_WORDS = 6`, ölçüyle seçildi.

## Açık kalanlar

1. **50 vakanın kulakla değerlendirilmesi** (FAZ-T1) — hâlâ bekliyor.
2. **A11** — koşular arası oynaklık kararı (a/b/c) hâlâ açık.
3. **Uzun bütçede tepe VRAM** — yukarıdaki [EMİN DEĞİLİM] notu; temiz
   koşulda tam bir kıyas koşusu yapılırsa ölçülür.
