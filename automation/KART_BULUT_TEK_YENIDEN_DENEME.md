# KART — Bulut çağrısına TEK yeniden deneme (bütçe büyümeden)

**Kime:** Claude Code (VS Code) · **Veren:** Ahmet, 2026-09-11
**Dal:** `auto/opencode-deepseek` · **Taban:** `4d53d51`
**Karar:** Ahmet onayladı (2026-09-11) — *"tek yeniden deneme"*.

---

## 0. Neden — ölçüldü

`automation/SES_YOLU_DEEPSEEK_2026-09-11.md` §7a: 21 turun **7'si**
geçici ağ hatasıyla yerele düştü (`WinError 10054`, `RemoteDisconnected`,
okuma zaman aşımı). Sınıf başına 1/7, 3/7, 3/7 — yani **her üç turdan biri.**

Bunun bedeli artık sadece gecikme değil: o turlarda cevabı `llama3.1`
veriyor ve **bugün ölçüldü ki llama "nerede kaldık" sorusunu
cevaplayamıyor** — üç denemede üçünde de *"anlık proje durumuna erişimim
yok"* dedi. Yani her üç turdan birinde PUSULA sessizce kırılıyor.

Aynı düzeltme ölçüm tarafında zaten işe yaradı: `run_turkish_quality.py`
yeniden denemeyle **15 boş vaka → 1**.

**Uyarı, kayda geçsin:** o 21 çağrı arka arkaya yapıldı. Gerçek sohbette
turlar saniyelerle ayrılır; %33 **kötümser olabilir.** Bu yüzden kart
düzeltmeden sonra oranı **yeniden ölçmeyi** şart koşuyor.

---

## 1. İÇ ÇELİŞKİ — kartın çözmesi gereken asıl mesele

Naif uygulama şudur: `timeout=20` ile dene, olmazsa `timeout=20` ile bir
daha dene. **Bu yanlıştır ve dün kazanılanı geri verir.**

Claude zaman aşımını 60 s'den 20 s'ye ölçümle indirdi
(`agent/cloud_llm.py:62`), gerekçesi: hat koptuğunda kullanıcı 60 saniye
bekleyip *sonra* yerel cevabı alıyordu (60.547 ve 75.565 ms ölçüldü).
PUSULA'nın hedefi ~1,5 s.

İki deneme × 20 s = **en kötü 40 saniye.** Kabul edilemez.

### Çözüm: bütçe bölünür, büyütülmez

Toplam duvar süresi **20 saniyede kalır** ve içine iki deneme sığar:

```
1. deneme : timeout 12 s
   geri çekilme : 0,5 s
2. deneme : timeout  7 s
   ------------------------
   en kötü toplam ≈ 19,5 s   (mevcut tavanın altında)
```

**Sayılar ölçümden geliyor, tahminden değil:** başarılı uzun anlatım turu
p95 **7,0 s**, en yavaş başarılı tur **7,6 s** (aynı rapor §7b). 12 s'lik
ilk deneme meşru hiçbir cevabı kesmiyor.

Geri çekilme 0,5 s: `WinError 10054` **anlık** bir kopmadır, sağlayıcının
toparlanmasını beklemek gerekmez. Ölçüm koşusundaki 2 s'lik bekleme
orada doğruydu (kullanıcı beklemiyordu), burada değil.

---

## 2. Ne yeniden denenir, ne denenmez

`eval/run_turkish_quality.py` bu politikayı zaten çözdü ve gerekçesi orada
yazılı. **Deseni oradan al** (`_gecici_ag_hatasi()`, `_GECICI_HTTP_KODLARI`).

Kritik: `HTTPError` bir `URLError` **alt sınıfıdır**. Önce o ayıklanmazsa
yanlış anahtar (401) da "geçici" sayılır ve boşuna tekrarlanır.

| Durum | Yeniden denenir mi |
|---|---|
| `ConnectionError`, `WinError 10054`, `RemoteDisconnected` | **Evet** |
| Okuma zaman aşımı (`TimeoutError`, `socket.timeout`) | **Evet** |
| HTTP 429, 500, 502, 503, 504, 408, 409, 425 | **Evet** |
| HTTP 401 / 403 (anahtar) | **Hayır** |
| HTTP 400 (bozuk istek) | **Hayır** |
| `CloudChatError("dis model bos cevap dondu")` | **Hayır** — hat değil, model |
| `https` değil / profil yok / anahtar yok | **Hayır** — istek hiç gitmedi |

### Politika iki yerde olacak — bunu bilerek yapıyoruz

`eval/` üretim kodundan, üretim kodu `eval/`'den **import etmez** — ikisi
de ters bağımlılık olur. Bu yüzden `_gecici_ag_hatasi` mantığı
`agent/cloud_llm.py`'ye **kopyalanır.**

