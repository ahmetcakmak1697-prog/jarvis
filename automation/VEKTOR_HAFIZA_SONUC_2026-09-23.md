# VEKTÖR HAFIZA — ölçüm sonuçları ve alınan kararlar

**Kart:** `automation/KART_VEKTOR_HAFIZA.md` · **Tarih:** 2026-09-23
**Dal:** `auto/opencode-deepseek` · **Taban:** `3557bd4`

Bu belge kartın *yapıldı* kaydı değil, **ölçümlerin** kaydıdır. Kart
"kazanç varsaymıyor, ölçüyor" diyordu; aşağıdaki sayılar o ölçümdür ve
biri kartın kendi önermesini çürütüyor.

---

## 0. Kartın iki yanlış önermesi — ölçülüp düzeltildi

**(a) "Canlı sohbet SQLite'tan son birkaç konuşmayı LIKE ile alıyor."**

Yanlış. `search_conversations()` (LIKE'ı içeren metot) repoda
**hiç çağrılmıyor** — tek geçtiği yer kendi tanımı. Canlı yol
`get_context_for_prompt()` → `get_recent_conversations(3)`, yani
**son 3 kayıt, zamana göre.** Arama diye bir şey yoktu.

Bu, kartın vardığı sonucu güçlendiriyor: anlamsal aramanın rakibi zayıf
bir arama değil, **hiç arama olmaması**.

**(b) "Önkoşullar sağlanıyor: çok dilli gömme modeli hazır."**

Model önbellekte, doğru. Ama indekse **bağlı değildi** — ayrıntı
`FAILURES.md` → *"Chroma'nın varsayılan gömme modeli İngilizcedir"*.
Özet: varsayılan model altı Türkçe sorguda **1/6** aldı (rastgele seçme
beklentisi de 1/6), çok dilli model **5/6**.

---

## 1. Verinin gerçek hâli — asıl bulgu

| ölçüm | sayı |
|---|---|
| SQLite'taki konuşma kaydı | 183 |
| **eşsiz** soru | **34** |
| "nerede kaldik" tekrarı | 59 |
| "Bir metrede kac santimetre vardir?" tekrarı | 33 |
| teknik borç sorusu tekrarı | 33 |
| yalnız bir kez geçen | 18 |

183 kaydın **125'i (%68)** üç kalite-takımı sorusunun tekrarı. Yani
"sohbet geçmişi" dediğimiz şeyin üçte ikisi sohbet değil, ölçüm koşusu.

**Sonuç:** indeks tekrarları birleştirir (34 parça). Ama asıl gerçek şu —
**bugün hatırlanacak pek bir şey yok.** Makine kuruldu ve çalışıyor;
içine koyulacak malzeme Ahmet JARVIS'i kullandıkça birikecek.

## 2. Eşik — seçildi, varsayılmadı

İki dağılım ölçüldü:

| dağılım | nasıl kuruldu | sonuç |
|---|---|---|
| **GÜRÜLTÜ** | karşılığı indekste **olmayan** 8 soru | en yüksek **0,409** · ortalama 0,306 |
| **İSABET** | karşılığı olan, doğru kayıtla **kelime paylaşmayan** sorular | 0,418 · 0,536 · 0,600 |

Aradaki boşluk **0,009**. Bu bir eşik değil, yazı-turadır: 0,41'de
*"en yakın eczane nerede"* sorusu *"Sadece pazıpanko'nun stünyü ne ya?"*
kaydını hafıza diye prompt'a sokuyordu.

**Seçilen: 0,50.** Ölçülen 8 gürültünün 8'ini eler, iki kuvvetli isabeti
(0,536 · 0,600) geçirir, zayıf olanı (0,418) gürültüden ayırt
edilemediği için **bilerek** bırakır.

Asimetri kasıtlı: prompt'a giren yanlış bir hatıra JARVIS'i kendinden
emin biçimde yanıltır (PUSULA ihlali); eksik bir hatıra yalnızca
"bilmiyorum" dedirtir.

`MemoryRetrievalPolicy`'nin 0,70 varsayılanı bu yolda **kullanılamaz** —
ölçülen doğru isabetlerin hepsini elerdi.

## 3. Mimari karar — indeks ayrı koleksiyonda

Kart indeksi `VectorMemory`'ye yazmayı öngörüyordu. **Yapılmadı.**

`jarvis_memories`, `knowledge_card_promoter`'ın **onaylanmış** kartları
yazdığı yerdir (§7.1a). İndeks oraya konsaydı `clear_history()` indeksi
silerken onaylanmış kartları da silerdi — sessiz ve geri dönüşü olmayan
bir veri kaybı.

İndeks `sohbet_indeksi` koleksiyonunda durur. Böylece §7.1a **yapısal**
olarak korunur: sohbet yolunda `jarvis_memories`'e yazan tek satır yok.

Yanında çıkan kusur da düzeltildi: `VectorMemory.reset()` koleksiyon adını
**sabit** yazıyordu, yani ayrı koleksiyon açan bir çağıran `reset()`
dediğinde kendi indeksini değil bilgi kartlarını siliyordu.

## 4. Maliyet — ölçüldü

| iş | süre |
|---|---|
| Gömme modelinin ilk yüklenmesi | **12 888 ms** |
| 34 parçanın indekslenmesi | 690 ms |
| Tek arama (model yüklüyken) | **11–17 ms** |

12,9 sn açılış yoluna konulamaz. Çözüm: **arka planda ısıtma.**
`LocalJarvisAgent.__init__` bir iş parçacığı başlatır; hazır değilken
sorulan tur hafızasız geçer, **beklemez**. Boş zemin, geç gelen zeminden
iyidir.

Kaçış kapısı: `JARVIS_ANLAMSAL_HAFIZA=0`.

## 5. Uçtan uca doğrulama (gerçek Chroma, gerçek model)

Ahmet'in verisine dokunulmadı: SQLite kopyalandı, Chroma ayrı dizinde
kuruldu, "unut" sınavı kopyayı sildi.

| sınav | sonuç |
|---|---|
| **1.** Anlamsal arama, düz aramanın bulamadığını buluyor mu? | **BULDU** |
| **2.** Yeni süreç, aynı disk → hatırlıyor mu? | **HATIRLADI** (34 parça) |
| **3.** `temizle()` sonrası aynı sorgu → unuttu mu? | **UNUTTU** (boş) |

Sınav 1'in ayrıntısı, kazancın nerede olduğunu gösteriyor:

```
sorgu : "uzunluk birimleri arasinda ne iliski var"
hedef : "Bir metrede kac santimetre vardir?"   (ortak kelime: SIFIR)

LIKE 'uzunluk' -> 0    LIKE 'iliski' -> 0    LIKE 'birim' -> 4 (alakasız)
anlamsal       -> doğru kayıt, benzerlik 0,536, 1. sırada
```

## 6. Kapı

| kontrol | sonuç |
|---|---|
| `pytest tests -q` (alfabetik) | **2074 geçti / 0 başarısız / 2 xfailed** |
| `pytest` (ters sıra) | **2074 geçti** — sıra bağımsız |
| `ruff check .` | **282** (tavan 283; bir azaldı) |
| Yeni test | 30 (17 birim + 13 bağlantı) |
| Mutasyon kontrolü | iki kritik kapı bozulup **kırmızı görüldü**, geri alındı |

## 7. Yapılmayanlar — bilerek

- **Otomatik kalıcı yazma yok.** `VectorMemory`'ye yazan tek bir yeni yol
  bile eklenmedi. §7.1a yürürlükte: varsayılan yazmaz.
- `jarvis_memories` koleksiyonunun gömme modeli **değiştirilmedi**.
  Orası da İngilizce varsayılanı kullanıyor, yani oraya yazılacak Türkçe
  bilgi kartları aranabilir olmayacak. **Görüldü, söylendi, dokunulmadı**
  (CLAUDE.md §3) — koleksiyon şu an boş olduğu için bedeli sıfır, ama
  ilk kart onaylanmadan önce Ahmet'in kararı gerekiyor.
- Backfill betiği sohbet yolundan **çağrılmıyor**; elle çalıştırılır.

---

## 8. Ek: `jarvis_memories` düzeltildi (aynı gün, Ahmet onayıyla)

§7'de "görüldü, söylendi, dokunulmadı" diye bırakılan madde kapatıldı.
Ahmet'in gerekçesi doğruydu: koleksiyon boşken bedel sıfır, ilk kart
onaylandıktan sonra indeksin tamamını yeniden kurmak gerekirdi.

Düzeltmeden önce iki şey ölçüldü ve ikisi de planı değiştirdi.

**(a) Chroma gömme modelini değiştirmeyi reddediyor.** Var olan bir
koleksiyona farklı model verilince `ValueError` atıyor. Yani "varsayılanı
değiştir" tek satırlık bir iş değil; koleksiyonun silinip yeniden
kurulması gerekiyor. Bu yüzden `koleksiyon_ac()` **boş/dolu ayrımı**
yapar: boşsa siler ve yeniden kurar, doluysa `KoleksiyonCakismasi`
yükseltir ve **silmez**. Sayım başarısız olursa dolu varsayar. Bu ayrım
olmasaydı kod bir veri imha aracı olurdu.

**(b) Daha sinsi olan:** koleksiyon EF verilmeden açılınca Chroma kayıtlı
modeli geri kurmuyor, sessizce `DefaultEmbeddingFunction`'a düşüyor.
Sorgu hata vermiyor, sonuç dönüyor — ama soru vektörü belgelerden **başka
bir modelle** hesaplanmış oluyor. İki model de 384 boyut ürettiği için
boyut hatası da alınmıyor. Sonuç: anlamsız mesafeler, tam güvenle.
Artık açılıştan sonra kullanılan modelin istenen model olduğu
**doğrulanıyor**; değilse yükseltiliyor.

**Uygulama ve doğrulama:**

| | |
|---|---|
| `jarvis_memories` | 0 kayıtla silindi, Türkçe modelle yeniden kuruldu |
| İlk açılış | 11 003 ms (model yükleme) |
| İkinci koleksiyon, aynı süreç | **13 ms** — model süreç başına bir kez |
| `sohbet_indeksi` | dokunulmadı, 34 kayıt yerinde |

Türkçe bilgi kartı sınavı (ortak kelime **sıfır**):

```
"oturma odasindaki cihazin baglantisi duzeldi mi"
    -> "Ahmet salon klimasinin ESP kablosunu geri takti"   0,529  ✓
"asistan nasil konusuyor"
    -> yanlış kartı 0,282'de getirdi; eşik 0,50 olduğu için ELENDİ
```

İkincisi kusur değil, tasarım: yanlış hatıra eşiğin altında kalıp
düşüyor. Aynı soru ilk gömme sınavında da çok dilli modelin kaçırdığı
tek vakaydı (5/6) — ölçüm tutarlı.

**Bedeli taşıyan taraf:** `VectorMemory()` açan yollar süreç başına bir
kez ~11–13 sn ödüyor. Bunlar bilgi kartı onaylama, `local_first_router`,
`jarvis_brain` ve `jarvis_server` — **hiçbiri canlı sohbet döngüsünde
değil**. `main.py` → `LocalJarvisAgent` bu depoyu hiç açmıyor.

**Kapı:** `pytest tests -q` **2081 geçti** (iki sırada), `ruff check .`
**282**. Yeni test: 8.
