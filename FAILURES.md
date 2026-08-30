# JARVIS Öğrenilen Hatalar ve Mimari Tuzaklar

> Bu dosya bir hata *günlüğü* değil, bir **kural üreteci**dir.
> Amaç: aynı tuzağa iki kez düşmemek. Bir hata buraya yazılmadıysa
> çözülmüş sayılmaz (bkz. `CLAUDE.md` §13.4).

## Nasıl kayıt eklenir

- **Yalnız kritik olanı yaz.** Yazım hatası, tek satırlık typo, geçici
  ortam sorunu buraya girmez. Buraya giren: mimari yanlış varsayım,
  sessiz mantık hatası, tekrar edebilecek sınıf-düzeyi tuzak.
- **En yeni kayıt en üste** eklenir.
- Her kayıt üç parçadan oluşur ve üçü de zorunludur:
  **Tuzak** (ne oldu) → **Kök neden** (neden oldu) → **Kural** (bir daha
  düşmemek için ne yapılacak).
- **Kural satırı test edilebilir olmalı.** "Dikkatli ol" kural değildir;
  "X yazılmadan önce Y testi yazılır" kuraldır.
- Kayıt tarihlidir ve mümkünse kanıta (commit hash, test adı, BLACKBOX
  `sequence`) bağlanır.

## Kayıt şablonu

Yeni kayıtlar aşağıdaki şablonla, `## Kayıtlar` başlığının hemen altına
eklenir:

```markdown
### [YYYY-AA-GG] Kısa başlık — bir cümlelik özet

- **Alan:** (ör. bellek katmanı / J0 ses hattı / router / otomasyon kapısı)
- **Şiddet:** BLOCKER | CONCERN | NOTE
- **Tuzak:** Ne oldu? Gözlemlenen yanlış davranış, tek paragraf.
- **Kök neden:** Neden oldu? Yanlış olan varsayım/mekanizma.
  Semptom değil, sebep yazılır.
- **Kural:** Bir daha düşmemek için ne yapılacak? Emir kipinde, tek cümle,
  doğrulanabilir.
- **Kanıt:** commit hash / test adı / BLACKBOX sequence / dosya:satır
- **Regresyon testi:** Bu hatayı yeniden üretecek testin adı.
  (Yoksa `YOK — açık borç` yazılır, uydurulmaz.)
```

## Kayıtlar

### [2026-08-30] Test State Pollution & Isolation — süit sıra bağımlıydı, 49 "hata" sahteydi

- **Alan:** test altyapısı (`tests/conftest.py`), orchestrator + J0 ses hattı
- **Şiddet:** BLOCKER (yeşil hattı imkânsız kılıyordu)
- **Tuzak:** `pytest tests` 51 başarısızlık veriyordu; ama aynı dosyalar tek
  başına çalıştırıldığında geçiyordu (`test_orchestrator.py` tek başına 42/42
  geçer, tam süitte 42/42 çökerdi). Yani süit **sıra bağımlıydı** ve
  başarısızlıkların 49'u gerçek kusur değildi. Bu, en tehlikeli hata sınıfıdır:
  gerçek 2 hatayı 49 sahte hatanın içinde gizliyordu.
- **Kök neden:** İki ayrı `sys.modules` sızıntısı vardı.
  1. **Belirsiz modül adı.** Repoda ayn ada sahip iki modül var:
     `scripts/orchestrator.py` ve `agents/orchestrator.py`. `import orchestrator`
     hangisine bağlanacağını `sys.path` sırasından öğreniyor.
     `tests/test_blackbox_log.py:45` modül düzeyinde `agents/` dizinini
     `sys.path[0]`'a sokuyor; alfabetik olarak sonra **toplanan**
     `test_orchestrator.py` ve `test_contractpath_schema_alignment.py` ise
     *scripts* sürümünü bekliyor → `AttributeError: module 'orchestrator' has
     no attribute '_read_verdict'`. Kritik ayrıntı: hasar **toplama
     (collection)** anında oluşuyor, çünkü `import orchestrator` modül
     düzeyinde. Bu yüzden bir fixture çok geç kalır.
  2. **Opsiyonel ses kütüphanesi sızıntısı.**
     `scripts/j0_spike_b_latency_probe.py` çalışma anında `sounddevice` import
     ediyor ve modül `sys.modules`'te kalıyor. `test_j0_voice_adapters.py` /
     `test_j0_voice_loop.py` ise "voice adapter'ı import etmek ağır ses
     kütüphanelerini yüklememeli" diye *import güvenliği* iddia ediyor; kirli
     `sys.modules` yüzünden çöküyorlardı.
