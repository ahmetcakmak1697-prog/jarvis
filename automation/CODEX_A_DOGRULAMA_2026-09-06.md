# Codex A — bağımsız doğrulama, 2026-09-06

**Verdict: BLOCKER.** İncelenen HEAD: `57e30876`, branch: `auto/opencode-deepseek`.
Görev: `automation/KART_CODEX_B08_B10.md`. Yedi düzeltme ve B11/B12 ölçüm değişikliği ayrı değerlendirildi. A kapsamında kaynak/test düzeltmesi yapılmadı.

## Sonuçlar

| Madde | Commit | Sonuç | Kapsam |
|---|---|---|---|
| B01 | 7b85d8c | CONCERN | Nesne grafiği kaçışı kapanmış; tuple çoğaltması kaynak sınırını aşıyor. |
| B02 | 1c0974a | PASS | gui.py gerçekten kaldırılmış; envanter güncellenmiş. Ağ sözleşmesi literal IPv4 biçimleriyle sınırlı. |
| B03 | a39dca6 | CONCERN | Niyet denetimi ile gönderilecek nihai sorgunun hassasiyet denetimi ayrışıyor. |
| B04 | 939376a | CONCERN | RAM/SQL sorgu düzeyinde silme doğru; fiziksel kalıntılar kurtarılabilir. |
| B05 | c401d4e | PASS | Bağlanan guard'ın tanıdığı hassas metin ve guard arızası bulut TTS'yi engelliyor. Desen kapsamı sınırlı. |
| B06 | e53b160 | CONCERN | Branch ref değişikliği, bazı bağlam kaynakları ve göreli gitdir çözümü eksik. |
| B07 | eca272d | CONCERN | Genel analiz düzelmiş; yeni yanlış pozitifler ve Türkçe ekli PDF kaçırmaları var. |
| B11 | cce25c6 | PASS | Prompt değerlendirme alanı doğru adlandırılmış; bu TTFT/ürün kalite garantisi değildir. |
| B12 | cce25c6 | BLOCKER | Ağ kopması ses ölçümünde sessizce başarılı tur oluyor; ayrıca başlangıç/bitiş sınırları yanlış. |

PASS ifadeleri incelenen değişiklik ve belirtilen kapsam içindir; bütün sistemin güvenli olduğu iddiası değildir.

## A-01 — B12: başarısız TTS, başarılı tam ölçüm olarak kaydediliyor (BLOCKER)

**Nerede:** `scripts/olc_ses_gecikmesi.py:197`, `:199`, `:200`, `:215`, `:229`; bağlantı hatası dönüşü `voice/voice_loop.py:173`; varsayılan no-op bildirim `:93`.

**Ne olur:** Gerçek `VoiceIO.say()` ile gerçek ölçüm `main()` metoduna sahte ajan/ses sağlayıcısı bağlandı. Sahte speaker `ConnectionError("FAKE_NETWORK_DROP")` üretti. Rapor yazıcısı bellekte tutuldu; gerçek ağ/ses/dosya raporu çalıştırılmadı. Sonuç:

```json
{"exit_code": 0, "mode": "tam", "reported_turns": 1,
 "speaker_calls": 1, "error_visible": false}
```

Hiç ses üretilemediği halde tur ölçülmüş sayılıyor. `build_default_voice_io(enabled=True)` çağrısına `notify` verilmediğinden VoiceIO'nun hata bildirimi varsayılan no-op'a gidiyor. `say()` hata sonucu döndürmüyor; ölçüm bunu tamamlanmış seslendirme sayıyor. Kurulumun istisna fırlatmadan `enabled=False` VoiceIO döndürmesi de `ses_aktif=True` ve `mod=tam` etiketini engellemiyor.

**Neden şimdi:** VoiceIO'nun sohbeti sürdürmek için mevcut hata yutma davranışını, `cce25c6` yeni ölçüm girişinde başarı sinyali gibi kullanıyor. B05'e yeni hata diye atfedilmiyor; hata yeni ölçüm bağlantısında. Protokol K2'nin “kopmayı sessizce yutup başarılı rapor eden yol” BLOCKER eşiğine doğrudan uyuyor.

**Düzeltme kabul kanıtı:** Sahte TTS kopması/kurulum başarısızlığı turu geçerli tam ölçüm yapmamalı; hata görünmeli. Başarılı turda gerçekten ilk ses olayının kanıtı olmalı. Bu raporda düzeltme yapılmadı.

## A-02 — B12: ölçülen zaman aralığı PUSULA aralığı değil (CONCERN)

