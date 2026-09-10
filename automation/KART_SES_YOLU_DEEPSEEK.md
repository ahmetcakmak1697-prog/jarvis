# KART — Ses yolunu DeepSeek'e bağla: PUSULA'yı canlıya al

**Kime:** Claude Code (VS Code) · **Veren:** Ahmet, 2026-09-10
**Dal:** `auto/opencode-deepseek` · **Taban:** `bfb4581`
**Sınıf:** A19 — mimari yön değişikliği. **Ahmet imzaladı** (2026-09-10),
`CLAUDE.md` §7.0'ın uygulanmasıdır.

---

## 0. Neden — ölçüldü, tercih edilmedi

Ses yolunun kurduğu system prompt (5.976 karakter, `## GUNCEL PROJE DURUMU`
bloğu **içinde**) aynen DeepSeek'e verildi. Cevap:

> *"Efendim, bu konuşmanın kaydına erişimim yok — o yüzden 'nerede kaldık'
> sorusuna hafızamdan cevap veremem. Ama elimdeki güncel proje durumuna göre
> özetleyeyim. Son commit'lerde terazi zinciri durmuş: yeni tanımda llama
> 64'te 52, DeepSeek 64'te 53 almış... Yol haritasında on dört adımın on üçü
> tamam; kalan tek adım Faz-3-E1... insan onayı bekleyen bir madde var."*

**His-testi (§8) geçti.** Ve kendiliğinden doğru ayrımı yaptı: konuşma
kaydına erişimi yok (doğru), proje durumu bloğu elinde (doğru).

Aynı prompt, aynı blok, aynı talimat ile `llama3.1` **üç denemede üçünde de**
*"Anlık proje durumuna erişimim yok"* dedi (Codex ölçümü, `bfb4581`).

Yani talimat doğru, kod yolu doğru, veri yerinde. **Eksik olan modelin
yeteneği.** PUSULA bir prompt kusuru değil.

---

## 1. BU KART NE DEĞİL — karıştırma

`automation/CODEX_IKI_BEYIN_FIZIBILITE_2026-09-09.md` ses yolunu
`AssistantExecutor` hattına devretmenin bedelini ölçtü ve somut bir güvenlik
gerilemesi buldu: **"internete çıkma" talimatının kaybı.**

**Bu kart onu YAPMIYOR.** `LocalJarvisAgent.chat()` yerinde kalıyor —
egress kapısı, `_yerel_kal_istendi()`, araç tespiti, proje bağlamı, ses
yönergesi, hepsi aynen duruyor. Değişen tek şey: **metni hangi modelin
ürettiği.**

Bu ayrım kartın güvenliğinin temelidir. `AssistantExecutor`'a,
`LocalFirstRouter`'a, `ModelCascade`'e **dokunma.** Dokunman gerektiğini
düşünürsen **dur ve söyle** — o ayrı bir karttır ve ayrı imza ister.

---

## 2. Bu değişikliğin AÇTIĞI üç delik — üçü de kapatılacak

Bunlar spekülatif değil; ikisi bugün ölçüldü.

### 2a. Her sohbet turu artık bir egress — ve system prompt de gidiyor

`CLAUDE.md` §7.1: *"Bulut temelli mimaride bu madde daha kritiktir: artık
her sohbet turu bir egress'tir."*

Giden şey yalnız kullanıcının sorusu değil: **proje bağlamı da gidiyor** —
commit mesajları, `HUMAN_NEEDED` maddeleri, yol haritası durumu, ve
`self.memory.get_context_for_prompt()` çıktısı (Ahmet hakkında öğrenilenler).

**Ölçülmüş boşluk:** `voice/voice_loop.py` `RedactionGuard`'ı **çıkan sese**
uyguluyor. **Dışarı giden prompt'a hiçbir şey uygulanmıyor** — bugüne kadar
gerek yoktu, çünkü model yereldi.

**Gerekli:** dış modele gitmeden önce **giden yük** veri sınıfı denetiminden
geçer. Hassas içerik varsa tur dışarı çıkmaz — yerelde kalır ya da reddedilir.
Hangisi olduğunu ölç ve seç; sessizce göndermek yok.

Bu maddenin testi kartın en önemli testidir.

### 2b. "Yerel kal" artık modeli de kapsamalı

`_yerel_kal_istendi()` bugün **araçları** engelliyor (web arama vs.). Ama
model artık uzaktaysa, *"internete çıkma"* diyen kullanıcı **modelin kendisinin
de yerel kalmasını** kastediyor.

**Gerekli:** `_yerel_kal_istendi()` doğruysa tur **zorunlu olarak yerel
modele** düşer. Kullanıcı bunu duyar (§7.1 human override her katmandan
üstündür).

### 2c. Sessiz geri düşme yasak

