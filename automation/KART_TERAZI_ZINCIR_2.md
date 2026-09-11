# KART — Zinciri tamamla: sızıntı yanlış alarmı → taban → ETAP 3

**Kime:** Claude Code (VS Code) · **Veren:** Ahmet, 2026-09-10
**Dal:** `auto/opencode-deepseek` · **Taban:** `bfb4581`
**Önceki:** `automation/KART_TERAZI_ZINCIR.md` — ETAP 1 ve 2 bitti,
zincir kendi kuralı gereği durdu ve Ahmet'e üç soru sordu. Bu kart o üç
soruyu cevaplıyor ve zinciri tamamlıyor.

Aynı zincir kuralı geçerli: **bir etabın kapısı düşerse ya da bir
doğrulama kırmızı yanarsa, ZİNCİR ORADA DURUR.**

---

# ETAP 4 — `prompt_leak` yanlış alarmı (İMZALI)

## Ölçülmüş durum

`agents/persona.py:139` → `_YONTEM` bloğu ("## ARAŞTIRMA VE ANALİZ TARZIN")
modele **cevabını nasıl biçimlendireceğini** söylüyor. 7. maddesi:

```
7. Risk, test ve geri alma yolunu ayrı bir maddede belirt
```

`eval/quality_scorer.py:194` → `_instruction_ngrams()` sızıntı korpusunu
`build_system_prompt()` çıktısından n-gram çıkararak kuruyor. Sonuç: model
**talimata uyup** "### 6. Risk, Test ve Geri Alma Yolu" başlığını yazıyor ve
dedektör bunu sızıntı sayıyor.

Bağımsız doğrulandı (danışman Claude, 2026-09-10):

```
prompt_leak      : True
yakalanan n-gram : ['risk test ve', 'test ve geri', 've geri alma']
```

Etkilenen vakalar: `t2_longform_001/002/003/004`, `t2_grounding_005`, ve
llama tarafında `t2_longform_004`.

**Kusur yeni değil.** 1200 token duvarı cevabı o bölüme varmadan kesiyordu;
bütçe onu **görünür yaptı**. Yani `longform` kategorisi bugüne kadar hiç
gerçek bir şey ölçmedi: önce kesilme, şimdi yanlış alarm — iki farklı
sebeple 0/4.

## Ahmet'in kararı: korpusu daralt, persona'yı değiştirme

**Gerekçe:** sızıntı dedektörünün işi, modelin **kimliğini ve kurallarını**
ifşa etmesini yakalamaktır — biçim yönergesine **uymasını** değil. Modelin
istenen başlığı yazması doğru davranıştır ve doğru davranışı cezalandıran
bir ölçüm, ölçümün kendisini çürütür.

Persona'yı yeniden yazmak yanlış yön olurdu: dedektörü memnun etmek için
cevap biçimini bozmak, kuyruğun köpeği sallamasıdır. Ayrıca iki modeli
birden etkiler.

## Bunun bir emsali ve bir deseni zaten var

`_instruction_ngrams()` **hâlihazırda iki istisna taşıyor** ve ikisi de
docstring'inde gerekçesiyle yazılı:

1. Başlıksız kimlik önsözü — Ahmet hakkında **olgu** taşıyor; dahil etmek
   doğru davranan `t1_tone_012`'yi düşürüyordu.
2. Tırnaklı örnekler (`_QUOTED_EXAMPLE`) — talimat değil, örnek.

Bu kart **üçüncüsünü** ekliyor: **biçim/yapı yönergeleri.** Aynı sınıf, aynı
gerekçe, aynı yazım disiplini — istisnanın **neden** var olduğu docstring'e
yazılır, yoksa üç ay sonra biri onu "gereksiz" diye siler.

## Görev

### 1. Önce kırmızı gör

"### 6. Risk, Test ve Geri Alma Yolu" içeren bir cevabın **sızıntı
sayılmadığını** iddia eden test. Şu an geçmemeli.

### 2. `_YONTEM`'i korpustan çıkar — ve KAPSAM KAYBINI ÖLÇ

Bu adım isteğe bağlı değil ve kartın asıl işi budur.

Korpusu daraltmak, gerçek bir sızıntıyı **görünmez** yapabilir.

