# KART — Codex: API yolu (B08–B10) + bağımsız doğrulama

**Kime:** Codex (gpt-6-astra) · **Tarih:** 2026-09-06 · **Veren:** Ahmet
**Bağlam commit:** `cce25c6`

---

## Rol değişikliği — önce bunu oku

`CODEX_AUDIT_PROTOCOL.md` senin sözleşmen ve şöyle diyor:

> *"Codex **review-only**'dir: bulguyu yazar, düzeltmeyi kendisi uygulamaz."*

**Ahmet bu kart için o kısıtı kaldırdı.** Bu kartın B bölümünde kod
yazacaksın. A bölümünde ise rol değişmedi — orada hâlâ denetçisin.

Değişmeyenler: `git add -A` yasak, push yalnız Ahmet'in onayıyla, `.env`
okunmaz/yazılmaz/loglanmaz, park edilmiş cepheler açılmaz, auto-fix retry yok
(bir şey patlarsa yaz ve dur).

---

## Neden sen, neden bu iş

İş bölümü keyfî değil, güce göre:

- **Danışman (Claude)** bugün B01–B07'yi kapattı ve B11/B12 ölçüm hattını
  kurdu. O kodun bağlamını taşıyor; devretmek soğuk başlangıç israfı olurdu.
- **Sen** API yolunu buldun ve kabul testlerini zaten yazdın. Ayrıca
  bağımsız denetimde kendini kanıtladın — 12 bulgu, hepsi `dosya:satır`
  kanıtlı.
- Ve kimse **kendi işini** onaylamamalı. A bölümü tam bunun için.

---

## A. Bağımsız doğrulama — danışmanın 7 düzeltmesi

Rolün burada denetçi. **Düzeltme yapma, bulgu yaz.**

Denetlenecek commit'ler:

```
7b85d8c  B01  calculate sandbox kaçışı
1c0974a  B02  gui.py emekliye ayrıldı + ağ bağlama sözleşmesi
a39dca6  B03  egress araçları politikadan geçiyor
c401d4e  B05  ses çıkışı veri sınıfını denetliyor
939376a  B04  "temizle" gerçekten temizliyor
eca272d  B07  genel istek PDF yoluna sapmıyor
e53b160  B06  proje durumu tazeleniyor
cce25c6  B11/B12  etiket düzeltmesi + gecikme ölçüm hattı
```

Özellikle şunlara bak — bunlar danışmanın **kendi** kör noktaları olabilir:

1. **B01'in beyaz listesi gerçekten kapalı mı?** `ast` tabanlı yorumlayıcı
   yeni bir kaçış yüzeyi açtı mı? Kaynak sınırları (`_guarded_pow`,
   factorial/comb/perm) aşılabilir mi?
2. **B03'ün kapısı atlatılabilir mi?** `_run_tool` tek boğaz noktası mı,
   yoksa bir aracı çağıran başka yol var mı? `original_message` boş
   geçilirse ne oluyor?
3. **B04 gerçekten siliyor mu?** SQLite `DELETE` sonrası veri kurtarılabilir
   mi (VACUUM yok)? Maskeleme `RedactionGuard`'ın kaçırdığı desenleri
   (`sk-...`, kredi kartı) yine kaçırıyor — bu kabul edilebilir mi?
4. **B06'nın parmak izi eksik mi?** Hangi kaynak değişikliği tazelemeyi
   tetiklemez? Worktree'de `.git` çözümü doğru mu?
5. **B07 fazla mı daralttı?** Artık PDF yoluna gitmeyen ama gitmesi gereken
   bir istek var mı?
6. **B12 ölçümü doğru dilimliyor mu?** `olc_tek_tur` gerçekten neyi ölçüyor,
   raporladığını mı?

Verdict biçimi değişmedi: **PASS | CONCERN | BLOCKER**, ve her bulgu üçlüyle
(nerede / ne olur / neden şimdi).

---

## B. Uygulama — B08, B09, B10

Kendi raporundaki (`automation/CODEX_DENETIM_2026-09-06.md`) kabul testlerini
kullan. Her biri **ayrı commit**.

### B08 — API girişi tanımsız sınıf içe aktarıyor

`agent/jarvis_agent.py:32` `MemoryManager` istiyor; `memory/memory_manager.py`
yalnız `JarvisMemory` tanımlıyor. Gerçek import satırı tek başına
**ImportError** veriyor.

**Kendi uyarını hatırla:** *"Sadece sınıf adını değiştirmek yeterli olduğu
varsayılmamalı."* Önce şunu belirle: bu giriş yolu **desteklenecek mi?**
Desteklenmeyecekse doğru iş, onu emekliye ayırmak — danışman `gui.py` için
tam bunu yaptı (`1c0974a`), deseni oradan al. Desteklenecekse hafıza arayüz
sözleşmesini birlikte doğrula.

**Karar senin değilse dur ve Ahmet'e sor.**

### B09 — TLS, dosya ve shell sınırları

- `agent/jarvis_agent.py:84` `httpx.Client(verify=False)` — sertifika
  doğrulaması tamamen kapalı. `tools/tools.py:219` `fetch_webpage` ve
  araştırma dalında da kapalı.
- `tools/tools.py:91` `read_file` / `write_file` mutlak yolları ve proje
  dışına çıkan göreli yolları sınırlamıyor.
- `tools/tools.py:158` `git_diff` argümanı shell komutuna birleştiriyor;
  `tools/tools.py:52` `_run` `shell=True` kullanıyor.
- `run_python_code` (`tools/tools.py:482`) API araç listesinde ve aynı
  süreçte `exec` kullanıyor.

Kendi sınırını da hatırla: B08 nedeniyle bu yüzeyin bugün çalıştığı
gösterilmedi. Import düzeltilirse bu riskler etkinleşir.

### B10 — bütçe yanlış noktada tükeniyor

`agents/local_first_router.py:109` çalıştırıcının yerel mi bulut mu olacağı
belirlenmeden `external_call` bütçesi tüketiyor. Ve router redaction hatasını
`except: pass` ile geçiyor — hata enjekte edildiğinde `ask_external` dönüyor.

**Guard arızası dışarı çıkışı KAPATMALI, açmamalı.** Danışman B03 ve B05'te
bu deseni uyguladı; tutarlı ol.

`CostLedger` para değil **çağrı** sayıyor — "50 çağrı" bir dolar tavanı
değildir. Bunu düzeltme, **belgele**.

---

## Dokunma

- `agent/local_agent.py`, `voice/voice_loop.py`, `memory/memory_manager.py`,
  `eval/`, `scripts/olc_ses_gecikmesi.py` — danışmanın bugün dokunduğu yerler.
  Bulgu yaz, değiştirme.
- `jarvis_server.py` — 4295 satır, `0.0.0.0:8000`, `auto_updater` /
  `self_improver` / `task_executor` oradan erişiliyor. **Park edilmiş cepheye
  komşu; Ahmet'in kararı bekliyor.** Ağ sözleşmesi testinde tarihli istisna
  olarak duruyor.
- `.env`, `config/*.json` gerçek dosyaları.

## Kapı

Her commit'ten önce:

```
pytest tests -q          -> 1793 + 1 xfail, alfabetik VE ters sıra
ruff check .             -> 290'ı geçmeyecek
```

Taban testi (`test_the_recorded_run_still_scores_49_of_64`) hâlâ 49 demeli.
Commit yalnız isimli dosya. **Push yok. Bittiğinde dur.**
