# KART — "Şunu unut": tek bir konuşmayı unutturma

> **✅ TAMAMLANDI — 2026-09-24.** Dört ölçüt de karşılandı.
> Doğrulama gerçek Chroma ve gerçek gömme modeliyle, **kopya** üzerinde:
> aday bulma hiçbir şey silmedi · onaydan sonra üç kopyanın üçü de gitti ·
> arama artık boş dönüyor · profil ve `events` korundu.
> Canlı `main.py`'de: konusuz "unut" sordu ve `temizle`'ye yönlendirdi,
> konulu olan doğru kaydı buldu, "vazgeç" hiçbir şey silmedi (183 → 183).
> Bu komutlar modele hiç gitmiyor — `Tur: 0`, sıfır maliyet.
>
> **Kartta olmayan bir madde eklendi:** kart indeksi bir sonraki
> `hafiza_indeksle` koşusunun uzlaştırmasına bırakıyordu. Yetmez —
> o ana kadar JARVIS hatırlamaya devam ederdi ve "unuttum" dedikten
> sonra hatırlamak, hiç unutmamaktan kötüdür. `unut()` artık SQLite ile
> indeksi **aynı anda** temizliyor (`AnlamsalHafiza.unut_anahtarlari`).

**Kime:** Claude Code (VS Code) · **Veren:** Ahmet, 2026-09-24
**Dal:** `auto/opencode-deepseek` · **Taban:** `47b4450`
**Sınıf:** Kullanıcı hakkı + **veri silme**. Bu kart geri alınamaz bir iş yapar.

---

## 0. Neden bu kart

`CLAUDE.md` §7.1: *"Human override her katmandan üstün: kullanıcı her an
dur/iptal/**unut**/yerel-kal diyebilir."* Bugün bu hakkın yalnız topyekûn
hâli var: `temizle` **her şeyi** siliyor. Tek bir şeyi unutturmanın yolu yok.

Ölçüldü (2026-09-23 gecesi): beş test kaydını kaldırmak için elle SQL
yazmak gerekti. Kullanıcının elle veritabanı düzenlemek zorunda kaldığı
yer, eksik bir özelliğin adresidir.

Altyapı 2026-09-24'te hazırlandı (`47b4450`): indeks artık SQLite ile
uzlaşıyor, yani bir konuşma silindiğinde aramadan da düşüyor. Bu kart o
kapının kolunu takıyor.

## 1. Bu kartın tek gerçek riski: YANLIŞ ŞEYİ SİLMEK

Eşleştirme **anlamsal**, yani olasılıksal. 0,45 eşiği "iyi bir hatıra"
için doğru ayar; **silme** için değil. Bir hatırayı yanlışlıkla prompt'a
sokmak kötü bir cevap üretir ve geri alınır; yanlış hatırayı silmek geri
alınmaz.

**Kural: onay olmadan hiçbir şey silinmez.** Akış şudur — adayları
**bul**, kullanıcıya **göster**, **sor**, sonra sil. Tek adımlı "unut
gitsin" yok.

İkinci kural: **konusuz "unut" hiçbir şey silmez.** Sadece "unut" demek
"her şeyi unut" değildir; o komutun adı `temizle` ve o ayrı duruyor.
Konusuz "unut" neyin unutulacağını **sorar**.

## 2. Kapsam — dar, bilerek

| silinir | silinmez |
|---|---|
| `conversations` tablosundaki eşleşen satırlar | kullanıcı profili (ad, tercihler) |
| anlamsal indeksteki karşılıkları | `events` tablosu |
| | `jarvis_memories` (onaylanmış bilgi kartları, §7.1a) |

Gerekçe `clear_conversations`'ın kendi notuyla aynı: *"geniş bir silme,
dar bir silmeden daha kötü bir sürprizdir."*

**Kopyalar birlikte gider.** Aynı soru geçmişte 59 kez sorulduysa (ölçüldü)
"bunu unut" hepsini kapsar; biri kalırsa unutma yarım kalmıştır.

## 3. Görev

### ADIM 1 — Ortak anahtar tek yerde

Eşleştirme, indeksin tekrar birleştirmede kullandığı **aynı** anahtarla
yapılır. `_anahtar()` bugün `scripts/hafiza_indeksle.py` içinde; veri
katmanına (`memory/memory_manager.py`) taşınır ve betik oradan alır.
İki ayrı normalleştirme, sessizce ıskalayan bir silme demektir.

Anahtar indeks üstverisine de yazılır ki aday → satır eşlemesi
**tahminle değil** yapılsın. Üstveridəki `user_msg` 200 karaktere
kırpılmış; uzun bir soruda eşleşme kaçardı.

### ADIM 2 — Silme, veri katmanında

`JarvisMemory.forget_by_keys(anahtarlar) -> int`. Sayı döner; sessiz
başarı yok. Boş küme verilirse **hiçbir şey silinmez** (uzlaştırmadaki
asimetrinin aynısı).

### ADIM 3 — Adayları bulma

`LocalJarvisAgent.unutma_adaylari(konu)` anlamsal aramayla aday döner.
Eşik burada **daha yüksek** tutulabilir; seçimi ölçüme bağla, varsayma.
Aday yoksa "bulamadım" denir ve **hiçbir şey silinmez**.

### ADIM 4 — Etkileşim

`main.py`'de, `temizle` ile aynı yerde. Adaylar numaralı gösterilir;
kullanıcı numara seçer, `hepsi` der ya da `vazgeç` der. Varsayılan
**vazgeç**: anlaşılmayan bir cevap silme yapmaz.

### ADIM 5 — Doğrulama (ölç, iddia etme)

- Unutulan konuşma SQLite'tan gitti ve aramadan da düştü.
- Kopyaları da gitti.
- `vazgeç` hiçbir şey silmedi.
- Aday yokken hiçbir şey silinmedi.
- Profil ve `jarvis_memories` **dokunulmadan** duruyor.

## 4. Sınırlar

- Onaysız silme **yok**; tek adımlı unutma **yok**.
- Silme "mantıksal"dır; diskten kurtarılamaz silme garantisi **verilmez**
  (`memory_manager` A-05 notuyla aynı dil).
- Türkçe eşleştirme `_fold_tr`/`keyword_present` ile (CLAUDE.md §6).
- `clear_history()` davranışı değişmez.
- Kapı: `pytest tests -q` **iki sırada**, `ruff check .` **≤ 282**.
- Push yalnız Ahmet'in onayıyla. Bitince **DUR**.

## 5. Bitti sayılma ölçütü

- "Şunu unut" konuşmayı hem SQLite'tan hem indeksten düşürüyor; testi var.
- Onay istenmeden silen **tek bir yol bile** yok; testi var.
- Konusuz "unut" hiçbir şey silmiyor, soruyor; testi var.
- Kapı iki sırada yeşil, ruff artmamış.