**Nerede:** `scripts/olc_ses_gecikmesi.py:67`, `:70`, `:79`, `:80`; gerçek oynatıcı `scripts/j0_tts_adapters.py:508`, dinleme zinciri `voice/stt.py:448`.

**Ne olur:** Saat, VAD konuşma-sonu olayında değil `dinle()` öncesinde başlıyor. `vio.prompt()` mikrofon kaydını, konuşmayı, STT'yi ve gerekirse klavye beklemesini kapsıyor. Son saat ilk duyulan seste değil `say()` dönüşünde alınıyor; varsayılan oynatıcı müziğin bitmesini bekliyor.

Deterministik sahte saat senaryosu: konuşma sonu 4,5 s; metin hazır 5,0 s; yanıt hazır 5,1 s; ilk ses 5,2 s; oynatma sonu 7,2 s. Gerçek ölçüm fonksiyonunun çıktısı ve probun ayrıca hesapladığı karşılaştırma aşağıdadır. `speech_end_to_first_audio_ms` ürünün döndürdüğü bir alan değildir:

```json
{"olc_tek_tur": {"stt_ms": 5000.0, "model_ms": 100.0,
 "ses_ms": 2100.0, "toplam_ms": 7200.0},
 "probe_comparison": {"speech_end_to_first_audio_ms": 700.0}}
```

**Neden şimdi:** `cce25c6` docstring'i VAD-sonu → ilk ses ölçtüğünü söylüyor; yeni kod iki farklı sınırı kullanıyor. `--kuru` yardımında model+sentez yazmasına karşın `:187` no-op nedeniyle sentez de ölçülmüyor.

**Mevcut kayıt hakkında:** `automation/SES_GECIKMESI_20260906-2116.json` dürüstçe `mod=kuru` diyor: 4 tur, p50 10954 ms, p95 17798 ms. Bunlar `ajan.chat()` dönüş süreleri; canlı ses gecikmesi değildir. Bu kayıt, tek başına “darboğaz prompt işleme” ayrımını kanıtlamaz; prompt/token üretim dilimleri burada ölçülmüyor. Sayısal kayıt yeniden yazılmadı.

## A-03 — B01: tuple döndüren matematik işlevleri bellek sınırını deliyor (CONCERN)

**Nerede:** `tools/tools.py:511`, `:569`, `:583`.

**Ne olur:** `frexp(1)*1000000000`, izinli `math.frexp` sonucunu iki öğeli tuple olarak sınırsız `operator.mul` işlemine geçiriyor. `modf` de tuple üretiyor. AST'den alınan gerçek yorumlayıcıda çarpma yerine casus kondu: `(tuple, 2 öğe, 1000000000)` argümanları görüldü. Büyük tahsis çalıştırılmadı. Üs/factorial/comb/perm sınırları bu yolu kapsamaz.

**Neden şimdi:** `7b85d8c` yeni beyaz listede bütün callable math üyelerini alıyor; sonuç türünü aritmetik öncesinde sınırlamıyor. Nesne grafiği üzerinden kod yürütme kapanmış olsa da kaynak tüketiminin kapandığı söylenemez. K1 kaynak sınırı endişesi; protokolün donanım/socket/ses tamponu BLOCKER eşiği değildir.

## A-04 — B03: nihai sorgunun veri sınıfı tekrar denetlenmiyor (CONCERN)

**Nerede:** `agent/local_agent.py:587`, `:604`; mevcut sorgu dönüşümü `:542`.

**Ne olur:** Gerçek `_detect_tool → _run_tool` zincirinde sentetik
`paara rola FAKE_AUDIT_MARKER son haberler` girdisi,
`parola FAKE_AUDIT_MARKER son ler` olarak sahte web aracına ulaştı: **1 çağrı**.
Orijinal metin politika kararından geçiyor; dönüştürülmüş sorgu yalnız sanitize ediliyor. Nihai sorguya `decide()` uygulansa hassas sayılacaktı; sanitizer boşluklu `parola X` biçimini temizlemiyor.

**Neden şimdi:** `a39dca6` eklenen `decide(original_message or sorgu)` ile `sanitize(sorgu)` ayrımı, yeni kapıyı eksik bırakıyor. Önceden var olan bozuk kırpma “yalnız kalite hatası” diye sınıflandırılmış, fakat bu birleşimde güvenlik etkisi var.

