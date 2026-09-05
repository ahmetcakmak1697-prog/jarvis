# KART — İki Türkçe modeli düzeltilmiş terazide ölç

**Durum:** Açık · **Karar:** Ahmet, 2026-09-05 — araştırma onaylandı, ölçüm yapılacak
**Önceki kart:** `KART_terazi_duzeltmeleri.md` (kapandı — `bb383d4`, `f2c5137`, `d030f98`)

Terazi üç turda kuruldu ve artık güvenilir. Bu kart onu, repo'nun kendi
yapılacaklar listesinde bekleyen bir maddeyi kapatmak için kullanıyor.

---

## Neden bu iki model

`docs/HARDWARE_AND_LOCAL_LLM_RESEARCH.md` §8, yapılacaklar sırasının **6.
maddesi** olarak zaten şunu yazıyor: *"Turkish-Gemma-9b-T1 GGUF'unu Türkçe
kalite karşılaştırmasına sok."* `config/runtime_profiles.json` notu da
ertelemenin gerekçesini kaydetmiş: *"Turkish-Gemma-9b-T1 indirilmedi (Ahmet
kararı: önce bu değişikliğin etkisi dinlenecek)."* O etki dinlendi, terazi de
düzeldi — madde artık açılabilir.

**Aday 1 — Turkish-Gemma-9b-v0.1** (YTÜ COSMOS). İnsan değerlendirmesi:
1.450 soru, 18 değerlendirici, ikili karşılaştırma; %68,65 kazanma oranıyla
Qwen3-32B'yi (%67,20) geçiyor. §4'e göre 8 GB'a sığıyor, §7'ye göre ~5,5 GB Q4.

> **T1 değil, v0.1 alınacak.** T1 akıl-yürütme sürümü; §5'in 3. maddesi sesli
> hat için *"`/no_think` zorla, thinking bloğu 500+ token = bütçeyi tek başına
> yer"* diyor. Ölçümü düşünme bloklarıyla kirletmenin anlamı yok.

**Aday 2 — Turkcell-LLM-7b-v1.** Mistral 7B tabanlı, 5 milyar Türkçe token,
Apache 2.0, ~4,5 GB. Bu proje için özel değeri: **genişletilmiş Türkçe
tokenizer.** `TURKISH_TOKENIZER_PENALTY = 1.9` sabiti tam bu maliyeti ölçüyor;
tokenizer cezası düşerse aynı bütçede daha çok içerik ve daha yüksek
Türkçe-eşdeğer hız çıkar. Bu, kalite puanından bağımsız ölçülebilir bir kazanç.

**Referans — llama3.1:latest de aynı oturumda koşacak.** Mevcut 48/64 dünkü
koşunun yeniden puanlanmasıdır; VRAM ve hız karşılaştırmasının geçerli olması
için üçü de aynı makine durumunda ölçülmeli. Yan ürün: A11 için üçüncü
oynaklık verisi.

---

## Yapılacak iş

### 1. Modelleri getir — ve şablon tuzağına dikkat

```
ollama pull RefinedNeuro/Turkcell-LLM-7b-v1
```

Turkish-Gemma için önce **yer kontrolü** yap (§7: "gerçek sorun biriktirme").
İki model ~10 GB.

> **⚠️ En büyük tuzak burada: yanlış sohbet şablonu iyi modeli kötü gösterir.**
> GGUF'u Ollama'ya elle alırken `Modelfile`'daki TEMPLATE ve stop token'ları
> modelin kendi kartındakiyle **birebir** eşleşmeli. Yanlışsa model sessizce
> saçmalar ve biz bunu "Türkçe model kötüymüş" diye kaydederiz — ölçümün
> tamamı çöp olur.
>
> Bu yüzden: **resmî `ytu-ce-cosmos` GGUF'u tercih et.** Topluluk aynası
> (`alibayram/turkish-gemma-9b-v0.1`) kullanılacaksa `ollama show --modelfile`
> ile şablonu ve kuantizasyonu **yazdır ve belgeye ekle** — hangi paketi
> ölçtüğümüz kayıtlı olsun.
>
> Şablonu doğrulayamıyorsan **dur ve sor** (§9). Doğrulanmamış şablonla ölçüm
> yapma.

