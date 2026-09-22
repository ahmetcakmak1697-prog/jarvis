# KART — Vektör hafızayı bağla (ADIM 4), mevcut onay hattını BAYPAS ETMEDEN

**Kime:** Claude Code (VS Code) · **Veren:** Ahmet, 2026-09-22
**Dal:** `auto/opencode-deepseek` · **Taban:** `e9ca2ac`
**Sınıf:** Bağlama + ölçüm. Yazma politikası **değişmez** (§7.1a).

---

## 0. Neden bu kart, dışarıdan gelen ADIM 4 metninin yerine

Dışarıdan gelen plan şunu söylüyordu:

> *"Cevap üretildikten sonra soru+cevabı vektör deposuna yaz."*

**Bu yapılmayacak.** Ölçüldü (2026-09-22): repoda zaten bir onay hattı var
ve her halkası yazmadığını kendi docstring'inde söylüyor:

| dosya | kendi ifadesi |
|---|---|
| `agents/answer_crystallizer.py` | *"Never writes to VectorMemory"* — aday kart üretir |
| `agents/episodic_buffer.py` | *"No VectorMemory writes"* |
| `agents/knowledge_card_editor.py` | *"No VectorMemory writes"* |
| `agents/knowledge_card_promoter.py` | **onaylanmış** kartı `VectorMemory`'ye geçirir |

Her turu otomatik yazmak bu hattın tamamını baypas eder ve `CLAUDE.md`
§7.1 ile **§7.1a**'yı (Ahmet'in 22.09 kararı) çiğner.

**Planın bir yanlışı daha:** sınıfların `jarvis_brain.py` içinde olduğunu
söylüyor. Değiller — `tools/vector_memory.py` (`VectorMemory`) ve
`agents/memory_retrieval_policy.py` (`MemoryRetrievalPolicy`).
`jarvis_brain.py` onları yalnızca **import ediyor** (satır 58-67).

## 1. Ölçülmüş önkoşullar — hepsi sağlanıyor

| önkoşul | durum |
|---|---|
| `chromadb` | ✅ 1.5.9 kurulu |
| `sentence_transformers` | ✅ 5.6.0 kurulu |
| Gömme modeli (çok dilli, Türkçe) | ✅ `paraphrase-multilingual-MiniLM-L12-v2`, 959 MB, HF önbelleğinde |
| `HF_*_OFFLINE` bayrakları | `config.py:17-19` — **yeri değişmez** (§9); model önbellekte olduğu için gerek de yok |

Yani planın korktuğu "model indirilemez" tıkanması **yok**.

## 2. Görev

### ADIM 1 — Okuma yolu (asıl değer burada)

Canlı sohbet şu an SQLite'tan son birkaç konuşmayı **LIKE** ile alıyor.
Yapılacak: `VectorMemory` + `MemoryRetrievalPolicy` ile **anlamsal**
arama. Kullanıcı mesajıyla benzerlik araması yapılır, bulunan geçmiş
parçalar system prompt'a ayrı bir başlıkla eklenir.

- Eşik ve n sayısı **ölçülerek** seçilir, varsayımla değil: birkaç gerçek
  soruda kaç isabet döndüğüne ve alakasız parça gelip gelmediğine bakılır.
- Bulunan hiçbir şey yoksa **hiçbir şey eklenmez.** Boş zemin, yanlış
  zeminden iyidir (`main.py`'deki mevcut yorumun aynı ilkesi).

### ADIM 2 — İndeks, kalıcı hafıza DEĞİLDİR

Arama, **var olan SQLite sohbet geçmişi** üzerine kurulan bir indekstir.
Türetilmiş yapıdır: silinebilir, yeniden kurulabilir, ve §7.1a'nın
kapsamına **girmez**. `VectorMemory`'ye kalıcı yazmak kapsama girer.

`scripts/` altına **idempotent** bir backfill betiği yazılır: mevcut
geçmişi indeksler, iki kez çalıştırılınca kopya üretmez.

### ADIM 3 — Yazma yolu: mevcut hattı KULLAN

Yeni yazma yolu **yazılmaz**. Ahmet "bunu kalıcı hafızaya yaz" dediğinde
akış şudur: `answer_crystallizer` aday kart üretir →
`knowledge_card_promoter` onaylıyla kalıcıya geçirir.

Kartın önemli olup olmadığına model karar verip **sormalı**; sessizce
kaydetmemeli, sessizce atmamalı (§7.1a madde 3).

### ADIM 4 — `clear_history` ile tutarlılık

`clear_history()` bugün RAM + SQLite siliyor (B04: "kullanıcı unut diyor,
JARVIS unuttum diyor, sonraki turda hatırlıyordu"). İndeks eklenince
**aynı tuzak geri gelir**: indeks silinmezse unutulan konuşma aramayla
geri döner. `clear_history` indeksi de temizlemeli ve bunun bir testi
olmalı.

### ADIM 5 — Doğrulama (ölç, iddia etme)

- Bilgi ver, programı **kapat**, yeniden aç, sor → hatırlamalı.
- "Unut" de, sonra aynı şeyi sor → hatırlamamalı (ADIM 4'ün kanıtı).
- Anlamsal aramanın LIKE'a göre ne kazandırdığı birkaç gerçek soruda
  yan yana yazılır. Kazanç yoksa **öyle yaz** — bu kart kazanç
  varsaymıyor, ölçüyor.

---

## 3. Sınırlar

- `chat()` imzası **bozulmaz** — 2048 test ona bağlı. Yeni davranış yeni
  parametre/metot olarak eklenir (`chat_stream` bu kalıpla eklendi).
- `chat_stream` de aynı hafızayı görmeli: iki yol **aynı** prompt'u
  kuruyor (`_mesajlari_hazirla`), hafıza oraya girer, iki yere değil.
- `config.py`'deki `HF_*_OFFLINE` bayraklarının **yeri değişmez** (§9).
- `agents/persona.py`: dokunma.
- Otomatik kalıcı yazma **yok** (§7.1a).
- Kapı: `pytest tests -q` **iki sırada**, `ruff check .` **≤ 283**.
- Push yalnız Ahmet'in onayıyla. Bitince **DUR**.

## 4. Bitti sayılma ölçütü

- Anlamsal arama canlı sohbette çalışıyor; eşik/n **ölçümle** seçilmiş.
- Backfill betiği var ve idempotent.
- `clear_history` indeksi de siliyor, **testi var**.
- Kapat-aç-hatırla ve unut-hatırlama testleri geçti.
- `VectorMemory`'ye otomatik yazan **tek bir yol bile** eklenmedi.
- Kapı iki sırada yeşil, ruff ≤ 283.
