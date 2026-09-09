# KART — PUSULA kırık: persona modele kaçış cümlesini öğretiyor

**Kime:** Codex (GPT-6 Astra) · **Veren:** Ahmet, 2026-09-10
**Dal:** `auto/opencode-deepseek` · **Taban:** `f1aa069`

---

## 0. Neden bu iş her şeyden önce geliyor

`CLAUDE.md` §8 projenin **tek cümlelik hedefini** tanımlıyor:

> Ahmet'in "Hey Jarvis, nerede kaldık?" sorusuna ~1,5 saniye içinde, Türkçe
> sesli ve **repo'nun o anki gerçek durumunu** yansıtan bir yanıt vermek.

Bu soru şu anda şu cevabı alıyor:

> *"Anlık proje durumuna erişimim yok."*

Yani PUSULA'nın kendisi kırık. Aylardır ölçtüğümüz gecikme, kalite ve mimari
— hepsi bu cümlenin hizmetindeydi ve cümle çalışmıyor.

---

## 1. Teşhis — ölçüldü, tahmin edilmedi

Üç şey doğrulandı (2026-09-10, danışman Claude):

**(a) Veri yerinde.** `LocalJarvisAgent._proje_ctx_guncel(Path('.'))`
**1436 karakter** döndürüyor ve içinde bugünkü commit'ler var
(`f1aa069`, `6291ee3`, `9ec724a`), `HUMAN_NEEDED` maddeleri, yol haritası
durumu. Blok `## GUNCEL PROJE DURUMU` başlığıyla geliyor.

**(b) Model küçüklüğü değil.** `ModelCascade.select("nerede kaldik")` →
`{'level': 'L2', 'model': 'local_main', 'reason': 'default'}`. Soru
`llama3.1`'e gidiyor, `qwen2.5`'e değil.

**(c) Persona kaçış cümlesini harfiyen öğretiyor.**

```
agents/persona.py:157-158
  Bilmediğin bir proje durumunu **uydurmazsın**. Bir dosyaya ya da kayda
  erişimin yoksa "erişimim yok" dersin.
```

Modelin ürettiği cümle ile prompt'taki cümle **aynı.** Model bağlamı
görmemezlikten gelmiyor; **koşulsuz yazılmış bir talimatı uyguluyor.**

Bu, senin PARÇA A'da düzelttiğin kusurun tam kardeşi: prompt'ta adı geçen
kalıp, modelin eline tutuşturulur. Orada "size yardımcı olmaktan mutluluk
duyarım"dı; burada "erişimim yok".

---

## 2. TUZAK — bu satırlar boşuna yazılmadı

**Naif düzeltme projeyi geriye atar.** Bu satırlar `FAILURES.md` ve A4
kaydındaki gerçek bir olaydan doğdu: model, eskimiş/eksik proje durumunu
**uydurarak** anlatıyordu ve canlı testte *"tasarım aşamasındayız"* dedi.
Halüsinasyon değildi — veriye sadakatti, ama veri yanlıştı.

Yani "modele *erişimin var* de" demek o deliği yeniden açar.

**Doğru düzeltmenin şekli koşulsallıktır, silme değildir:**

> Blok verilmişse ona dayan. Verilmemişse erişimin olmadığını söyle.

Talimat kalır, **koşula bağlanır.**

### 2a. Bir ayrım daha var, karıştırma

`persona.py:93` ayrı bir şey söylüyor:

```
Elinde gerçek kayıt yoksa "bu konuşmanın kaydına erişimim yok" de.
```

Bu satır **DOĞRU ve dokunulmaz.** Model gerçekten geçmiş oturumların
konuşma kaydına sahip değil. Kusur `157-158`'de: orası **proje durumu**
hakkında ve proje durumu bloğu modele **veriliyor.**

İkisini aynı düzeltmeye sokma. Konuşma kaydı ≠ proje durumu.

---

## 3. Görev

### ADIM 1 — Kusuru deterministik olarak üret, KIRMIZI GÖR

Önce bir test yaz ve düşürdüğünü **gör**. İki katmanı ayrı ayrı sına:

- **Prompt katmanı:** birleştirilmiş sistem prompt'u `## GUNCEL PROJE DURUMU`
  bloğunu **içeriyor mu?** (Cevaba değil, prompt'a bak. Bu, "veri yerinde"
  iddiasını ses yolunun kendi kod yolunda kilitler.)
- **Davranış katmanı:** bloğa canlı bir işaretçi enjekte et (ör. sahte bir
  commit özeti) ve modelin cevabının o işaretçiye **atıfta bulunduğunu**
  iddia et; ve "erişimim yok" kalıbını **içermediğini**.

Davranış testi canlı model ister. Belirlenimsizliği azalt: `temperature`
düşük, tek soru, ve kabul ölçütü "kelimesi kelimesine şu cümle" değil
"şu işaretçi geçiyor + şu kaçış kalıbı geçmiyor" olsun.

Model çağıramıyorsan davranış testini `xfail(strict=True)` ile görünür
bırak ve **sebebini yaz** — sessizce atlama.

### ADIM 2 — Yalnız 157-158'i koşullu hâle getir

Cerrahi ol (§3). Komşu satırları, `[VARSAYIM]` disiplinini, satır 90 ve
93'ü **değiştirme**.

Düzeltmeyi yazarken kendine sor: *"Bu cümle, blok verilmediğinde hâlâ
doğru davranışı üretir mi?"* Üretmiyorsa deliği açtın demektir.

### ADIM 3 — Deliğin kapalı kaldığını KANITLA

Bu adım isteğe bağlı değil.

1. **Blok yokken** eski davranış sürüyor mu? Boş/eksik bağlamla model hâlâ
   uydurmuyor mu? Bunu bir testle kilitle — asıl korunan sözleşme budur.
2. **64 vakalık takım:** `grounding` kategorisi **5/5** kalmalı. O kategori
   tam olarak bu disiplini ölçüyor. Düşerse düzeltme yanlıştır, geri al.
3. **llama3.1 tabanı:** kayıtlı koşu **49/64** üretmeye devam etmeli.
   Persona iki modele birden hizmet ediyor.
4. **DeepSeek:** PARÇA A sonrası koşu 56/64 idi; düşmemeli. Ama **56'yı yeni
   taban ilan etme** — o koşuda 5 vaka düzelip 3 vaka bozulmuştu, net +2
   A11'in gürültü zarfının içinde.

### ADIM 4 — Rapor

`automation/CODEX_PUSULA_2026-09-10.md`:

- Kırmızı görülen testler ve ne iddia ettikleri
- Değişen satırlar ve **neden bu şekil** seçildi
- Dört doğrulamanın sayıları
- **His-testi (§8):** cevap artık *"repo'yu şu an açıp `git log` + son
  BLACKBOX event'ine bakan biri gibi"* konuşuyor mu? Bir örnek cevabı
  olduğu gibi yapıştır. Değilse kusur kapanmamıştır, "test geçti" yetmez.

---

## Sınırlar ve durma koşulları

- `tests/test_local_agent_grounding.py` bu dizeleri sabitliyor olabilir. Bir
  test seni engellerse **bu bir sözleşme değişikliğidir** (§13.1): **DUR**,
  `AHMET_ONAYI_BEKLEYENLER.md`'ye yaz, kendi başına gevşetme.
- Kapı: `pytest tests -q` **iki sırada**, `ruff check .` **≤ 283**.
- **Kapı düşerse ya da ADIM 3'ün dört doğrulamasından biri kırmızı yanarsa:
  DUR.** Auto-fix retry yok (§9).
- Push yok. Yalnız isimli dosya `git add`.

## Bitti sayılma ölçütü

- Prompt katmanı testi ve davranış testi var; ikisi de önce kırmızı görüldü.
- `persona.py` diff'i **yalnız 157-158 civarına** dokunuyor.
- grounding 5/5, llama 49/64, DeepSeek ≥56/64, kapı iki sırada yeşil.
- Raporda **gerçek bir cevap örneği** var ve his-testini geçiyor.