### 2. Üç koşu, aynı oturum, temiz koşullar

```
python -m eval.run_turkish_quality --model llama3.1:latest
python -m eval.run_turkish_quality --model <turkish-gemma>
python -m eval.run_turkish_quality --model RefinedNeuro/Turkcell-LLM-7b-v1
```

**VRAM için temizlik şart** — bu koşunun ikinci ürünü aşağıdaki açık uç:
tarayıcı/oyun/başka model kapalı, masaüstü yükü not edilsin. `nvidia-smi`
kartın **toplamını** verir (raporun kendi uyarısı).

### 3. Açık uç: 1200 token bütçesi tavanı aşıyor mu?

`KART_terazi_duzeltmeleri.md` sonrası `longform` vakaları kalıcı olarak 1200
token alıyor, yani KV cache büyüdü. Ajan uzun bütçe testinde tepe **6275 MB**
görmüş — 6144 tavanının üstünde — ama koşu temiz değilmiş (~900 MB masaüstü
yükü) ve [EMİN DEĞİLİM] diye işaretlemiş.

**Temiz koşulda ölç ve karara bağla:** üç modelin her biri için tepe VRAM,
tavanı aşıp aşmadığı, ve Ollama'nın modelin kendisi için bildirdiği değer
ayrı ayrı yazılsın. Aşıyorsa bu, longform bütçesi için ayrı bir karar konusu
olur — **bu kartta çözme, ölç ve yaz.**

### 4. Kıyas belgesi

`automation/MODEL_KIYASI_TURKCE_2026-09-05.md`. `MODEL_KIYASI_2026-09-04.md`
biçimini izle, üzerine yazma. En az:

- Kategori kategori üç sütun
- Neden dağılımı: sızıntı / tekrar / kesilme / uydurma / kalıp / yabancı
- Hız: ham tok/s **ve Türkçe-eşdeğer tok/s** — Turkcell'in tokenizer iddiası
  burada sınanır; aradaki fark beklenenden küçükse iddia tutmamış demektir
- `done_reason` dağılımı (kaç cevap bütçeden, kaç cevap kendi durdu)
- Tepe VRAM + tavan durumu + masaüstü yükü notu
- llama3.1 canlı-vs-canlı: dünkü 48'e göre sapma → A11'e üçüncü veri

---

## Yasaklar

1. **`config/runtime_profiles.json`'a dokunma.** `local_main` = llama3.1,
   Ahmet'in 2026-09-05 kararı. Bu kart kanıt üretir, model değiştirmez.
2. **Puanlayıcıya dokunma.** Terazi donduruldu. Üç koşu da aynı puanlayıcıyı
   kullanacak, yoksa kıyas anlamsızlaşır. `test_the_recorded_run_still_scores_49_of_64`
   hâlâ 49 demeli.
3. **Kazananı ilan etme.** Tabloyu kur, takasları açıkça yaz (biri Türkçe'de
   iyi ama zeminde kötüyse bunu tek bir "daha iyi" cümlesine sıkıştırma),
   kararı Ahmet'e bırak.
4. **Şüpheli şablonla ölçme.** Doğrulayamıyorsan dur ve sor.
5. Auto-fix retry yok: indirme/koşu patlarsa yaz ve dur (§9).

## Bitti sayılma ölçütü

- Üç koşu tamam, ham JSON'lar repoda, hangi paketin (digest/kuantizasyon/
  şablon) ölçüldüğü kayıtlı.
- Kıyas belgesi yazıldı; içinde Türkçe-eşdeğer hız, `done_reason` dağılımı,
  temiz VRAM ölçümü ve A11 sapması var.
- `pytest tests -q` yeşil (alfabetik **ve** ters sıra), `ruff check .` ≤ 293.
- Taban testi hâlâ 49 diyor.
- Commit: yalnız isimli dosya. Push yok. **Bittiğinde dur.**