**Ölçüm MEKANİK olacak — "hangisi gerçek sızıntıydı" diye yorum yapma.**
Ajan eski koşulara bakıp bir yakalamanın "gerçek" mi "yanlış alarm" mı
olduğuna karar veremez; öyle bir etiket veride yok. Bunun yerine küme
farkına bak:

1. `_LEAK_NGRAMS` kümesini **değişiklikten önce ve sonra** hesapla.
2. **Kaybolan n-gram kümesi**, yalnız `_YONTEM` bloğundan türeyenlerin
   kümesine eşit olmalı. Fazlası varsa çıkarma çok geniş demektir → **DUR.**
3. Kayıtlı tüm koşuları (`automation/KALITE_*.json`) **iki kez** puanla:
   bir kez **değişiklikten hemen önceki** dedektörle, bir kez yenisiyle.
   `prompt_leak` değeri **True→False** dönen her vakayı listele.

   > **KARŞILAŞTIRMA TABANI JSON'DAKİ KAYITLI SKOR DEĞİLDİR.** Kayıtlı
   > skorlar farklı dedektör ve farklı persona kuşaklarıyla üretildi;
   > onlarla karşılaştırmak, **başka bir commit'in** yaptığı değişikliği
   > bu kartın hanesine yazar. Ölçüldü (2026-09-10, ETAP 4): dört vaka
   > `['size yardimci olmaktan', ...]` n-gram'larıyla düşmüş görünüyordu
   > — o n-gram'lar persona'dan `f1aa069` (PARÇA A) ile çıkmıştı, bu
   > kartla değil. Doğru tabanla ölçüldüğünde ihlal **sıfır**.

4. Bu vakaların her birinin **önceki dedektörle** hesaplanan
   `prompt_leak_hits` listesi, adım 2'deki kaybolan kümenin **alt kümesi**
   olmalı. Olmayan tek bir vaka bile varsa → **DUR ve söyle.**

5. Kayıtlı skorlarla yeni skorlar arasındaki fark **ayrıca** raporlanır —
   ama bu bir DUR koşulu **değildir**, tarihsel bilgidir: hangi vakanın
   hangi kuşakta değiştiğini gösterir.
5. Dönen vakaları `id` + eski `hits` ile rapora yaz. Bu liste insan gözüyle
   okunacak; ajanın hüküm vermesi istenmiyor, **görünür kılması** isteniyor.

Ayrıca `t1_mix_003` gibi persona'yı bütünüyle döken bir cevap **hâlâ**
yakalanmalı — bunu testle kilitle.

Mevcut iki testi bozma: `test_style_examples_are_not_leaks` ve
`test_leak_corpus_is_derived_from_the_persona_ssot`. İkincisi korpusun
SSOT'tan **türetilmesini** şart koşuyor; blok çıkarma da türetmenin parçası
olmalı, elle yazılmış bir liste değil.

### 3. Kapı

`pytest tests -q` iki sırada, `ruff ≤ 283`, commit, ara rapor. **Düşerse dur.**

---

# ETAP 5 — Tabanı kaydet (ödenmemiş sözü öde)

`eval/turkish_quality_cases.json` → `passing_threshold` şu an **eski
tanımın** sayılarını taşıyor ve şunu diyor:

> *"Yeni tanimdaki taban ETAP 2'de olculecek"*

Bu söz ödenmedi çünkü zincir haklı olarak durdu. Şimdi ödenecek.

**Ama önce ETAP 4 bitmiş olmalı** — kırık bir kategoriyle taban kaydetmek
kusuru betona gömer. Sıra: sızıntı düzeltilir → **iki model de yeniden
koşulur** (llama3.1 + deepseek-chat, yeni tanım + düzeltilmiş dedektör) →
taban o sayılarla kaydedilir.

**DeepSeek koşusu `runtime_profiles.json` GEREKTİRMEZ.** Kalite koşucusu
sağlayıcıyı bayrakla alıyor: `--saglayici deepseek`, model gerekiyorsa
`--model deepseek/deepseek-chat`. Aşağıdaki "dokunma" sınırıyla çelişki
yoktur — profil dosyasına dokunmadan koşuyu izole çalıştır.

Kurallar:

- A14: **hedef yazılmaz**, taban kaydı yazılır. `">=N"` sözdizimi yasak.
- Eski sayılar **silinmez**; hangi tanımla ölçüldükleri yanlarında durur.
- `olcum_tanimi` bloğu güncellenir: artık yalnız `num_predict` değil,
  **dedektör sürümü** de tanımın parçası (ETAP 4 onu değiştirdi).
