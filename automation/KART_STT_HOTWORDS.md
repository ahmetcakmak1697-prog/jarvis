# KART — STT'nin özel isimleri: `hotwords` ölçülmemiş bir kaçış yolu

**Kime:** Claude Code (VS Code) · **Veren:** Ahmet, 2026-09-15
**Dal:** `auto/opencode-deepseek` · **Taban:** `60b8a26`
**Sınıf:** Ölçüm + öneri. **Hiçbir varsayılan değişmez** — ölçülür, önerilir.

---

## 0. Neden — PUSULA cümlesinin kendisi bozuk

`automation/STT_TURKCE_OLCUM_2026-09-14.md` ölçtü: mevcut ayar (`small`,
beam 1) **"Hey Jarvis"i duymuyor.**

```
söylenen : Hey Jarvis, nerede kaldık?
small/1  : Heyecan mısın? Nerede kaldık?
small/5  : Heyecan mısın? Nerede kaldık?
medium/1 : Hey Jarvis, nerede kaldık?     ← doğru, ama 3671 ms
```

`CLAUDE.md` §8 PUSULA'yı tam bu cümleyle tanımlıyor. Onu duyamayan bir
asistan, cevabı ne kadar iyi olursa olsun hedefi tutturamaz.

**Doğruluğu `medium` düzeltiyor ama bütçe reddediyor:** `medium` p50 3,6 s,
1.500 ms'lik bütçenin 2,4 katı. Aynı rapor bunu gerekçesiyle eledi.

**Bu kartın sorusu:** doğruluğu modeli büyüterek değil, **çözücüye ipucu
vererek** almak mümkün mü? `faster-whisper` 1.2.1 bu makinede kurulu ve
`hotwords`, `initial_prompt`, `prefix` parametrelerinin **üçü de var**
(doğrulandı, 2026-09-15). Bu yeni bir teknoloji değil — kurulu kütüphanenin
kullanılmayan bir parametresi (§9 adopt-over-build).

## 1. Ölçülmüş taban — bu kartın karşılaştıracağı sayılar

15 cümle, Ahmet'in sesi, `%TEMP%\jarvis_stt_kayit\20260914-185533`,
referans = ekrandaki metin (hiçbir cümle düzeltilmedi), 76 kelime.

| model | beam | WER | hata/76 | p50 ms |
|---|---|---|---|---|
| `small` | 1 (**mevcut**) | 0,171 | 13 | 1252 |
| `small` | 5 | 0,132 | 10 | 1305 |
| `medium` | 1 | 0,105 | 8 | 3671 |
| `medium` | 5 | 0,079 | 6 | 3618 |

Bu sayılar bağımsız bir koşuyla %1 içinde doğrulandı (`small`/1 1243 ms,
`small`/5 1308 ms, WER birebir aynı — `FAILURES.md`, 2026-09-14).

## 2. Hangi hata `hotwords`'ün konusu, hangisi DEĞİL

**Bu ayrımı ölçmeden önce yaz, sonra tahminini sına.** Kartın asıl
entelektüel işi bu.

**Sözlük boşluğu gibi duranlar** — ipucunun yardım etmesi beklenir:

| referans | small/1 duydu |
|---|---|
| Hey **Jarvis** | Heyecan mısın |
| **DeepSeek**'in | Deep-sik'in |
| Son **commit**'te | Son komitte |

**Sözlük boşluğu OLMAYANLAR** — ipucunun yardım etmesi beklenmez:

| referans | dört kombinasyonun **dördünde de** yanlış |
|---|---|
| **Klimayı** biraz daha serin yap | Kulüme / Kulümeyi |
| **Testler** iki sırada | Sestler / Sesler |

"Klima" ve "test" Türkçe'nin sıradan kelimeleri; modelin sözlüğünde yok
değiller. `medium` bile düzeltemiyor. Bu bir **akustik/dil modeli** hatası,
kelime dağarcığı boşluğu değil. `hotwords` bunları düzeltirse tahmin
yanlıştı — **onu da yaz.**

> **"Klimayı" özellikle önemli:** `CLAUDE.md` §7.0 ev kontrolünü yerel ve
> deterministik yapmaya karar verdi. O kararın sessiz öncülü, cihaz adının
> doğru duyulması. Şu an duyulmuyor ve bu kart onu çözmeyebilir — çözmezse
> ev kontrolü cephesi için **ayrı bir sorudur**, burada kapatma.

## 3. Görev

### ADIM 1 — Sondayı genişlet, üretimdeki çağrıyı bozmadan

`scripts/olc_stt_turkce.py` → `_yaziya()` şu an şöyle çağırıyor:

```python
model.transcribe(ses, language="tr", beam_size=beam, vad_filter=True)
```

Bu, üretimdeki çağrının aynısıdır ([voice/stt.py:406](voice/stt.py:406) —
`language`, `beam_size=1` (:409), `vad_filter=True` (:415)). **Bu eşliği
koru:** `_yaziya`'ya `hotwords` (ve/veya `initial_prompt`) geçilebilir olsun,
verilmediğinde davranış **bugünküyle birebir aynı** kalsın.

