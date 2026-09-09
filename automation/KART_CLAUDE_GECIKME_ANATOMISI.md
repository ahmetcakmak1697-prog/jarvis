# KART — Gecikmenin anatomisi: 10.954 ms nereye gidiyor?

**Kime:** Claude Code (VS Code) · **Veren:** Ahmet, 2026-09-09
**Dal:** `auto/opencode-deepseek` · **Taban commit:** `8c428e2`

---

## Neden bu iş, kuyruktan önce

Kuyruk (`automation/IMZASIZ_IS_KUYRUGU.md` K4–K13) meşru bakım işi ama
hiçbiri kullanıcının duyduğu cevabı iyileştirmiyor. Bu iş iyileştiriyor.

**Ölçülmüş olgu:** ses yolunun p50'si **10.954 ms**, PUSULA hedefi
**1500 ms** — yaklaşık **7 kat** üstünde. Ve bu sayının **içi bilinmiyor.**

Daha önce "darboğaz prompt işleme" diye bir teşhis yazıldı ve o teşhis
**geri alındı** — çıkarım, ölçüm gibi sunulmuştu. Sayı duruyor, teşhis
durmuyor. Bu kart o boşluğu kapatıyor: **teşhis yok, ölçüm var.**

Optimizasyon kararı (daha küçük model mi, daha kısa cevap mı, akışlı TTS
mi, mimari mi) tamamen bu dağılıma bağlı. Dağılım bilinmeden yapılan her
optimizasyon kumar.

---

## ADIM 1 — Ölçüm aracı (test-first)

`scripts/olc_llm_anatomisi.py` yaz. Mikrofon **gerektirmez** — girdi sabit
metin. Ahmet'in evde olmasını beklemez.

Tek turu şu bileşenlere ayır ve **her birini ayrı ölç**:

| Bileşen | Ne ölçülüyor |
|---|---|
| `prompt_insa_ms` | persona + proje bağlamı + hafıza + geçmiş birleştirme |
| `arac_tespiti_ms` | `_detect_tool` + egress kapısı |
| `model_prompt_eval_ms` | Ollama'nın `prompt_eval_duration` alanı |
| `model_uretim_ms` | Ollama'nın `eval_duration` alanı |
| `uretilen_token` | `eval_count` |
| `sonrasi_ms` | hafızaya yazma, kayıt, dönüş |
| `toplam_ms` | uçtan uca |

**Kritik kural:** her alanın adı **ölçtüğü şey** olsun. B12'de
`first_token_ms` diye bir alan vardı ve `prompt_eval_duration`
ölçüyordu — TTFT değil. Aynı hataya düşme. Ölçemediğin bileşen için
alan **`None`** döner, `0` değil.

Türkçe gotcha: `prompt_eval_duration` ve `eval_duration` Ollama'da
**nanosaniye**. Bölmeyi unutma, testle kilitle.

Donanım enjekte edilebilir olsun (B12'deki `olc_tek_tur` deseni):
sahte bir model istemcisiyle test edilebilmeli, gerçek Ollama olmadan.

**Önce düşen testi yaz, kırmızı olduğunu GÖR.** En az:
- ns→ms dönüşümü doğru
- eksik alan `None` dönüyor, `0` değil
- bileşenlerin toplamı `toplam_ms`'i **aşmıyor** (üst üste binme yok)
- sahte istemciyle uçtan uca çalışıyor

## ADIM 2 — Canlı ölçüm

`llama3.1:latest` ile en az **5 tur**, üç farklı soru sınıfı:

1. Kısa olgusal (*"saat kaç"* gibi, araç tetiklemeyen)
2. Proje durumu (*"nerede kaldık"* — PUSULA sorusu, tam bağlam yükü)
3. Uzun anlatım (kasıtlı olarak uzun cevap üretecek soru)

Her sınıf için p50 ve dağılım. Çıktı:
`automation/GECIKME_ANATOMISI_2026-09-09.md`.

**Raporda cevaplanacak tek soru:** 10.954 ms'nin **kaçı** üretim
(`eval_duration`), kaçı prompt işleme, kaçı bizim kodumuz?

Ve türev sayı: **token/saniye** ve **üretilen ortalama token sayısı.**
Eğer model 400 token üretiyorsa ve hızı 40 tok/s ise, darboğaz mimari
değil **cevap uzunluğudur** — ve bu tamamen farklı bir çözüm demektir.

## ADIM 3 — Hüküm verme, seçenek sun

Raporun sonunda **karar verme.** Ölçüme dayanan seçenekleri maliyetiyle
listele:

- Cevap uzunluğunu sınırlamak (kalite tabanı 49/64'ü nasıl etkiler?)
- Daha küçük model (`llama3.2` 2 GB kurulu — ölçülmedi)
- Akışlı TTS: ilk cümle bitince konuşmaya başlamak
  → **algılanan** gecikme düşer, toplam düşmez. Bu bir mimari
  değişiklik → imza gerektirir, uygulama.
- Prompt küçültmek (proje bağlamı her turda mı gerekli?)

Her seçenek için: **hangi ölçüm bunu destekliyor** ve **ne feda edilir**.
Desteklenmeyen seçeneği yazma.

---

## Sonra: kuyruktan devam

Bu kart bitince **DUR** (§9). Ahmet raporu okuyacak.

Onaydan sonra kuyruk kaldığı yerden: **K4** (bayat envanter — `gui.py`
hâlâ canlı giriş noktası olarak listeli), sonra K13, K6, K5.

---

## Sınırlar

- Yeni bağımlılık yok. Yeni sağlayıcı yok. Ollama'nın zaten döndürdüğü
  alanlar kullanılıyor.
- `config/runtime_profiles.json` **değişmez** (imza — A2/A19 sınıfı).
  Ölçüm için başka model denenecekse yalnız betiğe parametre olarak
  geçilir, profil dosyasına dokunulmaz.
- Kapı: `pytest tests -q` **iki sırada**, `ruff check .` **≤ 283**.
- Commit yalnız isimli dosya; mesajda **ne ölçüldüğü** yazılı.
- Auto-fix retry yok. Push yok.

## Bitti sayılma ölçütü

- `scripts/olc_llm_anatomisi.py` var, testleri var, kırmızı görüldü.
- `automation/GECIKME_ANATOMISI_2026-09-09.md` üç soru sınıfı × 5 tur
  ölçümünü taşıyor; her bileşen ayrı sayı.
- "10.954 ms'nin kaçı üretim" sorusu **sayıyla** cevaplı.
- Seçenekler ölçüme bağlı, hüküm verilmemiş.
- Kapı iki sırada yeşil, ruff ≤ 283.