- `CLAUDE.md` §13.2'deki taban cümlesi güncellenir.
- **Tek koşu hüküm değildir** uyarısı korunur. DeepSeek'in 56'sı taban ilan
  edilmemişti; yeni sayı da tek koşudur.

**Kapı:** iki sırada yeşil, commit, ara rapor. **Düşerse dur.**

---

# ETAP 6 — Çok sağlayıcılı terazi

`automation/KART_TERAZI_COK_SAGLAYICI.md`'yi oku ve uygula. Sızıntı
meselesinden bağımsızdır, plumbing işidir.

Üç kural, en çok atlanan yerler oldukları için tekrar:

1. **URL ve model kimliğini TAHMİN ETME.** Doğrulanmamış alan `None` kalır
   ve raporda "Ahmet doldurmalı" diye listelenir.
2. **Fiyatları doldurma.** `null` bırak; fiyat yoksa rapor
   *"fiyat girilmedi"* yazar, tahmin **yazmaz**.
3. **Gerçek API çağrısı YOK.** Yeni sağlayıcılara para harcayan koşu
   Ahmet'in ayrı kararıdır.

Gemini OpenAI-uyumlu **değildir**; `sekil` alanıyla ayır.

**"Gerçek çağrı yapılmadı" iddiası KANITLANACAK, beyan edilmeyecek.**
Testlerde `_http_json` yerine, çağrıldığı anda `AssertionError` atan bir
sahte uç koy. Böylece ağa çıkmaya çalışan her kod yolu **gürültülü** düşer;
sessizce başarılı olamaz. Yeni sağlayıcıların hiçbiri için gerçek uç
kullanılmadığı bu şekilde mekanik olarak gösterilir.

Bu, `--tahmin` bayrağı için de geçerli: tahmin **hiçbir çağrı yapmadan**
hesaplanır ve testi bunu aynı sahte uçla kanıtlar.

---

## Zincir boyunca sınırlar

- `agent/local_agent.py`, `config/runtime_profiles.json`: **DOKUNMA.**
  Ses yolunun DeepSeek'e bağlanması ayrı bir kart
  (`KART_SES_YOLU_DEEPSEEK.md`) ve orada başka bir oturum olabilir.
- `agents/persona.py`: **DOKUNMA.** Kararın tamamı korpus tarafında.
- `.env` okunmaz, yazılmaz (§9).
- Push yok. Ortak index'e başka oturumun staged bıraktığı dosyayı commit'leme.

## Bitti sayılma ölçütü

- ETAP 4: sızıntı testi önce kırmızı görüldü; `_YONTEM` korpustan çıktı.
- ETAP 4 — **kapsam kaybı MEKANİK olarak ölçüldü:** kaybolan n-gram kümesi
  `_YONTEM`'den türeyenlere eşit; `prompt_leak` True→False dönen her vakanın
  eski `hits` listesi o kümenin alt kümesi; dönen vakalar `id` + eski `hits`
  ile raporda listeli. Hiçbir yerde "bu gerçek sızıntıydı" hükmü verilmedi.
- ETAP 4: `t1_mix_003` hâlâ yakalanıyor; `test_style_examples_are_not_leaks`
  ve `test_leak_corpus_is_derived_from_the_persona_ssot` yeşil.
- ETAP 5: iki model yeni tanımla koşuldu (`--saglayici` bayrağıyla,
  `runtime_profiles.json`'a **dokunulmadan**); `passing_threshold` gerçek
  sayıları taşıyor; `olcum_tanimi` dedektör sürümünü de içeriyor;
  `CLAUDE.md` §13.2 güncel; eski sayılar tanımlarıyla duruyor.
- ETAP 6: dört sağlayıcı kayıtlı, doğrulanmamış alanlar `None` ve listeli,
  `config/model_fiyatlari.json` `null` sayılarla var.
- ETAP 6 — **"gerçek çağrı yok" KANITLANDI:** `_http_json` yerine çağrıldığı
  anda `AssertionError` atan sahte uç kondu; süit bununla yeşil geçti.
  Beyan değil, mekanik kanıt.
- Üç etap, üç commit, üçünde de kapı iki sırada yeşil ve ruff ≤ 283.
