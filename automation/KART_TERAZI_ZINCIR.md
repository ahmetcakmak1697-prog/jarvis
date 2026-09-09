# KART — Terazi zinciri: bütçe → taban → çok sağlayıcı (üç etap, tek akış)

**Kime:** Claude Code (VS Code) · **Veren:** Ahmet, 2026-09-10
**Dal:** `auto/opencode-deepseek` · **Taban:** `f1aa069`

---

## 0. Bu kart neden zincir — ve §9 nasıl korunuyor

`CLAUDE.md` §9: *"Otomatik sıradaki-işe-geçiş yok."* Bu kart üç etabı
ardışık yürütüyor, yani kuralın **lafzını** esnetiyor. Ahmet bunu bilerek
istedi ve gerekçe şu: üç etap **aynı işin** parçaları — terazinin çok
modelli ölçüme hazırlanması. Ayrı ayrı verilirse ikisi arasında ölçüm
tanımı değişir ve iş **iki kez** yapılır.

**§9'un ruhu korunuyor, katı biçimde:**

> **Herhangi bir etabın kapısı düşerse, bir doğrulama kırmızı yanarsa, ya
> da bir BLOCKER/CONCERN çıkarsa — ZİNCİR ORADA DURUR.** Sonraki etaba
> geçilmez. Rapor yazılır, Ahmet'e gidilir. Auto-fix retry yok.

Yani mutlu yolda ilerler, bozuk yolda durur. §9'un var oluş sebebi
"başarısız bir adımın üstüne sessizce iş yığılmaması"ydı; bu kart onu
açıkça uyguluyor.

Her etabın sonunda **ayrı commit** ve **tek paragraflık ara rapor**.

---

# ETAP 1 — Longform bütçesi (ölçüm tanımı değişikliği)

**Kaynak kart:** `automation/KART_DEEPSEEK_10_KUSUR.md` → PARÇA B.
Onu oku; burada yalnız eklenen kısıtlar var.

**Ahmet'in imzası verildi** (2026-09-09) ve koşulludur: bütçe değişirse
`llama3.1` de **aynı tanımla** yeniden koşulur (ETAP 2).

### Bütçeyi TAHMİNLE seçme

Ölçülmüş durum: dört longform vakası da `num_predict=1200`'de
`done_reason="length"` ile kesiliyor, cevaplar 2599–3042 karakter.
Modelin **kendi durduğu** uzunluk bilinmiyor.

Önce onu bul: tek bir longform vakasını yüksek bir bütçeyle (ör. 4000)
koştur, `done_reason == "stop"` olduğu noktayı **gör**, sonra sayıyı
ona göre — makul bir pay bırakarak — belirle. Seçtiğin sayının
gerekçesini rapora yaz.

### ÖNGÖRÜ — bunu şimdiden yaz, sonra doğrula

`llama3.1`'in ölçülmüş başlıca kusuru **tekrar/dejenerasyon** (6 vaka).
Bütçeyi büyütmek ona **tekrar etmek için daha çok yer** verir.

**Yani llama'nın puanı düşebilir.** Düşerse bu bir gerileme değil,
modelin tavanının daha görünür olmasıdır — ama **taban değişir** ve
bunun böyle olduğu yazılmalıdır. Öngörüyü önce yaz, sonra sayıyı gör;
tersini yaparsan sonuca göre hikâye kurmuş olursun.

### Ayrıca

- `passing_threshold` bloğu **taban kaydıdır, hedef değil** (A14).
  `">=N"` sözdizimi yasak.
- `CLAUDE.md` §13.2'deki *"taban 49/64"* cümlesi de güncellenmeli —
  ölçüm tanımı değişiyor.
- Eski sayılar **silinmez**; "hangi tanımla ölçüldüğü" ile birlikte durur.

**ETAP 1 kapısı:** `pytest tests -q` iki sırada, `ruff ≤ 283`, commit,
ara rapor. **Düşerse dur.**

---

# ETAP 2 — Tabanı yeni tanımla tazele

Yeni bütçeyle **iki modeli de** koştur:

