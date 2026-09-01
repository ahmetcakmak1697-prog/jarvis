# Türkçe Model Kıyası — 2026-09-01

**Neden bu kıyas var:** `config/runtime_profiles.json` kendi notunda
*"bir model 'varsayilan' yapilmadan once benchmark ile dogrulanir"* ve
*"local_main icin Qwen'e gecis HALA benchmark bekliyor"* diyor. Bu borç
ödendi.

**Kazanan ilan edilmedi. `runtime_profiles.json`'a dokunulmadı.** Türkçe
kalite özneldir; deterministik kapı yalnız regresyonu tutar, kaliteyi Ahmet
onaylar (FAZ-T1 deseni).

**Yöntem:** 7 sabit Türkçe soru (selam ×2, teknik ×2, hafıza ×2, uzun anlatım),
her modele **aynı** persona prompt'uyla (`agents/persona.py`, seviyeye göre
L1/L2/L3), `num_ctx=4096`, `num_predict=400`, `temperature=0.2`.
Her model ölçümden önce ısıtıldı, sonra `keep_alive=0` ile boşaltıldı.
Ham veri: `automation/_model_bench_raw.json`.

---

## Ölçüm tablosu

| Model | Dosya | VRAM artışı | Tepe VRAM | tok/s | TR-eşdeğer | Ort. yanıt | İlk token |
|---|---|---|---|---|---|---|---|
| **qwen2.5:7b** | 4,7 GB | 4707 MB | **5386 MB** | **78,2** | **41,2** | **4,8 s** | **53 ms** |
| **llama3.1:latest** | 4,9 GB | 5199 MB | 5878 MB | 74,3 | 39,1 | 4,0 s | 52 ms |
| **mistral-nemo:latest** *(mevcut local_main)* | 7,1 GB | 6195 MB | **6880 MB** | **25,8** | **13,6** | 8,5 s | 180 ms |

TR-eşdeğer = ham tok/s ÷ 1,9 (Türkçe tokenizer cezası,
`HARDWARE_AND_LOCAL_LLM_RESEARCH.md` §4).

### Kartın VRAM hipotezi doğrulandı

`HARDWARE_AND_LOCAL_LLM_RESEARCH.md` §3: *"8 GB kartta pratik tavan ~6 GB
model dosyası"*, ve tavanı aşan modelin katman katman RAM'e taşıp çöktüğü
ölçülmüştü.

