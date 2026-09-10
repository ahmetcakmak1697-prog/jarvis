# Dış denetim kaydı — Gemini, iki görev kartı, 2026-09-10

**Denetlenen:** `KART_SES_YOLU_DEEPSEEK.md`, `KART_TERAZI_ZINCIR_2.md`
**Denetim yönergesi:** `KART_DENETIM_PROMPTU.md` (v2)
**Bulguları değerlendiren:** danışman Claude — her bulgu **repoya bakılarak**
sınandı, hiçbiri körü körüne uygulanmadı.

Yedi bulgu geldi. **Dördü kabul, ikisi kısmen, ikisi reddedildi.**

---

## KABUL — dördü de karta girdi

### 1. Kart 1 §2a — "ölç ve seç" kararı ajana bırakılmış

**Bulgu:** *"Otonom bir ajan ürün yöneticisi gibi karar veremez. Ajan ya
rastgele bir metrik icat edip karar mantığı yazacak ya da hata fırlatıp
duracaktır."*

**Doğrulama:** Haklı. Kart hassas içerik bulununca "yerelde kalır ya da
reddedilir, hangisi olduğunu ölç ve seç" diyordu — bu bir ürün kararıdır ve
kartın işidir. Önerdiği mekanizma da repoda **gerçekten var**:
`RedactionGuard.contains_sensitive_data()` → `agents/redaction_guard.py:103`.

**Uygulandı.** Karar karta yazıldı: guard `True` dönerse yerele düşülür,
reddedilmez; guard istisna atarsa da dışarı çıkılmaz. İkincisi Gemini'nin
istediğinden fazlası — `voice_loop.py:158-164`'teki mevcut desenden ve
Codex'in B10 bulgusundan geldi.

### 2. Kart 1 ADIM 5 — "sayı bir yerde yazmalı" hedefi belirsiz

**Bulgu:** *"Ajan stdout'a print() atıp testi geçebilir veya kök dizine
rastgele bir harcama.txt açabilir. Bu, bitti ölçütünü sahte şekilde sağlar."*

**Doğrulama:** Haklı, klasik sahte başarı kriteri.

**Uygulandı — ama önerdiği yolla değil.** Gemini `logs/llm_cost.log`
önerdi; **`logs/` dizini repoda yok** ve o dosya uydurma. Doğru hedef
`CostLedger`'ın zaten kullandığı `cost_ledger.jsonl`
(`agents/cost_ledger.py`, `DEFAULT_FILENAME`, `_append()`). §9
adopt-over-build: var olan mekanizmaya yaz, yeni dosya açma.

### 3. Kart 1 — mock'la geçiştirilmiş test hiçbir şey kanıtlamaz

**Bulgu:** *"`call_count == 0` assert etmek, dış çağrının gerçekten
engellendiğini ispatlamaz."*

**Doğrulama:** Haklı ve önemli. Kapı hiç kurulmamışken de o test yeşil yanar.

**Uygulandı.** Üç testin de **mutasyon sınamasından** geçmesi şart koşuldu:
kapı bellekte devre dışı bırakılınca test kırmızı yanmalı. Bu,
`scripts/mutation_gate.py`'nin mantığının elle uygulanmasıdır.

### 4. Kart 2 ETAP 6 — "gerçek çağrı yapılmadı" doğrulanamaz

**Bulgu:** Gemini bunu dürüstçe *"doğrulayamıyorum"* diye işaretledi ve
mekanik bir kanıt istedi.

**Doğrulama:** Haklı. Kart beyan istiyordu, kanıt değil.

**Uygulandı.** `_http_json` yerine çağrıldığı anda `AssertionError` atan
sahte uç konulacak; ağa çıkmaya çalışan her yol gürültülü düşer.

---

## KISMEN KABUL — endişe haklı, önerilen çözüm uydurma

### 5. Kart 1 §2c — kullanıcı geri düşmeyi nasıl öğrenecek?

**Endişe haklı:** kart "kullanıcı bilecek" diyordu, mekanizmayı söylemiyordu.

**Önerisi reddedildi:** yapılandırmadan `fallback_warning_message` okunmasını
istedi. Böyle bir anahtar yok ve gerekmiyor — repo'nun **kendi deseni var**:
`voice/voice_loop.py` → `_duyur()`, `[ses] ...` önekli, seslendirilmeyen
bildirim. Üstelik tam kardeş senaryo orada duruyor: *"bulut sentezine
göndermedim, ekranda bırakıyorum."*

**Kural alıntısı da yanlıştı.** §7.1'in "koda gömülmez" kuralı **model
adları** içindir; kullanıcıya dönük metinler bu projede kodda tutulur
(`agents/persona.py` de öyle).

**Uygulandı:** `_duyur()` deseni + üç durumun (hassas / ağ hatası / "yerel
kal") **ayırt edilebilir** olması şartı. Üçüncüsü Gemini'de yoktu.

### 6. Kart 2 ETAP 4 — ajan "gerçek sızıntı" ile "yanlış alarm"ı ayıramaz

**Endişe haklı ve iyi yakalanmış:** kart ajandan mekanik olarak yapamayacağı
bir yorum istiyordu.

**Önerisi reddedildi:** JSON'daki `is_false_positive` alanına bakmasını
söyledi — **öyle bir alan yok**, uydurdu.

**Uygulandı, daha iyi bir mekanizmayla:** n-gram **küme farkı**. Kaybolan
n-gram kümesi `_YONTEM`'den türeyenlere eşit olmalı; `prompt_leak` True→False
dönen her vakanın eski `hits` listesi o kümenin alt kümesi olmalı. Tamamen
mekanik, yorum gerektirmiyor, ve ajan hüküm vermiyor — **görünür kılıyor.**

---

## RED — repoya bakınca yanlış çıktı

### 7. Kart 2 ETAP 5 — "iç çelişki: profil dosyasına dokunmadan DeepSeek
koşulamaz"

**Yanlış.** Kalite koşucusu sağlayıcıyı bayrakla alıyor
(`--saglayici deepseek`, `--model`), `runtime_profiles.json` okumuyor.
Çelişki yok.

Yine de karta **açıklayıcı bir satır eklendi** — repo'yu bilmeyen biri aynı
çıkarımı yapabilir, ve ajan da yapabilir.

### 8. Kart 2 ETAP 5 — "`passing_threshold` şema değişikliği okuyucuları
bozar"

**Yanlış.** Blok **zaten** iç içe bir nesne (string değerler + `olcum_tanimi`
alt nesnesi) ve dosyanın kendi notu şunu diyor: *"Hiçbir Python kodu bu
bloğu okumaz."* Bozulacak okuyucu yok.

Değişiklik yapılmadı.

---

## Ayrıca kayda geçsin

Gemini ilk turda **yanlış şeyi denetledi** — kartları değil, denetim
yönergesini eleştirdi. İkinci turda düzeldi.

Ve ilk turdaki eleştirisinde **kaynaksız bir istatistik** üretti:
*"few-shot halüsinasyonları %80 oranında azaltır."* Böyle bir ölçüm yok.
Bu yüzden denetim yönergesi v2'ye açık bir madde eklendi: *"Ölçmediğin
hiçbir orana, yüzdeye veya süreye atıfta bulunma."* İkinci turda uydurma
sayı gelmedi.