`vad_filter=True`'nun kodda yazılı bir gerekçesi var (Whisper saf sessizliğe
metin **uyduruyor**, :410-414). **Kapatma.**

### ADIM 2 — Matris: ipucu var / yok

Yalnız `small` üzerinde — `medium` bütçe gerekçesiyle zaten elendi, yeniden
ölçme.

| # | ayar | ipucu |
|---|---|---|
| 1 | `small`/1 | yok (**taban**, 0,171 olmalı) |
| 2 | `small`/1 | `hotwords` |
| 3 | `small`/5 | yok (**taban**, 0,132 olmalı) |
| 4 | `small`/5 | `hotwords` |
| 5 | `small`/1 | `initial_prompt` |

**Taban satırları koşulmalı ve 0,171 / 0,132 çıkmalı.** Çıkmıyorsa ölçüm
düzeneği değişmiş demektir — **DUR ve söyle**, ipucunu yorumlama.

İpucu listesi kayıtlardaki gerçek kelimelerden: `Jarvis`, `DeepSeek`,
`Ollama`, `commit`, `klima`. Uydurma kelime ekleme.

`initial_prompt` ile `hotwords` **aynı şey değildir** (biri bağlam metni,
öbürü sözcük listesi); ikisini tek satırda karıştırma.

### ADIM 3 — Cümle cümle karşılaştır, toplamla yetinme

**Kartın en önemli maddesi.** Bir ipucu çözücüyü yanlı hâle getirir ve
**önceden doğru olan cümleleri bozabilir.** Toplam WER düşerken üç cümlenin
düzelip iki cümlenin bozulması, "iyileşme" değil **takas**tır.

Raporda her ipucu satırı için:

1. Toplam WER ve p50/p90 süre.
2. **Düzelen cümleler** (no + önce/sonra metin).
3. **Bozulan cümleler** (no + önce/sonra metin). Sıfırsa "sıfır" yaz.
4. §2'deki tahmin tuttu mu — özel isimler düzeldi mi, "Klimayı"/"Testler"
   düzeldi mi.

### ADIM 4 — Öneri (uygulama yok)

ETAP 1 şablonu: ölçüldü mü, bütçeye sığıyor mu, oynaklık payı var mı.

`hotwords` bir çözücü ipucudur; maliyetinin ~0 ms olması **beklenir** ama
**ölç** — beklenti ölçüm değildir.

Öneri olumluysa: `hotwords`'ün `FasterWhisperTranscriber`'a nasıl
geçirileceği yazılır (`__init__` parametresi + `build_default_voice_io`),
**ama bu kartta uygulanmaz.** `beam_size` de aynı durumda ve aynı yerde
(`:409` kodda sabit) — ikisi tek bir kartta birlikte parametreye çevrilmeli,
ayrı ayrı değil.

---

## 4. Ölçüm hijyeni — iki tuzak, ikisi de bu repoda yaşandı

1. **Ölçüm sırasında makine boş olmalı.** Süre ölçülüyor; başka bir iş
   koşarsa sayı şişer.
2. **İki PID çekişme DEĞİLDİR.** Windows'ta `.venv\Scripts\python.exe` bir
   başlatıcıdır ve gerçek yorumlayıcıyı **alt süreç** olarak açar; süreç
   listesinde aynı komut iki kez görünür. Çekişme sanmadan önce
   `ParentProcessId` oku. Bu tuzak 2026-09-14'te bir saat ve bir koşu yedi
   (`FAILURES.md`).

## 5. Sınırlar

- `voice/stt.py`'de **hiçbir varsayılan değişmez.** `vad_filter` kapatılmaz,
  `beam_size` parametreye çevrilmez, `model_size` değişmez.
- `medium` yeniden ölçülmez (bütçeyle elendi, gerekçesi yazılı).
- Ses kayıtları **repoya girmez**; raporda yalnız metin.
- GPU kurulumu bu kartın konusu değil (`cublas64_12.dll` yok — ayrı karar).
- `agent/`, `eval/`, `agents/persona.py`: dokunma.
- Kapı: `pytest tests -q` **iki sırada**, `ruff check .` **≤ 283**.
- Push yok. Bitince **DUR**.

## 6. Bitti sayılma ölçütü

- `_yaziya` ipucu alabiliyor; **ipucusuz davranış birebir aynı** (taban
  satırları 0,171 / 0,132 çıktı).
- Beş satırın WER'i ve süresi yan yana.
- Her ipucu satırında **düzelen ve bozulan cümleler ayrı ayrı** listeli.
- §2'deki tahminin tuttuğu ya da tutmadığı yazılı.
- "Hey Jarvis" cümlesinin ne olduğu **açıkça** yazılı — düzeldi mi, hayır mı.
- Hiçbir varsayılan değişmedi (`git diff` yalnız sonda + rapor).
- Kapı iki sırada yeşil, ruff ≤ 283.