Boş `original_message` tek başına bypass değildir: hassas sorgu doğru engellendi. Politika kararındaki istisnada **0 çağrı** doğrulandı. Sanitizer istisnasının kaynakta fail-closed dönüşü var; bu alt dal için ayrıca bağımsız hata enjeksiyonu yapılmadı. Aktif yerel zincirde kapıyı atlayan ikinci araç yürütme yolu gösterilmedi.

## A-05 — B04: mantıksal silme fiziksel silme anlamına gelmiyor (CONCERN)

**Nerede:** `memory/memory_manager.py:124`.

**Ne olur:** Geçici sentetik SQLite veritabanında sistem Python 3.11 için `PRAGMA secure_delete=0` gözlendi. Gerçek yeni `clear_conversations()` **1 kayıt sildi**, sorguda satır kalmadı; sentetik işaret veritabanı dosyasının baytlarında kaldı. Canlı kullanıcı hafızası okunmadı.

**Neden şimdi:** `939376a` yeni temizleme işlevi `DELETE` uyguluyor, kurtarılamaz silmeyi sağlamıyor. Bu bir yeni ham-veri regresyonu değil, kartın özellikle sorduğu silme güvencesinin sınırıdır. Gerekli fiziksel silme kapsamı ayrıca belirlenmelidir; yalnız VACUUM eklemek bütün yedek/WAL kopyalarının silindiğini kanıtlamaz.

Disk silme hatası denemesinde bağlantı `closed=True`; kullanıcıya disk hatası bildiriliyor, sahte başarı yok. Guard arızasında ham metin yerine placeholder kullanılıyor.

**Önceden var olan borç:** Yeni `_temizle` bağlantısının kullandığı `agents/redaction_guard.py:25` sentetik API anahtarı/kart numarası desenlerini kaçırıyor. B05 TTS de aynı sınırlı sınıflandırıcıyı kullanıyor. Bu commit'lerin eski desen borcunu kapattığı iddia edilmemeli.

## A-06 — B06: yeni commit ve bazı kaynaklar bağlamı tazelemiyor (CONCERN)

**Nerede:** `agent/local_agent.py:264`, `:274`, `:275`; okunup izlenmeyen kaynak `:405`.

**Ne olur:**

- Branch üzerinde commit atıldığında sembolik `HEAD` aynı kalır, `refs/heads/...` değişir. Yeni imza yalnız HEAD'i izliyor. Sentetik ref değişiminden sonra yükleyici çağrı sayısı **1**, bağlam hâlâ `old_fake_commit` oldu. Worktree ortak refs/packed-refs de izlenmiyor.
- Yükleyicinin okuduğu `automation/T1_S2_FAIL_LOG.md` eklenince imza değişmedi. Yükleyicinin kullandığı ortam bayrağı da izlenmiyor.
- `gitdir: ../.git`, worktree köküne göre çözülmüyor. Farklı köklü sentetik worktree'de gerçek HEAD mevcutken imza `('..\\.git\\HEAD', None, None)` oldu.

**Neden şimdi:** Bunlar `e53b160` eklenen fingerprint'in eksikleri. Eski bayat bağlam sorununun bütünüyle kapandığı gösterilemiyor; PUSULA'nın canlı repo durumu şartına etkisi var.

## A-07 — B07: yeni yönlendirme yanlış pozitif ve negatif üretiyor (CONCERN)

**Nerede:** `agent/local_agent.py:98`, `:111`, `:114`, `:658`.

**Ne olur:** `README.md nedir?` yeni uzantı eşleşmesi nedeniyle gerçek chat metodunda sahte bağımlılıklarla **FIND → RAG_INIT → INDEX → QUERY** yoluna girdi. `belgesel oner` ve `belge ne demek?` de pozitif. Buna karşılık `PDFyi oku` / `PDFleri incele` **False**; özellikle kesme işareti üretmeyen ses dökümleri etkilenebilir.

**Neden şimdi:** `eca272d` .md uzantısı ve “belge” kökünü ekliyor; kısa “pdf” kökünde kelime sınırı kullanarak eski substring davranışını daraltıyor. Genel kod analizi isteğinin PDF yolundan çıkması doğru, bütün yönlendirme sözleşmesi kapanmış değil. Belirtilen dosya yerine en yeni PDF'yi seçme davranışı eski borçtur, bu diff'e yeni hata diye atfedilmedi.

## B02, B05, B11 için bağımsız olumlu kanıt

