# KART — Anlamsal indeksi SQLite ile uzlaştır (silinen konuşma indekste kalmasın)

**Kime:** Claude Code (VS Code) · **Veren:** Ahmet, 2026-09-24
**Dal:** `auto/opencode-deepseek` · **Taban:** `a5ad136`
**Sınıf:** Tutarlılık kusuru. Yeni özellik değil, açık kapanıyor.

---

## 0. Bu kartın dürüst önceliği — abartılmamalı

Kusur gerçek ama **bugün ulaşılabilir değil.** Ölçüldü (2026-09-24):
repoda `conversations` tablosundan silen **tek** yol
`memory_manager.py:126`'daki `clear_conversations()` ve o **hepsini**
siliyor; `clear_history()` de indeksin tamamını zaten temizliyor. Yani
"tek bir konuşmayı sil" diye bir üretim yolu yok.

Delik şu an yalnız **elle** müdahaleyle açılıyor — 2026-09-23 gecesi
tam olarak bu oldu: beş test kaydı SQLite'tan silindi, indeks onları
tuttu ve `--sil` + yeniden kurma ile elle dolanıldı.

**Ne zaman aktif hale gelir:** "şunu unut" (tek bir şeyi unut) özelliği
yazıldığı gün. O özellik hafızanın doğal bir sonraki isteğidir ve
yazıldığında bu delik B04'ün üçüncü kapısı olur: kullanıcı unut der,
SQLite unutur, anlamsal arama **hatırlar**.

Yani bu kart bir yangın söndürme değil, yangından önce kapıyı kapatma
işidir. Sıralanırken buna göre değerlendirilmeli.

## 1. Kusur, tek cümle

`scripts/hafiza_indeksle.py` **yalnız ekler** (`upsert`); SQLite'tan
silinmiş bir konuşmanın indeks kaydını **çıkarmaz**. İndeks böylece
SQLite'ın üst kümesine dönüşür ve aradaki fark sessizce büyür.

Aynı kusur **düzenlenen** kayıt için de geçerli: kimlik içerikten
türetildiği için (`_kimlik()` = normalize edilmiş soru+cevabın sha1'i)
metin değişince **yeni** bir kayıt yazılır ve eskisi öksüz kalır.

## 2. Ölçülmüş önkoşullar — yol açık

| önkoşul | durum |
|---|---|
| İndeksteki kimlikler listelenebiliyor mu | ✅ `col.get(include=[])` → 34 kimlik, ucuz |
| Geçerli kimlik kümesi hesaplanabiliyor mu | ✅ `_kimlik()` içerikten türetiyor, SQLite'tan yeniden üretilir |
| Chroma toplu silme | ✅ `col.delete(ids=[...])` |

Yani iş, iki kümenin farkını almaktan ibaret.

## 3. Görev

### ADIM 1 — Uzlaştırma, ayrı bir kip DEĞİL

`indeksle()` varsayılan çalışmasında uzlaştırsın: geçerli kimlik kümesi
hesaplanır, indekste olup o kümede olmayanlar silinir. Yeni bayrak
eklenmesin (CLAUDE.md §2 — önce sadelik); bir kipin arkasına saklanan
tutarlılık, çalıştırılmadığı gün tutarlılık değildir.

Betik ne yaptığını **saysın**: `eklenen / guncellenen / silinen`.
Sayı basılmazsa uzlaştırmanın çalıştığı iddia edilemez.

### ADIM 2 — Boş okuma indeksi SİLDİRMEZ (asıl tehlike burası)

Bu adım kartın en önemli maddesi. Uzlaştırma, "SQLite'ta olmayan her
şeyi sil" demektir; SQLite okunamaz ya da boş dönerse bu emir
**indeksin tamamını silmek** anlamına gelir.

Kural: geçerli kimlik kümesi **boşsa hiçbir şey silinmez** ve sebep
ekrana yazılır. Aynı asimetri `tools/vector_memory.py:koleksiyon_ac`'ta
zaten var (boş koleksiyon yeniden kurulur, dolu koleksiyon **silinmez**,
sayılamıyorsa dolu varsayılır) — aynı disiplin buraya da uygulanır.

İkinci emniyet: silinecek oran indeksin yarısını aşıyorsa betik durur
ve onay ister. Gerekçe: normal kullanımda bir seferde bu kadar kayıt
düşmez; düşüyorsa okuma tarafında bir şey bozulmuştur.

### ADIM 3 — Kapsam sınırı yazılı olsun

Uzlaştırma bugün doğru, çünkü `sohbet_indeksi`'ndeki **her** parça
SQLite'tan geliyor. İleride başka bir kaynak (notlar, belgeler) aynı
koleksiyona indekslenirse "SQLite'ta yoksa sil" kuralı o kayıtları da
siler. Bu varsayım koda **yorum olarak** yazılsın; kaynak çeşitlenirse
kimliklere kaynak öneki gerekir.

### ADIM 4 — Test

- Silinen konuşma indeksten de düşüyor.
- Düzenlenen konuşmada eski kayıt öksüz kalmıyor.
- **SQLite boş/okunamaz → indekse DOKUNULMUYOR** (en kritik test).
- Yarıdan fazlası silinecekse duruluyor.
- İki kez çalıştırmak hâlâ kopya üretmiyor (mevcut garanti bozulmasın).

Testler `chromadb` **gerektirmesin** — kapı sistem Python'unda koşuyor
ve orada kurulu değil. Depo sahte nesneyle verilir; ölçülen şey Chroma
değil, bizim kararımız.

## 4. Sınırlar

- `VectorMemory` varsayılanları **değişmez**; `jarvis_memories`'e
  dokunulmaz (§7.1a).
- `clear_history()` davranışı **değişmez** — o zaten indeksin tamamını
  siliyor ve doğru çalışıyor.
- Otomatik kalıcı yazma **yok**.
- Silme "mantıksal"dır; diskten kurtarılamaz silme garantisi **verilmez**
  (`memory_manager` A-05 notuyla aynı dil kullanılsın).
- Kapı: `pytest tests -q` **iki sırada** yeşil, `ruff check .` **≤ 282**.
- Push yalnız Ahmet'in onayıyla. Bitince **DUR**.

## 5. Bitti sayılma ölçütü

- Silinen konuşma indekste kalmıyor; bunu gösteren test var.
- Boş/okunamaz SQLite indeksi silmiyor; bunu gösteren test var.
- Betik `eklenen/guncellenen/silinen` sayılarını basıyor.
- Elle `--sil` + yeniden kurma **gerekmiyor** (2026-09-23'te gerekmişti).
- Kapı iki sırada yeşil, ruff artmamış.
