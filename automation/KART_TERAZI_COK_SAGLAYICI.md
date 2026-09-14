# KART — Terazi çok sağlayıcılı olsun + maliyeti de ölçsün

**Kime:** Claude Code (VS Code) · **Veren:** Ahmet, 2026-09-09
**Dal:** `auto/opencode-deepseek` · **Taban:** `9ec724a`

---

## Neden

CLAUDE.md §7.0 artık "zor iş → **tek** üst katman, **ölçülmeden seçilmez**"
diyor. Ama terazi tek sağlayıcı tanıyor (`_SAGLAYICILAR` → yalnız `deepseek`)
ve **maliyeti hiç ölçmüyor.**

Fiyat/performans sorusu bu iki eksik kapanmadan cevaplanamaz. Şu an elimizde
puan var, maliyet yok — yani "f/p" diyemiyoruz, yalnız "p" diyebiliyoruz.

**Ahmet'in onayladığı aday listesi (§9 — yeni sağlayıcı imza gerektirir,
imza 2026-09-09'da verildi):** DeepSeek (mevcut), **Kimi K2.8 (Moonshot)**,
**OpenAI (GPT)**, **Google (Gemini)**. Anthropic modelleri (Sonnet 5 / Opus 5 /
Haiku 4.5) konuşuldu ama listeye **alınmadı** — ayrı imza ister.

---

## ADIM 1 — Sağlayıcı kaydı (test-first)

`_SAGLAYICILAR` sözlüğünü genişlet. Şu an tek şekil var (OpenAI-uyumlu
`chat/completions`) ve DeepSeek onu kullanıyor.

**Şekil farkını küçümseme.** OpenAI ve Moonshot bu şekli konuşur; Google'ın
kendi API'si **konuşmaz** — OpenAI-uyumluluk ucu ayrıdır. Anthropic hiç
konuşmaz.

Bu yüzden kayıt yapısı `sekil` (şema) alanı taşısın: `"openai_chat"` bugünün
tek şekli olsun, farklı şekil gerekirse **ayrı bir fonksiyon** eklensin —
`_api_ask` içine `if saglayici == ...` dallanması **yazma**.

> **URL ve model kimliğini TAHMİN ETME.** Bir taban URL'yi ya da model adını
> doğrulamadan koda yazma. Doğrulanmamış her alanı `None` bırak ve raporda
> "Ahmet'in doldurması gerekiyor" diye işaretle. Bugünün dersi tam bu:
> uydurulan bir sayı, ölçülmüş gibi okunuyor (`FAILURES.md`, 2026-09-09).
> Bir uç noktanın gerçekten cevap verdiğini görmeden "destekleniyor" yazma.

Her sağlayıcı için: `url`, `env` (anahtar değişkeni), `model` (varsayılan),
`sekil`. Anahtar **hiçbir çıktıya sızmaz** — mevcut redaksiyon testi tüm
sağlayıcılar için parametrik hâle getirilsin.

`--saglayici` seçenekleri sözlükten türetilsin (zaten öyle), yani yeni
sağlayıcı eklemek CLI'yi kendiliğinden güncellesin.

## ADIM 2 — Maliyeti ölç (kartın asıl işi)

Şu an yalnız `completion_tokens` okunuyor. **Giriş tokenı da lazım**, yoksa
maliyet hesaplanamaz.

Her vaka kaydına ekle: `giris_token`, `cikis_token`. Sağlayıcı vermiyorsa
**`None`**, sıfır değil.

Fiyatlar **koda gömülmez** (§7.1: model adı koda gömülmez, aynı ilke).
`config/model_fiyatlari.json` oluştur:

```json
{
  "schema_version": 1,
  "guncellendi": "2026-09-09",
  "kaynak": "Ahmet elle doldurdu — saglayicinin fiyat sayfasindan",
  "fiyatlar": {
    "deepseek/deepseek-chat": {"giris_usd_1m": null, "cikis_usd_1m": null}
  }
}
```

**Sayıları sen doldurma.** `null` bırak; Ahmet doldurur. Fiyat `null` ise rapor
maliyet sütununu **"fiyat girilmedi"** yazar — tahmini bir sayı **yazmaz**.

Rapora üç yeni satır: toplam giriş tokenı, toplam çıkış tokenı, **koşunun
maliyeti** (fiyat varsa).

## ADIM 3 — Harcamadan önce tahmin (`--tahmin`)