- **B02:** gui.py silinmiş, `scripts/envanter_uret.py:55` giriş listesi güncellenmiş. Yerine işaret edilen `jarvis_desktop.py:640`, `:658` loopback. `jarvis_server.py` tarihli istisnası mevcut; incelenmedi/değiştirilmedi. `tests/test_network_binding_contract.py:25` regex'i değişken/IPv6/nested-call biçimlerini bütünüyle taramaz; mevcut başka açık bind kanıtı değildir.
- **B05:** Gerçek VoiceIO ile fake speaker: tanınan hassas metin için **0**, sıradan metin için **1**, guard istisnasında **0 çağrı + bildirim**. Yukarıdaki eski desen borcu saklı kalır.
- **B11:** `eval/run_turkish_quality.py:156`, `:197`, `:304`, `:389` yeni alanı taşıyor. Gerçek `_ollama_ask` fonksiyonu AST'den alınarak fake HTTP yanıtına bağlandı: `prompt_eval_duration=123000000` → `prompt_eval_ms=123.0`; eski alan yok, timeout=300. Ağ çağrısı yapılmadı. Tarihsel JSON'lar değiştirilmedi.

## Protokolün dört kriteri

1. **K1 — CONCERN:** B01 tuple çoğaltmasında kaynak sınırı eksik. B04 DELETE hata yolunun bağlantı kapanışı ölçüldü; yeni donanım/socket kaçağı ya da sınırsız ses tamponu kanıtlanmadı.
2. **K2 — BLOCKER:** A-01, sahte ağ kopmasını sessizce tamamlanmış ses ölçümü sayıyor. Yeni zaman aşımsız ağ beklemesi ayrıca gösterilmedi.
3. **K3 — PASS, diff kapsamıyla:** İncelenen değişikliklerde yeni çoklu uydu paylaşımlı durumu/kilit sırası gösterilmedi. Canlı uydu testi yapılmadı.
4. **K4 — CONCERN:** `graphify update .` tamamlandı: 5795 düğüm, 10928 kenar, 344 topluluk; HEAD `57e30876`; Import Cycles **None detected**. Önceki raporla aynı yedi 60+ bağlantılı düğüm var, yeni 60+ düğüm yok. B03 `agent/local_agent.py:586` ve B05 `voice/voice_loop.py:41` geç import'larının neden geç olduğu açıklanmamış; protokolün açık maddesi gereği düşük öncelikli CONCERN. B04 geç import gerekçesi belgeli. Graphify'ın ilk sandbox denemesi erişim hatası verdi; izinli dış çalıştırma başarılı oldu. LLM etiketleme çalıştırılmadı.

## Doğrulama kapısı ve sınırlar

- `pytest tests -q`: **1793 passed, 1 xfailed**, 83,89 s.
- `ruff check . --statistics`: **290 bulgu**, çıkış kodu 1; kabul edilen mevcut lint borcu, artış yok.
- Test dosyaları ters sırada tam süit: **1793 passed, 1 xfailed**, 72,35 s.
- Her iki süitte `tests/test_quality_scorer.py:644` taban testi geçti; kayıtlı puan **49/64**. Yeni canlı kalite koşusu yapılmadı.
- Her iki süitte aynı iki mevcut TestCore toplama uyarısı var.
- Problar gerçek metot/AST ve fake bağımlılıklar üzerinden yürütüldü; uyku/büyük tahsis/gerçek dış çağrı/ses donanımı kullanılmadı. Bellek deneyi yalnız sentetik geçici SQLite üzerinde.
- Kaynak/test dosyaları, yasaklanan dosyalar ve gerçek config JSON'ları değiştirilmedi. Secret dosyaları okunmadı. Graphify çıktıları Git tarafından izlenmiyor.

## B bölümünün durumu ve insan kararı

**B08/B09/B10 uygulanmadı; commit/push yapılmadı.** A'nın BLOCKER/CONCERN sonucu üzerine kartın “bir şey patlarsa yaz ve dur” ve protokolün “Ahmet'e gider” kuralı uygulandı. Bulgular A kapsamındaki danışman dosyalarında otomatik düzeltilmedi.

B08 için ayrı açık karar da var: eski `main.py claude → JarvisAgent` girişi emekliye mi ayrılacak, desteklenerek mi onarılacak? Öneri emeklilik; bu mevcut AssistantExecutor/APIExecutor hattının kaldırılması anlamına gelmez. Karar kullanıcıya soruldu, henüz yanıt yok. Devam izni verilirse B08/B09/B10 kendi kabul testleri ve ayrı commit kapılarıyla ele alınmalı.

Bu rapor, HUMAN_NEEDED maddesi ve append-only BLACKBOX olayı denetim çıktısıdır. Çözülmüş yeni hata olmadığı için FAILURES.md'ye “düzeltildi” kaydı eklenmedi.