Bedeli: "hangi hata geçicidir" kararı iki dosyada. **Her iki yere de tek
satırlık not düş:** *"Bu politika `eval/run_turkish_quality.py` ile
ikizdir; biri değişirse diğeri de değişmeli."* Ortak bir modül açmak
spekülatif genişlemedir (§2) ve bu kartın işi değil.

---

## 3. Görev

### ADIM 1 — Önce düşen testi yaz, KIRMIZI GÖR

`tests/test_ses_yolu_bulut_kapisi.py`'ye ekle (13 test var, bozma):

- Birinci deneme `ConnectionResetError` atar, ikincisi başarılı →
  `cloud_chat` **metni döndürür**, `CloudChatError` atmaz, çağrı sayısı 2.
- Her iki deneme de kopar → `CloudChatError` yukarı çıkar, çağrı sayısı
  **tam 2** (üç değil), ve `local_agent` yerele düşüp kullanıcıyı
  bilgilendirir (mevcut davranış bozulmaz).
- HTTP 401 → çağrı sayısı **tam 1**. Kalıcı hata tekrarlanmaz.
- `"dis model bos cevap dondu"` → çağrı sayısı **tam 1**.
- Zaman aşımı bütçesi: birinci çağrıya geçen `timeout` 12, ikinciye 7.
  Sahte uçta yakalanır.
- Anahtar hiçbir yeniden deneme yolunda sızmaz (mevcut redaksiyon
  testinin kardeşi).

### ADIM 2 — `agent/cloud_llm.py:165-168` etrafına döngü

`_http_json` çağrısını saran mevcut `try/except` yeniden deneme döngüsüne
dönüşür. Redaksiyon (`anahtar` → `[REDACTED]`) **korunur** — son hata
mesajı da aynı temizlikten geçer.

`local_agent.py`'ye **DOKUNMA.** `:1022`'deki yakalama ve
`_BULUT_AG_HATASI` duyurusu aynen kalır — kullanıcı hâlâ "hat koptu,
yerele düştüm" diye duyar. Değişen tek şey: bu duyuru **daha seyrek**
çıkacak.

### ADIM 3 — Mutasyon sınaması (atlanamaz)

Her yeni testi, düzeltmeyi bellekte geri alarak sına: deneme sayısını 1'e
indir, geçici/kalıcı ayrımını kaldır, bütçe bölmesini kaldır — **testin
kırmızı yandığını GÖR.** Yanmayan test kendi kurgusunu ölçüyordur,
yeniden yazılır.

### ADIM 4 — Oranı YENİDEN ÖLÇ

Düzeltme öncesi taban: **21 turun 7'si düştü (%33).**

Aynı ölçümü tekrarla (aynı üç soru sınıfı, aynı tur sayısı) ve yeni oranı
yaz. Ayrıca **uçtan uca gecikmenin** dünkü tabloya göre nasıl değiştiğini
ölç — özellikle kopan turların süresi:

```
kısa olgusal    978,9 ms  ->  ?
proje durumu  3.108,0 ms  ->  ?
uzun anlatım  6.483,3 ms  ->  ?
```

Oran düşmediyse **söyle** — düzeltme işe yaramamış demektir ve bunu
saklamak, dün ödediğimiz bedelin aynısıdır.

---

## 4. Sınırlar ve durma koşulları

- **DOKUNMA:** `agent/local_agent.py`, `agents/persona.py`,
  `eval/` (orada başka bir oturum olabilir), kalite dedektörleri,
  `config/runtime_profiles.json`.
- `DEFAULT_TIMEOUT_S = 20` **toplam tavandır ve büyümez.** İki denemenin
  toplamı bu tavanın altında kalmalı; testle kilitle.
- `.env` okunmaz, yazılmaz (§9).
- Kapı: `pytest tests -q` **iki sırada**, `ruff check .` **≤ 283**.
- Mutasyon sınamasından geçmeyen bir test varsa: **DUR.**
- ADIM 4'te oran düşmediyse: **DUR ve söyle**, başka çözüm arama.
- Push yok. Yalnız isimli dosya `git add`.

## 5. Bitti sayılma ölçütü

- Altı test var, hepsi önce kırmızı görüldü.
- Hepsi **mutasyon sınamasından** geçti (düzeltme geri alınınca kırmızı).
- Çağrı sayıları **tam** doğrulanıyor: geçici hata 2, kalıcı hata 1,
  boş cevap 1.
- İki denemenin toplam zaman aşımı bütçesi **20 s'yi aşmıyor** ve bu
  testle kilitli.
- `agent/cloud_llm.py` ve `eval/run_turkish_quality.py`'nin **ikisinde de**
  "bu politika ikizdir" notu var.
- **Düşme oranı yeniden ölçüldü** ve dünkü %33 ile yan yana yazılı.
- Gecikme tablosu dünküyle yan yana.
- Kapı iki sırada yeşil, ruff ≤ 283.
