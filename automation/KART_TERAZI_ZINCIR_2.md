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

Korpusu daraltmak, gerçek bir sızıntıyı **görünmez** yapabilir. Ölç:

- Kayıtlı tüm koşuları (`automation/KALITE_*.json`) yeni korpusla yeniden
  puanla.
- **Daha önce yakalanan hangi gerçek sızıntı artık yakalanmıyor?** Varsa
  adıyla yaz. Bir tane bile varsa **DUR ve söyle** — o zaman blok bazlı
  değil daha dar bir çıkarma gerekir.
- `t1_mix_003` gibi persona'yı bütünüyle döken bir cevap **hâlâ**
  yakalanmalı. Bunu testle kilitle.

Mevcut testleri (`test_style_examples_are_not_leaks` vb.) bozma.

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

---

## Zincir boyunca sınırlar

- `agent/local_agent.py`, `config/runtime_profiles.json`: **DOKUNMA.**
  Ses yolunun DeepSeek'e bağlanması ayrı bir kart
  (`KART_SES_YOLU_DEEPSEEK.md`) ve orada başka bir oturum olabilir.
- `agents/persona.py`: **DOKUNMA.** Kararın tamamı korpus tarafında.
- `.env` okunmaz, yazılmaz (§9).
- Push yok. Ortak index'e başka oturumun staged bıraktığı dosyayı commit'leme.

## Bitti sayılma ölçütü

- ETAP 4: sızıntı testi önce kırmızı görüldü; `_YONTEM` korpustan çıktı;
  **kapsam kaybı ölçüldü ve raporda yazılı**; `t1_mix_003` hâlâ yakalanıyor.
- ETAP 5: iki model yeni tanımla koşuldu; `passing_threshold` gerçek
  sayıları taşıyor; `olcum_tanimi` dedektör sürümünü de içeriyor;
  `CLAUDE.md` §13.2 güncel; eski sayılar tanımlarıyla duruyor.
- ETAP 6: dört sağlayıcı kayıtlı, doğrulanmamış alanlar `None` ve listeli,
  `config/model_fiyatlari.json` `null` sayılarla var, **hiçbir gerçek çağrı
  yapılmamış**.
- Üç etap, üç commit, üçünde de kapı iki sırada yeşil ve ruff ≤ 283.
