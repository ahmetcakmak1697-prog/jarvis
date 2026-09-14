# KART — `localhost`'un kalanları: PDF dalı canlı, gerisi sınıflara ayrıldı

**Kime:** Claude Code (VS Code) · **Veren:** Ahmet, 2026-09-14
**Dal:** `auto/opencode-deepseek` · **Taban:** `3982fe3`
**Sınıf:** Düpedüz hata — **imza gerekmiyor.** Ama park edilmiş cepheler
kapsam dışı ve bu **bilerek** (§9).

---

## 0. Neden — canlı ses yolunda hâlâ bir satır var

`5ebf4aa` dört yolu düzeltti. Ama `tests/test_localhost_gecikmesi.py`'nin
kendi docstring'i açık bıraktığını yazıyor:

> *"ISTISNA (olculdu, duzeltilmedi): ayni `chat()`'in acik PDF/belge istegi
> dali (agent/local_agent.py:939-947) cevabi rag/rag_engine.py:138'den alir;
> o satir `requests.post` ile localhost'a gider. Yani ses yolu yalniz bu
> dalda ~2 s oder."*

Ölçüm (2026-09-13, bu makine, bağımsız doğrulandı):

```
getaddrinfo("localhost")  -> ['::1', '127.0.0.1']
urllib -> localhost:11434 : ~2,05 s / istek
urllib -> 127.0.0.1:11434 : ~0,001-0,016 s / istek
```

Ollama IPv6'yı dinlemiyor; bağlantı önce orada zaman aşımına uğrayıp
IPv4'e düşüyor.

**Sonuç:** Ahmet bir PDF ya da belge sorduğunda cevabı ~2 saniye geç
duyuyor. PUSULA bütçesi 1.500 ms.

## 1. Kalan 19 satır — sınıflara ayrıldı

`git grep localhost:11434` (2026-09-14, `__pycache__` ve `.venv` hariç):

| yer | sayı | sınıf | dokunulsun mu |
|---|---|---|---|
| `rag/rag_engine.py:138` | 1 | **canlı ses yolu** (PDF dalı) | **EVET — öncelik** |
| `jarvis_brain.py` | 5 | canlı giriş noktası (envanter §B: `CANLI \| giris noktasi (A)`, 22 dosyaya ulaşıyor) | **EVET** |
| `training/conversation_summarizer.py:42` | 1 | toplu iş betiği | **EVET** |
| `training/quality_evaluator.py:28` | 1 | toplu iş betiği | **EVET** |
| `tests/jarvis_system_audit.py:568` | 1 | denetim aracı | **EVET** |
| `setup.py:36` | 1 | kurulum, bir kez koşar | **EVET** (ucuz) |
| `agents/daily_digest.py:32` | 1 | **park edilmiş cephe** | **HAYIR** |
| `agents/orchestrator.py:27` | 1 | **park edilmiş cephe** | **HAYIR** |
| `agents/proactive_agent.py:77` | 1 | **park edilmiş cephe** | **HAYIR** |
| `agents/self_improver.py:46` | 1 | **park edilmiş cephe** | **HAYIR** |
| `tests/test_api_executor.py:410` | 1 | **test verisi** (`https://localhost/v1`, sahte URL, gerçek çağrı yok) | **HAYIR** |
| `tests/test_localhost_gecikmesi.py` | 4 | kilit testinin **kendi metni** | **HAYIR** |

### Park edilmiş dördü neden dışarıda

`CLAUDE.md` §9 park edilmiş cepheleri **hiçbir gerekçeyle** yeniden
açmayı yasaklıyor. Kusur görülüyor, yazılıyor, **düzeltilmiyor** (§3:
gör, söyle, silme). Onlara dokunmak o cepheleri açmak demektir.

Bu bir eksiklik değil, **bilinçli bir sınır.** Kilit testinin mevcut
docstring'i bunu zaten böyle anlatıyor; koru.

### `jarvis_brain.py` neden içeride

Park edilmiş **değil**. `docs/JARVIS_ENVANTER.md` onu
`CANLI | giris noktasi (A)` diye işaretliyor ve 22 dosyaya ulaşıyor.
Ses yolundan (`main.py`) import edilmiyor ama kendi başına bir giriş
noktası ve aynı 2 saniyeyi ödüyor.

**[EMİN DEĞİLİM]** Bu giriş noktasının bugün fiilen kullanılıp
kullanılmadığını ölçmedim. Kullanılmıyorsa düzeltme zararsız; ayrı bir
soru ve bu kartın konusu değil.

---

## 2. Görev

### ADIM 1 — Kilit testini genişlet, ÖNCE KIRMIZI GÖR

`tests/test_localhost_gecikmesi.py` → `_HEDEFLER`'e yeni yolları ekle.
Şu an dört dosya var; altı yeni dosya eklenecek.

**Docstring'i güncelle** — mevcut metin çok iyi yazılmış, bozma:

- "ISTISNA ... duzeltilmedi" paragrafı artık **yanlış** olacak; PDF
  dalının düzeltildiğini ve hangi commit'te olduğunu yaz.
- "Kartin tablosunda OLMAYAN ve bu kartta duzeltilmeyen yerler" listesi
  daralacak; kalanlar **yalnız** park edilmiş dört dosya + test verisi
  olacak.
- Park edilmiş dördünün neden dışarıda olduğu paragrafı **aynen kalsın.**

Testin kırmızı yandığını gör: altı dosya da hâlâ `localhost` taşıyor.

### ADIM 2 — Değiştir

`localhost` → `127.0.0.1`, altı dosyada. Başka hiçbir şeye dokunma.

`rag/rag_engine.py:138` **önceliklidir** — canlı ses yolu odur.

### ADIM 3 — Kazancı ölç

PDF dalı gerçek bir Ollama çağrısı yapıyor. Düzeltmeden önce ve sonra:

```
python -c "from rag.rag_engine import JarvisRAG; ..."
```

ya da eşdeğer bir sonda ile **aynı sorgu** iki kez ölçülür. Beklenen:
~2 saniye düşüş.

**Düşmezse söyle** — o zaman PDF dalı başka bir yerden de `localhost`
kullanıyor demektir ve teşhis eksiktir.

RAG indeksi kurulumu ölçüme **dahil edilmez**; yalnız `query_with_ollama`
çağrısının süresi yazılır.

---

## 3. Sınırlar

- **Park edilmiş dört dosyaya DOKUNMA** (§9). Testin kapsamına da alma.
- `tests/test_api_executor.py:410` bir **test verisi**, gerçek çağrı
  değil — dokunma.
- `agent/local_agent.py`, `voice/`: dokunmaya gerek yok, `ollama` paketi
  zaten `127.0.0.1` çözüyor.
- Kalite eşikleri, dedektörler, `passing_threshold`: dokunma.
- Kapı: `pytest tests -q` **iki sırada**, `ruff check .` **≤ 283**.
- Push yok. Bitince **DUR**.

## 4. Bitti sayılma ölçütü

- `_HEDEFLER` altı yeni yolu içeriyor; test önce kırmızı görüldü.
- Docstring güncel: PDF dalı artık "düzeltilmedi" demiyor, park edilmiş
  dördünün gerekçesi **aynen duruyor**.
- Altı dosyada `localhost:11434` kalmadı.
- **PDF dalının kazancı ölçüldü** ve öncesi/sonrası süre yazılı.
- Park edilmiş dört dosya **hâlâ dokunulmamış** (`git diff` kanıtlıyor).
- Kapı iki sırada yeşil, ruff ≤ 283.