- `llama3.1:latest` (yerel, `--model` ile)
- `deepseek/deepseek-chat` (`--saglayici deepseek`)

Rapora **dört sayı** yan yana: her modelin eski tanımdaki ve yeni
tanımdaki puanı. Ve tek cümlelik uyarı: eski ile yeni **karşılaştırılamaz**.

### Bu etapta da hüküm verme

DeepSeek PARÇA A sonrası 56/64 idi ama o koşuda **5 vaka düzelip 3 vaka
bozulmuştu** — net +2, A11'in gürültü zarfının içinde. Kalıp kusuru
3'ten 3'e gitti, yani hedeflenen kusur azalmadı.

**56'yı taban ilan etme.** Yeni tanımdaki sayıyı yaz, "tek koşu hüküm
değildir" uyarısını koru.

**ETAP 2 kapısı:** kapı yeşil, dört sayı raporda, commit, ara rapor.
**Beklenmedik bir şey çıkarsa dur** — ör. bir kategori 2+ vaka oynarsa,
sebebini yaz ve Ahmet'e sor.

---

# ETAP 3 — Terazi çok sağlayıcılı olsun

**Kaynak kart:** `automation/KART_TERAZI_COK_SAGLAYICI.md`. Tamamını oku
ve uygula. Kısaca: dört sağlayıcı kaydı (DeepSeek mevcut + Kimi K2.8 +
OpenAI + Gemini), giriş/çıkış tokenı kaydı, `config/model_fiyatlari.json`
(sayılar `null`), `--tahmin` bayrağı, sahte uçla uçtan uca testler.

O kartın üç kuralını burada tekrar ediyorum çünkü en çok atlanan yerler:

1. **URL ve model kimliğini TAHMİN ETME.** Doğrulamadan koda yazma;
   doğrulanmamış alan `None` kalır ve raporda "Ahmet doldurmalı" diye
   listelenir.
2. **Fiyatları sen doldurma.** `null` bırak. Fiyat yoksa rapor
   *"fiyat girilmedi"* yazar, tahmini sayı **yazmaz**.
3. **Gerçek API çağrısı YAPMA.** Yeni sağlayıcılara para harcayan koşu
   Ahmet'in ayrı kararıdır. Bu etap plumbing kurar.

Gemini'nin şekli OpenAI-uyumlu **değildir**; `sekil` alanıyla ayır,
`if saglayici == ...` dallanması yazma.

**ETAP 3 kapısı:** kapı yeşil, hiçbir gerçek çağrı yapılmamış, commit,
kapanış raporu.

---

## Zincir boyunca geçerli sınırlar

- `.env` okunmaz, yazılmaz (§9).
- Kalite eşikleri ve dedektörler **değişmez.** Değişen tek şey longform
  token bütçesi ve o da imzalı.
- Anthropic modelleri listede **yok** — ayrı imza.
- `agents/persona.py`'ye **dokunma.** Codex aynı anda orada
  (`KART_PUSULA_KIRIK.md`). Persona'ya dokunman gerektiğini düşünürsen
  **dur ve söyle**.
- Push yok. Yalnız isimli dosya `git add` — ortak index'e başka bir
  oturumun staged bıraktığı dosya varsa **onu commit'leme.**

## Bitti sayılma ölçütü (zincirin tamamı)

- Üç etap, üç commit, üçünde de kapı iki sırada yeşil ve ruff ≤ 283.
- Longform bütçesi **ölçümle** seçilmiş; gerekçesi yazılı.
- llama öngörüsü önce yazılmış, sonra sayıyla karşılaştırılmış.
- Dört sayı (2 model × 2 tanım) yan yana; karşılaştırılamazlık uyarısı var.
- `CLAUDE.md` §13.2 tabanı güncel.
- Dört sağlayıcı kayıtlı, doğrulanmamış alanlar `None` ve listeli.
- `config/model_fiyatlari.json` var, sayılar `null`.
- **Hiçbir yeni sağlayıcıya gerçek çağrı yapılmamış.**