Pahalı bir modelle 64 vaka koşturmak gerçek para. `--tahmin` bayrağı ekle:
hiçbir API çağrısı **yapmadan**, vakaların prompt uzunluğundan ve `num_predict`
bütçesinden koşunun **üst sınır** maliyetini yazsın ve çıksın.

Türkçe token oranı ölçüldü: **~2,39 karakter/token** (DeepSeek longform,
2026-09-09). Tahminde bu oran kullanılsın ve raporda **hangi orana dayandığı**
yazsın — başka sağlayıcının tokenizer'ı farklıdır, tahmin tahmindir.

> **NOT (2026-09-13, `KART_400_UYGULA_VE_TABAN.md` ADIM 4) — tek oran
> yetmez.** Ölçüldü (`automation/TERAZI_400_SONDA_2026-09-12.md` §1d ve §4):
> DeepSeek **2,41** karakter/token (ETAP 1'in ~2,40'ıyla tutarlı), llama3.1
> **~3,2–3,3**. Aynı Türkçe metin llama tokenizer'ında ~%25 daha az token
> tutuyor (40 cevapta medyan oran 0,746). Yani `--tahmin` tek bir oranla
> hesaplanamaz, **sağlayıcı başına oran** ister. Oranı ölçülmemiş bir
> sağlayıcı için tahminin başka bir sağlayıcının oranını ödünç almak yerine
> "oran ölçülmedi" demesi, bu kartın URL/fiyat kuralıyla tutarlı olur.
>
> Ayrıca kısa vakaların bütçesi 400 → **2000** oldu. Bütçe bir tavandır; üst
> sınır tahmini gerçek tüketimin çok üstünde çıkar. Ölçüm: DeepSeek sondasında
> 60 vakanın toplam çıkış tokeni **6.458**, tavan 60 × 2000 = **120.000**.
>
> Bu not uygulama değildir; ETAP 6 ayrı iştir.

## ADIM 4 — Kuru doğrulama, para harcamadan

Sahte HTTP ucuyla her sağlayıcı için uçtan uca test: alan sözleşmesi aynı mı,
anahtar sızıyor mu, yeniden deneme çalışıyor mu, `prompt_eval_ms` `None` mu.

**Gerçek koşuları BU KART YAPMAZ.** Para harcayan koşu Ahmet'in kararıdır ve
ayrıca ADIM 5'e bağlıdır.

---

## ADIM 5 — SIRALAMA UYARISI (bu kartın en önemli maddesi)

`automation/KART_DEEPSEEK_10_KUSUR.md` **PARÇA B** longform token bütçesini
değiştirmeyi öneriyor ve bu bir **ölçüm tanımı** değişikliğidir.

Bütçe önce değişmezse: N modeli 1200 token ile ölçer, sonra bütçeyi büyütür,
**hepsini yeniden koşturmak zorunda kalırız** — N kez para. Bütçe önce
değişirse: bir kez ölçeriz.

**Bu yüzden: para harcayan hiçbir koşu, longform bütçesi kararlanmadan
başlamaz.** Bu kart plumbing'i kurar; harcama ondan sonra.

Kararlandığında sıra: bütçe düzeltilir → llama3.1 **ve** DeepSeek yeni tanımla
yeniden ölçülür (taban tazelenir) → sonra yeni adaylar tek seferde ölçülür.

---

## Sınırlar

- `.env` okunmaz, yazılmaz; anahtarlar yalnız ortamdan/`.env`'den gelir (§9).
- Anthropic modelleri listede **yok** — ayrı imza.
- Kalite eşikleri, dedektörler, `passing_threshold` **değişmez.** Bu kart
  teraziyi genişletir, ayarını değiştirmez.
- Kapı: `pytest tests -q` **iki sırada**, `ruff check .` **≤ 283**.
- Auto-fix retry yok. Push yok. Bitince **DUR**.

## Bitti sayılma ölçütü

- `_SAGLAYICILAR` dört sağlayıcı taşıyor; doğrulanmamış alanlar `None` ve
  raporda "Ahmet doldurmalı" diye listeli.
- Her vaka `giris_token` / `cikis_token` kaydediyor (bilinmiyorsa `None`).
- `config/model_fiyatlari.json` var, sayılar `null`, şeması testli.
- `--tahmin` API çağrısı yapmadan üst sınır maliyet veriyor.
- Sahte uçla dört sağlayıcının hepsi uçtan uca test edilmiş; anahtar
  sızıntısı testi parametrik.
- **Hiçbir gerçek API çağrısı yapılmadı.**
- Kapı iki sırada yeşil, ruff ≤ 283.