- **Kural:** Testler arası izolasyon **tek noktadan**, `tests/conftest.py`'de
  sağlanır; hiçbir test dosyası bunun için değiştirilmez.
  (a) Birden fazla enjekte edilebilir dizinde aynı ada sahip modüller
  *hesaplanarak* bulunur (sabit liste değil) ve her toplama adımında
  `sys.modules`'ten atılır; `scripts/` her zaman `agents/`'ın önünde tutulur.
  (b) Modül düzeyinde import'un bozduğu şey fixture ile değil,
  `pytest_collectstart` kancasıyla onarılır — **fixture toplama anına
  yetişmez.**
  (c) Ağır opsiyonel ses kütüphaneleri her testin hem kurulumunda hem
  sökümünde `sys.modules`'ten atılır; böylece koruma test sırasından bağımsız
  olur.
  (d) Yeşil hat iddiası **tam süit** üzerinde kanıtlanır; ek olarak süit
  **ters sırada** da çalıştırılır. "Tek başına geçiyordu" bir kanıt değildir.
- **Kanıt:** `pytest tests` → 1351 passed (öncesi: 51 failed / 1300 passed).
  Ters sıra (126 dosya) → 1351 passed. Minimal tekrar-üreticiler:
  `test_blackbox_log.py + test_orchestrator.py` → 133 passed;
  `test_j0_spike_b_latency_probe.py + test_j0_voice_adapters.py` → 127 passed.
- **Regresyon testi:** YOK — açık borç. Sızıntının kendisini yakalayan
  bir test yok; koruma kaldırılırsa bunu ancak tam süit fark eder.
  Bu boşluk bilinçli olarak kaydedilmiştir.

### [2026-08-30] Bayat sözleşme iddiası — `assert result is True` DeliveryResult'a karşı

- **Alan:** proaktif teslimat hattı (E1-S6B)
- **Şiddet:** CONCERN
- **Tuzak:** `tests/test_proactive_telegram_adapter.py` içindeki 2 test
  `run_proactive_delivery(...)` çağrısının `is True` / `is False` döndürmesini
  bekliyordu; fonksiyon `DeliveryResult` dönüyor.
- **Kök neden:** E1-S6B, dönüş tipini bilinçli olarak `bool` → `DeliveryResult`
  yükseltti (`tests/test_e1_6b_delivery_result.py` docstring'i: "returns a
  structured DeliveryResult **instead of a bare bool**"). İki iddia bu
  geçişte güncellenmeden kaldı. Testlerin geri kalanı (`calls` iddiaları)
  zaten geçiyordu — yani davranış doğruydu, **iddia bayattı**.
- **Kural:** Bir dönüş tipi genişletildiğinde, o fonksiyonu çağıran **tüm**
  testler aynı commit'te taranır. `is True` / `is False` kimlik
  karşılaştırmasıdır: zenginleştirilmiş bir dönüş tipiyle **hiçbir kaynak
  düzeltmesi** onu geçiremez — bu yüzden böyle bir başarısızlık her zaman
  "kaynak mı bayat, test mi bayat" sorusunu zorunlu kılar; sessizce kaynağı
  bool'a geri döndürmek yanlış cevaptır.
- **Kanıt:** `agents/proactive_runtime.py:18` (`-> DeliveryResult`),
  `tests/test_e1_6b_delivery_result.py:1-7`
- **Regresyon testi:** `tests/test_e1_6b_delivery_result.py::test_delivery_result_is_dataclass`
  (sözleşmeyi zaten kilitliyor)

---

## Kalıcı tuzak listesi (repo genelinde bilinen, tekrar eden sınıflar)

Bunlar tek bir olaya değil, bu repoda **tekrar tekrar** ortaya çıkan
hata sınıflarına karşılık gelir. Yeni kod yazarken önce buraya bakılır.

- **Türkçe `.lower()` tuzağı** — `"İ".lower()` combining-dot üretir,
  `"I".lower()` `'i'` verir (Türkçe'de `'ı'` olmalı). Düz `.lower()` ile
  keyword eşleştirme sessizce KAÇIRIR. Kural: eşleştirmede her iki tarafa
  da aynı ASCII-fold uygulanır (`_fold_tr`). Bkz. `CLAUDE.md` §6.
- **PowerShell paste'i Türkçe karakteri bozar** ve BOM ekler. Kural:
  patch `@' ... '@ | python` here-string ile verilir, içinde `"""`
  kullanılır, asla `'''`. Bkz. `CLAUDE.md` §5.
- **"Başarılı" demeden önce görmek** — patch sonrası `py_compile` +
  `git status`/`git diff` + import smoke çalıştırılmadan hiçbir iş
  tamamlandı sayılmaz. Bkz. `CLAUDE.md` §5.
- **Doküman ↔ durum dosyası kayması** — iki dosya aynı gerçeği farklı
  anlatabiliyor (ör. `HUMAN_NEEDED.md` "Pending" derken
  `roadmap_state.json` "DONE" diyor). Kural: bir gerçeğin tek bir
  doğruluk kaynağı olur; ikinci yer ona *referans verir*, kopyalamaz.
- **Kendi ürettiğini kendin doğrulama önyargısı** — "bunu ben yazdım,
  iyi olduğunu düşünüyorum". Kural: stratejik "sıradaki adım doğru mu"
  sorusu ayrıca sorulur; Codex diff-review'ı bunu kapatmaz.
  Bkz. `CLAUDE.md` DANIŞMAN MODU.
