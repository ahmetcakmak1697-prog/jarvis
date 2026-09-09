# KART — İki beyin: birleştirme fizibilitesi (SALT-OKUNUR DENETİM)

**Kime:** Codex (GPT-6 Astra, VS Code terminali) · **Veren:** Ahmet, 2026-09-09
**Dal:** `auto/opencode-deepseek` · **Taban commit:** `8c428e2`

> **Bu kart KOD YAZDIRMAZ.** Çıktı tek bir rapor dosyasıdır. Tek satır
> kaynak kodu değiştirirsen kart ihlal edilmiştir — dur ve söyle.
> Gerekçe: birleştirmenin **kendisi** mimari yön değişikliğidir
> (`automation/AHMET_ONAYI_BEKLEYENLER.md` → A19) ve Ahmet'in imzasını
> bekler. Senin işin imzayı **bilgilendirmek**, imzanın yerine geçmek değil.

---

## Ölçülmüş olgu (2026-09-09, doğrulanabilir)

JARVIS'in iki ayrı yürütme hattı var ve karar katmanını paylaşmıyorlar:

```
main.py (260 satır) — GÜNLÜK SES YOLU
  voice.voice_loop.build_default_voice_io
  agent.local_agent.LocalJarvisAgent
  memory.life_graph.LifeGraph
  → LocalFirstRouter YOK · CostLedger YOK · KnowledgeCard* YOK · ModelCascade YOK

tools/telegram_agent.py (1541 satır) — TELEGRAM YOLU
  _build_assistant_executor()  (satır 1356)
  → LocalFirstRouter (1371, 1381) + KnowledgeCardStore + CostLedger
  → agents/assistant_executor.py:103 ikinci bir LocalFirstRouter kuruyor
```

`LocalFirstRouter` tüm depoda yalnız bu iki yerde **kuruluyor**
(`tools/telegram_agent.py:1371`, `agents/assistant_executor.py:103`).
`main.py`, `agent/`, `voice/` altında sıfır referans.

Sonuç: yerel-önce cascade, maliyet kapısı, bilgi kartları, redaction
politikası ve deterministik routing — **hepsi Telegram'a özel.** Ahmet
mikrofona konuştuğunda bunların hiçbiri çalışmıyor.

---

## Sorun: hangi soru sorulmuyor

Kolay soru: "ses yolu `AssistantExecutor`'ı çağırsın, bitti."
**Bu soruyu sorma.** Çünkü cevabı zaten "evet" ve hiçbir şey öğretmiyor.

Sorulacak soru: **"Bunu yaparsak ne bozulur, ne yavaşlar, ne kaybolur?"**

Sen bu depoda 12 gerçek kusur buldun (B01–B12) çünkü "bu çalışır mı" diye
değil "bu nerede yalan söylüyor" diye baktın. Aynı bakışı buraya uygula.

---

## Görev — dört soru, hepsi kanıtla

Çıktı: `automation/CODEX_IKI_BEYIN_FIZIBILITE_2026-09-09.md`

### S1 — Arayüz uyuşmazlığı

`LocalJarvisAgent.ask()` (veya ses yolunun çağırdığı ne ise) ile
`AssistantExecutor.ask()` ne **döndürüyor** ve ne **bekliyor**?

Yan yana yaz: imza, dönüş tipi/anahtarları, hata davranışı, durum
(history/memory) sahipliği. Nerede uyuşmuyorlar?

Özellikle: ses yolu `str` bekliyorsa ve executor `dict` döndürüyorsa,
**cevabı kim düzleştirir ve `source`/`ok` alanları nereye gider?**
`source == "external_blocked"` ve `ok is False` durumunda kullanıcı sesli
olarak ne duyar? (Bu bir tasarım sorusu — cevabı sen vermiyorsun, ama
**kararın var olduğunu** göstermek zorundasın.)

### S2 — Gecikme bedeli

Ses yolunun ölçülmüş p50'si **10.954 ms** (kuru mod, `chat()` süresi;
`automation/`'daki B12 ölçümü). PUSULA hedefi **1500 ms**.

`AssistantExecutor` hattına geçmek bu sayıyı **hangi yönde** ve **kaç ms**
oynatır? Kanıtla, tahmin etme:

- Router kaç I/O yapıyor? (vektör arama, kart deposu okuma, ledger dosyası)
- Cascade **kaç LLM çağrısı** yapabilir? En kötü durumda kaç?
- Bunların hangisi ses yolunda **her turda** çalışır, hangisi koşullu?

Ölçemediğin şeyi `[ÖLÇÜLEMEDİ]` diye işaretle. Uydurma sayı yazma.

Bu soru kartın **en önemli** sorusu: birleştirme kaliteyi artırıp
kullanılabilirliği öldürebilir. O takas ölçülmeden imzalanamaz.

### S3 — Ne kaybolur

Ses yolunda **olup** executor hattında **olmayan** ne var?

Bilinen aday: `agent/local_agent.py` içindeki egress kapısı
(`_egress_kapisi`, `_yerel_kal_istendi`, `_pdf_istegi_mi`) ve
`_proje_ctx_guncel` canlı proje bağlamı. Bunlar B03/A-04 turlarında
**oraya** eklendi. Executor hattında karşılıkları var mı?

Yoksa: birleştirme sessizce bir **güvenlik gerilemesi** olur. Bunu bul
ve adını koy. Yoksa yok de, ama bak.

Ters yön de geçerli: executor hattında olup ses yolunda olmayan
korumalar (redaction, bütçe) birleştirmede ses yoluna **gelir mi**,
yoksa yol ayrımında mı kalır?

### S4 — En küçük dürüst adım

Tam birleştirme büyük. **Ölçülebilir, geri alınabilir, tek commit'lik**
en küçük adım nedir?

Kendi önerini yaz ve **kendi önerini eleştir**: bu adım atıldıktan sonra
geri dönmek ne kadar pahalı? Yarım birleşmiş bir sistem, iki ayrı
sistemden daha mı kötü?

En az iki seçenek sun (ör. "executor'ı ses yoluna bağla" vs. "ses
yolunun eksik parçalarını executor'a taşı") ve **hangisini neden**
önerdiğini yaz. Ahmet iki seçeneği de görecek.

---

## Sınırlar

- **Salt-okunur.** `git diff` sonunda boş olmalı. Yalnız rapor dosyası eklenir.
- Bulgular **kanıtlı**: `dosya:satır` ver. Kanıtı olmayan her cümle
  `[EMİN DEĞİLİM]` taşır.
- Kartın kendi çerçevesini sorgulamakta serbestsin: "iki beyin" tanımı
  yanlışsa **söyle**, ölçümle çürüt. Kartı savunmak senin işin değil.
- Auto-fix retry yok (§9): bir sorun bulunca düzeltip devam etme, yaz.
- Push yok.

## Bitti sayılma ölçütü

- `automation/CODEX_IKI_BEYIN_FIZIBILITE_2026-09-09.md` var; S1–S4
  cevaplı, her iddia `dosya:satır` kanıtlı.
- S2'de en az bir **gerçek ölçüm** var (tahmin değil) ya da neden
  ölçülemediği yazılı.
- S4 iki seçenek ve gerekçeli bir öneri içeriyor.
- `git status` yalnız o dosyayı gösteriyor.
- Rapor tek commit: `docs(fizibilite): iki beyin birlestirme -- olcum, kod degismedi`