İnternet kesikse ya da API hata verirse yerel modele düşmek doğru davranıştır
(§7.0: "internet kesikse sohbet durur" bedeli kabul edildi — ama çökme değil,
düşme).

**Ama sessiz olmaz.** Sessizce llama'ya düşmek, PUSULA'nın sessizce yeniden
kırılması demektir — bugün öğrendiğimiz tam olarak bu. Kullanıcı hangi
modelde olduğunu **bilecek**.

---

## 3. Görev

### ADIM 1 — Model adı koda gömülmez (§7.1)

Değişiklik `config/runtime_profiles.json` / `ModelRegistry` üzerinden olur.
`local_agent.py` içine `"deepseek-chat"` yazma.

`config/runtime_profiles.json` **gerçek yapılandırma dosyasıdır** ve imza
listesindeydi — bu kartla imzalandı, ama **yalnız bu değişiklik için.**
Başka alanına dokunma; diff'i raporda göster.

### ADIM 2 — Test-first, üç deliğin üçü için

Önce kırmızı gör:

- **2a:** hassas içerik taşıyan bir bağlamla tur, dış sağlayıcıya
  **0 çağrı** yapmalı.
- **2b:** `"internete cikma, nerede kaldik"` → dış sağlayıcıya **0 çağrı**,
  cevap yine gelmeli (yerel model).
- **2c:** dış sağlayıcı hata verince tur **yerel cevapla** dönmeli **ve**
  kullanıcı bilgilendirilmeli. Sessiz düşme testi kırmızı yanmalı.

Dış çağrı sahte uçla sayılır; testler ağa çıkmaz.

### ADIM 3 — Canlı doğrulama: PUSULA his-testi

`python main.py` ile ya da eşdeğer bir sonda ile **"nerede kaldık"** sorulur.

**Kabul ölçütü sayı değil, cümledir:** cevap o anki gerçek `git log` ve
`roadmap_state.json` durumunu anlatıyor mu? Cevabı **olduğu gibi rapora
yapıştır.** "Test geçti" yetmez (§8 his-testi).

### ADIM 4 — Gecikmeyi ölç

`scripts/olc_llm_anatomisi.py` zaten var. Aynı üç soru sınıfını **yeni
modelle** koştur ve dünkü llama sayılarının yanına koy:

```
kısa olgusal    464 ms  ->  ?
proje durumu  1.160 ms  ->  ?
uzun anlatım 15.890 ms  ->  ?
```

Ağ gidiş-dönüşü eklenir ama üretim hızı ve ilk-token davranışı farklıdır;
**yön belli değil, ölç.**

### ADIM 5 — Harcama görünür olsun (§7.0b)

§7.0b: *"Pahalı bir sağlayıcı, kapı bağlanmadan bağlanmaz."* DeepSeek pahalı
değil, ama sürekli açık bir ev asistanı **yeni bir harcama deseni**.

Bu kart hard limit istemiyor. İstediği: **günlük çağrı sayısı ve token
toplamı sayılsın ve görünür olsun.** Ölçülmeyen harcama, yönetilemeyen
harcamadır. `CostLedger(daily_limit=0)`'ın "unlimited" döndüğü ölçüldü
(`cost_ledger.py:78`) — sayaç bunu bilerek kullanabilir, ama **sayı bir
yerde yazmalı.**

---

## 4. Sınırlar ve durma koşulları

- **DOKUNMA:** `AssistantExecutor`, `LocalFirstRouter`, `ModelCascade`,
  `agents/persona.py`, kalite dedektörleri, `eval/` eşikleri.
- `.env` okunmaz, yazılmaz (§9). Anahtar ortamdan gelir.
- Yerel modeller **kurulu kalır** — §7.0 "geri dönülebilir" diyor.
- Kalite tabanı bu kartla **oynatılmaz.** Terazi ayrı bir iştir.
- Bir sözleşme testi seni engellerse (§13.1): **DUR**, sor, gevşetme.
- Kapı: `pytest tests -q` **iki sırada**, `ruff check .` **≤ 283**.
- **Üç delikten biri kapatılamıyorsa: DUR.** Yarım bağlanmış bir bulut
  hattı, bağlanmamış olandan tehlikelidir.
- Push yok.

## 5. Bitti sayılma ölçütü

- Model seçimi yapılandırmadan geliyor; `local_agent.py`'de model adı yok.
- 2a / 2b / 2c için testler var, üçü de önce kırmızı görüldü.
- **Raporda gerçek bir "nerede kaldık" cevabı var** ve his-testini geçiyor.
- Gecikme üç sınıf için ölçüldü ve dünkü sayıların yanında.
- Günlük çağrı/token sayacı çalışıyor ve bir yere yazıyor.
- Kapı iki sırada yeşil, ruff ≤ 283.
- `git diff` yalnız isimli dosyaları gösteriyor.