Ölçülen: **mistral-nemo tepe 6880 MB** — 8192 MB'lık kartta tavanın üstünde.
Sonucu tabloda görünüyor: **3 kat yavaş** (25,8'e karşı 78,2 tok/s) ve ilk
token **3,5 kat geç** (180 ms'e karşı 52 ms). Diğer iki model rahat sığıyor.

Bu, JARVIS'in "yavaş" hissettirmesinin ölçülmüş sebebidir.

---

## Kalite gözlemleri

### Persona uyumu ("Efendim" hitabı, 7 turda)

| Model | Efendim |
|---|---|
| llama3.1 | **3/7** |
| qwen2.5:7b | 2/7 |
| mistral-nemo | **0/7** |

### Bozuk Türkçe — deterministik dedektör 0/7 buldu, ama bu YETERSİZ

`tests/test_persona_ssot.py::corrupted_fragments` yeniden kullanıldı
(adopt-over-build). Üç modelde de **0 bulgu** — ama bu dedektör *kodlama
bozulmasını* yakalar (mojibake, soru işaretine dönmüş harfler), **dilbilgisi
hatasını değil**. Gözle görülen gerçek:

| Model | Örnek çıktı | Sorun |
|---|---|---|
| mistral-nemo | *"Selamlar Ahmet Bey, ben için çok teşekkürler. Sizin için ne yapabileceğime ne diyorsunuz"* | Cümle Türkçe değil |
| qwen2.5:7b | *"size nasılsınız diye sormaktan mutluluk duyarım"* | Bozuk yapı + yasak kalıp |
| llama3.1 | *"Telmeteri verisini pandas ile özetrme"* | İki yazım hatası |

**Bu, kararın neden Ahmet'e ait olduğunu gösteriyor:** ölçülebilen tek şey
kodlama bütünlüğü; akıcılık kulakla değerlendirilir.

### Uydurma testi (kayıt olmayan iki soru)

| Model | "Geçen hafta ne konuştuk?" | "Eşimin doğum günü ne zamandı?" |
|---|---|---|
| qwen2.5:7b | ❌ uydurdu (telemetri konuşması icat etti) | ✅ *"bu bilgiye erişimim yok"* |
| mistral-nemo | ❌ soruyu tekrarladı | ✅ *"Doğum tarihi bilmiyorum"* |
| llama3.1 | ❌ uydurdu (ESHOT projeleri icat etti) | ⚠️ *"doğum **günüm** hakkında bilgiye erişemiyorum"* |

**Üçü de "Geçen hafta ne konuştuk?" sorusunda uydurdu.** Bu bir model kusuru
değil, **mimari eksiklik**: bu kıyasta `LifeGraph.recall_context()` zemini
verilmedi (kasıtlı — modelleri çıplak karşılaştırmak için). Canlı sistemde
zemin veriliyor ve daha önce ölçülmüştü: zeminli soruda uydurma durmuştu.

**Dedektör uyarısı:** llama3.1'in ikinci cevabı aslında dürüst bir kaçış
("erişemiyorum") ama benim anahtar kelime listem bunu yakalamadı — dedektör
`durust_kacis=False` dedi, **yanlış**. Ayrıca llama3.1 soruyu yanlış anladı:
"eşimin" değil "günüm" dedi. Sayıyı bu yüzden ⚠️ işaretledim.

### Yabancı kelime sızıntısı

Üç modelde de **0/7**. Persona'nın *"Gerekmedikçe İngilizce kelime
karıştırmazsın"* kuralı tutuyor.

### Sistem prompt'u sızıntısı

**mistral-nemo**, uzun anlatım turunda persona metnini cevap sanıp geri
kustu: *"Ahmet'in en güvendiği zihinsel ortağı olduğum için, onun hedefi
benim de hedefimdir..."* Aynı kusur 2026-08-31'de `llama3.2` için de
ölçülmüş ve o model bu yüzden `local_small` rolünden çıkarılmıştı.

---

## Önerim (bağlayıcı değil)

**`local_main`: mistral-nemo → qwen2.5:7b.**

Gerekçe, tercih değil ölçüm:
1. VRAM tavanının altında (5386 MB / 8192 MB) — mistral-nemo üstünde.
2. **3 kat hızlı**, ilk token 3,5 kat erken. Sesli asistanda bu her turda
   hissedilir.
3. Persona uyumu daha iyi (2/7 ve 0/7).
4. Sistem prompt'u sızdırmadı; mistral-nemo sızdırdı.

**llama3.1 ciddi bir alternatif** — persona uyumu en iyisi (3/7) ve hız
neredeyse aynı. Zayıf yanı yazım hataları ("Telmeteri", "özetrme").
qwen ile arasındaki fark **kulak kararıdır**, ölçüm ikisini ayıramıyor.

**Uyarı:** `local_small` zaten qwen2.5:7b. Öneri kabul edilirse `local_small`
ve `local_main` **aynı model** olur — kademe ayrımı anlamını yitirir.
Bu durumda ya `local_small` llama3.2'ye geri alınmalı (ama o model prompt
sızdırıyordu) ya da kademe yapısı yeniden düşünülmeli. **Bu ayrı bir karar.**

---

---

## EK: Whisper `small` vs `medium` (STT) — varsayılan DEĞİŞTİRİLMEDİ

**Yöntem:** 4 bilinen Türkçe cümle Edge TTS ile sese çevrildi (referans metin
belli), 16 kHz mono'ya indirildi, iki modelle transkribe edildi. Doğruluk
karakter benzerliği ile ölçüldü — kulakla değil.
Ham veri: `automation/_whisper_bench_raw.json`.

| Model | Yükleme | Ort. transkripsiyon | Gerçek-zaman çarpanı | Ort. benzerlik |
|---|---|---|---|---|
| **small** *(mevcut)* | 18,2 s | **1,05 s** | **0,26×** | **0,982** |
| medium | 25,0 s | 2,85 s | 0,69× | 0,974 |

**`medium` daha yavaş VE daha doğru değil.** 2,7 kat yavaş, benzerlik ise
biraz **düşük**. Örnek: `small` *"Polimer"* yazdı, `medium` *"Polymer"*
(İngilizce) yazdı.

İkisi de "üç Mart"ı "3 Mart" olarak yazdı (davranış, hata değil) ve ikisi de
"ESHOT" kısaltmasını kaçırdı (`small` → "SOT", `medium` → "SH").

**Önerim: `small` kalsın.** Değişiklik önerisi yok.

**Dürüst sınır:** Test sesi TTS üretimi — temiz, gürültüsüz, aksansız.
Gerçek mikrofon kaydında (oda gürültüsü, konuşma temposu) sonuç farklı
olabilir; `medium` orada öne geçebilir. Bu ölçüm **stüdyo koşulunu** ölçtü.
Gerçek mikrofonla tekrarı Ahmet konuştuğunda yapılabilir.

---

## Kapsam dışı

- **Turkish-Gemma-9b-T1 indirilmedi** — model indirme insan kapısı.
  `automation/AHMET_ONAYI_BEKLEYENLER.md` → A1.
- `runtime_profiles.json` **değiştirilmedi** — A2.
